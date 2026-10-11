using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace Base.Res
{
    // 成组资源。children 是最新的一批子资源，raw 是正在用、已建立联系的一批；两者是同一个对象时，没有待交付的状态。
    // 包含即计数：在使用时，每一批对它的每个成员计一次数。计数只记账：本组在检查时激活还没在使用的成员，放开后计数归零的由本组停用。
    // 增删立刻换上新的一批、改计数，但不激活、不交付；新的成员在本组的下一个检查点激活，通常就是紧接着的提交。
    // 被上层联系（在某个上层的 raw 里）时不就地替换：新的一批齐了只通知上层，等上层重建、放开旧的一批时就位。
    // 本层不涉及引擎对象：子资源之间的联系由派生类在 OnActive 里建立，自身镜像由派生类在 Render 里应用。
    // Render 不级联：要改用某个子资源时，派生类在 Render 里显式地对它 SetData，再 SetActive(true)；只提交数据，不提交增删。
    public abstract class ResourceGroup : Resource
    {
        // 最新的一批子资源。每次增删换成一个新的集合，原来的一批不改。
        HashSet<Resource> children;

        protected ResourceGroup()
        {
            children = new HashSet<Resource>();
        }

        public void AddChild(Resource child)
        {
            if (child == null)
                throw new ArgumentNullException("child");
            if (children.Contains(child))
                throw new ArgumentException("子资源已在本组中", "child");
            if (new HashSet<Resource>(dependents).Count > 1)
                Trace.TraceWarning("修改了共享的资源");

            HashSet<Resource> batch = new HashSet<Resource>(children);
            batch.Add(child);
            HashSet<Resource> linked = raw as HashSet<Resource>;
            if (linked != null && linked.SetEquals(batch))
                batch = linked;

            HashSet<Resource> old = children;
            children = batch;
            if (!active)
                return;
            if (!ReferenceEquals(batch, raw))
            {
                foreach (Resource c in batch)
                    c.AddDependent(this);
            }
            // 被取代、没在用的一批放开；之前激活、现在被放弃的子资源随之停用。
            if (!ReferenceEquals(old, raw))
            {
                foreach (Resource c in old)
                {
                    c.RemoveDependent(this);
                    if (c.dependents.Count == 0)
                        c.SetActive(false);
                }
            }
        }

        public void RemoveChild(Resource child)
        {
            if (child == null || !children.Contains(child))
                throw new ArgumentException("子资源不在本组中", "child");
            if (new HashSet<Resource>(dependents).Count > 1)
                Trace.TraceWarning("修改了共享的资源");

            HashSet<Resource> batch = new HashSet<Resource>(children);
            batch.Remove(child);
            HashSet<Resource> linked = raw as HashSet<Resource>;
            if (linked != null && linked.SetEquals(batch))
                batch = linked;

            HashSet<Resource> old = children;
            children = batch;
            if (!active)
                return;
            if (!ReferenceEquals(batch, raw))
            {
                foreach (Resource c in batch)
                    c.AddDependent(this);
            }
            if (!ReferenceEquals(old, raw))
            {
                foreach (Resource c in old)
                {
                    c.RemoveDependent(this);
                    if (c.dependents.Count == 0)
                        c.SetActive(false);
                }
            }
        }

        // 有 raw，且最新的一批都已齐。
        public override bool IsLoaded()
        {
            if (raw == null)
                return false;
            foreach (Resource c in children)
            {
                if (!c.IsLoaded())
                    return false;
            }
            return true;
        }

        // 开始使用：最新的一批计数，再检查；成员在检查时激活。
        protected override void Load()
        {
            foreach (Resource c in children)
                c.AddDependent(this);
            OnDependencyLoaded();
        }

        // 停止使用：没在用的最新一批放开，计数归零的停用；在用的一批由 Free 放开。
        protected override void BreakLoad()
        {
            if (ReferenceEquals(children, raw))
                return;
            foreach (Resource c in children)
            {
                c.RemoveDependent(this);
                if (c.dependents.Count == 0)
                    c.SetActive(false);
            }
        }

        // 放开在用的一批：计数归零的子资源停用；仍有计数的子成组资源已不受本组联系，检查一次，待交付的就此就位。
        protected override void Free(object raw)
        {
            foreach (Resource c in (HashSet<Resource>)raw)
            {
                c.RemoveDependent(this);
                if (c.dependents.Count == 0)
                {
                    c.SetActive(false);
                    continue;
                }
                ResourceGroup group = c as ResourceGroup;
                if (group != null)
                    group.OnDependencyLoaded();
            }
        }

        // 激活还没在使用的成员；最新的一批不是 raw、已齐、本组没有被上层联系，就交付；被联系就转告上层。
        protected override void OnDependencyLoaded()
        {
            if (!active)
                return;

            HashSet<Resource> linked = raw as HashSet<Resource>;
            if (ReferenceEquals(children, linked))
            {
                bool stale = false;
                foreach (Resource c in linked)
                {
                    ResourceGroup group = c as ResourceGroup;
                    if (group != null && !ReferenceEquals(group.children, group.raw))
                        stale = true;
                }
                if (!stale)
                    return;
                // 联系着的子成组资源要换新版本：按原成员用新的一批。
                HashSet<Resource> batch = new HashSet<Resource>(linked);
                foreach (Resource c in batch)
                    c.AddDependent(this);
                children = batch;
            }

            // 激活的成员交付时会再通知本组。
            bool started = false;
            foreach (Resource c in children)
            {
                if (!c.active)
                {
                    c.SetActive(true);
                    started = true;
                }
            }
            if (started)
                return;

            foreach (Resource c in children)
            {
                if (!c.IsLoaded())
                    return;
                // 本组还没联系它：它要先就位。
                ResourceGroup group = c as ResourceGroup;
                bool linkedByThis = linked != null && linked.Contains(c);
                if (!linkedByThis && group != null && !ReferenceEquals(group.children, group.raw))
                    return;
            }

            bool linkedByUpper = false;
            foreach (Resource upper in dependents)
            {
                HashSet<Resource> upperRaw = upper.raw as HashSet<Resource>;
                if (upperRaw != null && upperRaw.Contains(this))
                    linkedByUpper = true;
            }
            if (linkedByUpper)
            {
                foreach (Resource upper in new HashSet<Resource>(dependents))
                {
                    ResourceGroup group = upper as ResourceGroup;
                    if (group != null)
                        group.OnDependencyLoaded();
                }
                return;
            }

            OnLoadDone(children);
        }
    }
}
