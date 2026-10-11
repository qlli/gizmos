using System;

namespace Base.Res
{
    // 按模板拷贝出来的资源。本类只决定何时拷贝、何时销毁拷贝；怎样拷贝由派生类的 CreateClone、DestroyClone 决定。
    // 本拷贝在使用时对模板计一次数，在检查时激活模板；放开后计数归零，就停用模板。
    // 模板只能是单个资源，它的 raw 在拷贝的生命期内不变；成组资源的地址拷贝，就是把它加入别的成组资源。
    public abstract class Clone : Resource
    {
        // 加载依赖。构造后不再改变。
        Resource template;

        protected Clone(Resource template)
        {
            if (template == null)
                throw new ArgumentNullException("template");
            if (template is ResourceGroup)
                throw new ArgumentException("模板只能是单个资源", "template");
            this.template = template;
        }

        // 开始使用：对模板计数，再检查；模板在检查时激活。
        protected override void Load()
        {
            template.AddDependent(this);
            OnDependencyLoaded();
        }

        // 停止使用：还没交付就放开模板，计数归零就停用它；已交付的由 Free 放开。
        protected override void BreakLoad()
        {
            if (raw != null)
                return;
            template.RemoveDependent(this);
            if (template.dependents.Count == 0)
                template.SetActive(false);
        }

        // 先销毁拷贝，再放开模板：拷贝可能引用模板的内容。
        protected override void Free(object raw)
        {
            DestroyClone(raw);
            template.RemoveDependent(this);
            if (template.dependents.Count == 0)
                template.SetActive(false);
        }

        // 模板没在使用就激活它；模板到了就交付。
        protected override void OnDependencyLoaded()
        {
            if (!active || raw != null)
                return;
            if (!template.active)
            {
                // 模板交付时会再通知本拷贝。
                template.SetActive(true);
                return;
            }
            if (template.IsLoaded())
                OnLoadDone(CreateClone(template.raw));
        }

        // 按模板的 raw 拷贝出一份 raw。只考虑同步的拷贝。
        protected abstract object CreateClone(object templateRaw);

        // 与 CreateClone 成对。
        protected abstract void DestroyClone(object cloneRaw);
    }
}
