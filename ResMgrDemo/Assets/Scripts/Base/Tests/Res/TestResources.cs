using System;
using System.Collections.Generic;

namespace Base.Res.Tests
{
    // 测试资源的名字，用来书写成组资源的 raw。
    public interface ITestNode
    {
        string Name { get; }
    }

    // 测试用单个资源。raw 记作「名字#第几次交付」，由测试调用 Complete 交付。
    public sealed class TestLeaf : Resource, ITestNode
    {
        LifecycleLog log;
        string name;

        // 为真时 Load 当场交付，模拟命中缓存。
        bool sync;

        // 为假时 BreakLoad 取消不了底层加载，结果照常到达，成为迟到的结果。
        bool cancelable;

        bool pending;
        int delivered;

        public TestLeaf(LifecycleLog log, string name) : this(log, name, false, true)
        {
        }

        public TestLeaf(LifecycleLog log, string name, bool sync, bool cancelable)
        {
            this.log = log;
            this.name = name;
            this.sync = sync;
            this.cancelable = cancelable;
            pending = false;
            delivered = 0;
        }

        public string Name
        {
            get { return name; }
        }

        public bool IsPending
        {
            get { return pending; }
        }

        public object CurrentRaw
        {
            get { return raw; }
        }

        // 交付进行中的加载。
        public void Complete()
        {
            if (!pending)
                throw new InvalidOperationException(name + " 没有进行中的加载");
            pending = false;
            delivered++;
            OnLoadDone(name + "#" + delivered);
        }

        // 取消不了的加载还在进行时，复用它。
        protected override void Load()
        {
            if (pending)
                return;
            log.Add(name, CallKind.Load, null);
            if (sync)
            {
                delivered++;
                OnLoadDone(name + "#" + delivered);
                return;
            }
            pending = true;
        }

        protected override void BreakLoad()
        {
            if (!pending)
                return;
            log.Add(name, CallKind.BreakLoad, null);
            if (cancelable)
                pending = false;
        }

        protected override void Free(object raw)
        {
            log.Add(name, CallKind.Free, (string)raw);
        }

        protected override void OnActive(object raw, bool active)
        {
            log.Add(name, active ? CallKind.ActiveOn : CallKind.ActiveOff, (string)raw);
        }

        protected override void Render(object raw)
        {
            log.Add(name, CallKind.Render, (string)raw);
        }
    }

    // 测试用成组资源。raw 记作按名字排序的子资源集合，如 {a,b}。
    public sealed class TestGroup : ResourceGroup, ITestNode
    {
        LifecycleLog log;
        string name;

        // 在本组的 Render 里额外执行，用来测试 Render 中的提交与停用。
        Action<TestGroup> renderHook;

        public TestGroup(LifecycleLog log, string name, params Resource[] children)
        {
            this.log = log;
            this.name = name;
            renderHook = null;
            foreach (Resource child in children)
                AddChild(child);
        }

        public string Name
        {
            get { return name; }
        }

        public void SetRenderHook(Action<TestGroup> hook)
        {
            renderHook = hook;
        }

        protected override void Load()
        {
            log.Add(name, CallKind.Load, null);
            base.Load();
        }

        // 只在首次交付之前停用时记：确有加载被打断。
        protected override void BreakLoad()
        {
            if (raw == null)
                log.Add(name, CallKind.BreakLoad, null);
            base.BreakLoad();
        }

        // 先记再交给基类：子资源在基类的 Free 里随之停用。
        protected override void Free(object raw)
        {
            log.Add(name, CallKind.Free, Format(raw));
            base.Free(raw);
        }

        protected override void OnActive(object raw, bool active)
        {
            log.Add(name, active ? CallKind.ActiveOn : CallKind.ActiveOff, Format(raw));
        }

        protected override void Render(object raw)
        {
            log.Add(name, CallKind.Render, Format(raw));
            if (renderHook != null)
                renderHook(this);
        }

        static string Format(object raw)
        {
            List<string> names = new List<string>();
            foreach (Resource child in (HashSet<Resource>)raw)
                names.Add(((ITestNode)child).Name);
            names.Sort(string.CompareOrdinal);
            return "{" + string.Join(",", names) + "}";
        }
    }

    // 测试用完整拷贝。raw 记作「名字<模板的 raw>#第几份」。
    public sealed class TestCopy : Clone, ITestNode
    {
        LifecycleLog log;
        string name;
        int copies;

        public TestCopy(LifecycleLog log, string name, Resource template) : base(template)
        {
            this.log = log;
            this.name = name;
            copies = 0;
        }

        public string Name
        {
            get { return name; }
        }

        protected override void Load()
        {
            log.Add(name, CallKind.Load, null);
            base.Load();
        }

        // 只在交付之前停用时记：确有加载被打断。
        protected override void BreakLoad()
        {
            if (raw == null)
                log.Add(name, CallKind.BreakLoad, null);
            base.BreakLoad();
        }

        protected override void Free(object raw)
        {
            log.Add(name, CallKind.Free, (string)raw);
            base.Free(raw);
        }

        protected override object CreateClone(object templateRaw)
        {
            copies++;
            return name + "<" + templateRaw + ">#" + copies;
        }

        protected override void DestroyClone(object cloneRaw)
        {
        }

        protected override void OnActive(object raw, bool active)
        {
            log.Add(name, active ? CallKind.ActiveOn : CallKind.ActiveOff, (string)raw);
        }

        protected override void Render(object raw)
        {
            log.Add(name, CallKind.Render, (string)raw);
        }
    }

    // 测试用引用：只多暴露 raw，用来比较是否与模板的 raw 是同一个对象。
    public sealed class TestRef : Reference
    {
        public TestRef(Resource template) : base(template)
        {
        }

        public object CurrentRaw
        {
            get { return raw; }
        }
    }
}
