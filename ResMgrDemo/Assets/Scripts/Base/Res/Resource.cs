using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace Base.Res
{
    // 抽象资源。加载与释放由派生类实现。
    // 单个资源、成组资源、拷贝走同一套流程，差别只在派生类实现的方法里。
    public abstract class Resource
    {
        // 全部使用信息。只由 SetData 修改，不触发任何实际处理。
        protected object data;

        // 当前持有的原始资源，如 UnityEngine.GameObject、UnityEngine.Texture2D 等。
        // 非空当且仅当生命期正在进行。OnActive、Render 等是 raw 的生命期，不是 Resource 对象的。
        // 成组资源要读上层与子资源的 raw，拷贝要读模板的 raw，所以对程序集内可见。
        protected internal object raw;

        // 唯一的状态标志：是否正被使用。
        internal bool active;

        // 需要本资源的上层。多重集合：上层的每一批需要本资源时各记一次。
        // 只记账：上层在检查时激活还没在使用的下层，放开后计数归零时由放开的上层停用。
        internal List<Resource> dependents;

        protected Resource()
        {
            data = null;
            raw = null;
            active = false;
            dependents = new List<Resource>();
        }

        // 开始使用时 Load；已在使用时提交：Render 镜像，再检查有没有可以就位的新状态。
        // 停止使用时 BreakLoad，再结束生命期。Load 与 BreakLoad 每个使用周期各调一次。
        // 有上层的资源由上层驱动：上层代码只对根调 SetActive(false)。
        public void SetActive(bool on)
        {
            if (on)
            {
                if (!active)
                {
                    active = true;
                    Load();
                }
                else
                {
                    if (raw != null)
                        Render(raw);
                    OnDependencyLoaded();
                }
            }
            else if (active)
            {
                active = false;
                BreakLoad();
                object oldRaw = raw;
                if (oldRaw != null)
                {
                    OnActive(oldRaw, false);
                    raw = null;
                    Free(oldRaw);
                }
            }
        }

        // 只修改镜像。共享的资源应当不可变。
        public void SetData(object data)
        {
            if (new HashSet<Resource>(dependents).Count > 1)
                Trace.TraceWarning("修改了共享的资源");
            this.data = data;
        }

        // 有 raw，并且最新的状态都已齐。
        public virtual bool IsLoaded()
        {
            return raw != null;
        }

        // 上层的一批需要本资源时计一次。只记账，不激活。
        internal void AddDependent(Resource dependent)
        {
            dependents.Add(dependent);
        }

        // 上层的一批不再需要本资源时放开一次。只记账，不停用，也不检查。
        internal void RemoveDependent(Resource dependent)
        {
            if (!dependents.Remove(dependent))
                throw new InvalidOperationException("上层放开前没有计数");
        }

        // 开始使用时调一次：发起加载，完成后调 OnLoadDone 交付。
        protected abstract void Load();

        // 停止使用时调一次：打断进行中的加载，回滚 Load 的全部副作用。不在加载时什么都不做。
        protected abstract void BreakLoad();

        // 释放原始资源，与交付对称。
        protected abstract void Free(object raw);

        // 生命期开始时做只做一次的初始化；结束时撤销开始与 Render 所做的全部修改。
        protected abstract void OnActive(object raw, bool active);

        // 按镜像修改 raw。可能被重复调用。
        protected abstract void Render(object raw);

        // 交付点。持有 raw 时是替换，只有没有被上层联系的成组资源会走到。
        protected void OnLoadDone(object newRaw)
        {
            // 停用之后才到达的结果，只有单个资源会有。
            if (!active)
            {
                Free(newRaw);
                return;
            }

            object oldRaw = raw;
            if (oldRaw != null)
            {
                OnActive(oldRaw, false);
                raw = null;
                Free(oldRaw);
                // 放开旧的一批时，仍有计数的子成组资源就位并通知本组，新的一批可能已在其中开始了生命期。
                if (raw != null)
                    return;
            }

            OnActive(newRaw, true);
            raw = newRaw;
            Render(raw);

            // 上层检查时可能停用别的上层，改动 dependents。
            foreach (Resource dependent in new HashSet<Resource>(dependents))
                dependent.OnDependencyLoaded();
        }

        // 检查能否交付。下层交付或就绪、上层放开了联系着本资源的一批、提交、开始使用时调用。
        protected virtual void OnDependencyLoaded()
        {
        }
    }
}
