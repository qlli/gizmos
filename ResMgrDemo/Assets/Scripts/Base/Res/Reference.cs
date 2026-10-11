namespace Base.Res
{
    // 地址拷贝：拷贝出的 raw 就是模板的 raw 本身。
    // 用于上层代码共享一个单个资源：每个使用者各持一份引用，各自 SetActive。
    // 多份引用拿到的是同一个对象，raw 属于模板，所以本类既不修改它，也不销毁它。
    public class Reference : Clone
    {
        public Reference(Resource template) : base(template)
        {
        }

        protected override object CreateClone(object templateRaw)
        {
            return templateRaw;
        }

        protected override void DestroyClone(object cloneRaw)
        {
        }

        protected override void OnActive(object raw, bool active)
        {
        }

        protected override void Render(object raw)
        {
        }
    }
}
