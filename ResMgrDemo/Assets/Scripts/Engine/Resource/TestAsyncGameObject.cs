using System.Collections;
using UnityEngine;

namespace Engine.Resource
{
    // 测试用叶节点资源。从 bundle 文件里取出 prefab，实例化成 GameObject。
    // raw 是实例化出来的 GameObject。bundle 与 prefab asset 不在本类里成为资源，
    // 它们的共享与计数由 AsyncBundle、AsyncAsset 加 Reference 另做。
    public class TestAsyncGameObject : Base.Res.Resource
    {
        string bundlePath;
        string assetName;

        // 镜像。raw 未到达时只改这里，到达或被替换后由 Render 应用。
        Vector3 position;
        Quaternion rotation;

        // 进行中的加载。BreakLoad 靠它停止协程。
        Coroutine loading;

        // 协程中途的产物。打断时要跟着一起收尾。
        AssetBundleCreateRequest bundleRequest;
        AssetBundle bundle;

        public TestAsyncGameObject(string bundlePath, string assetName)
        {
            this.bundlePath = bundlePath;
            this.assetName = assetName;
            position = Vector3.zero;
            rotation = Quaternion.identity;
            loading = null;
            bundleRequest = null;
            bundle = null;
        }

        // 只修改镜像。生效由后续的 SetActive(true) 统一提交。
        public void SetPose(Vector3 position, Quaternion rotation)
        {
            this.position = position;
            this.rotation = rotation;
        }

        // 开始使用时调一次。完成后由协程交付。
        protected override void Load()
        {
            loading = CoroutineHost.Start(LoadRoutine());
        }

        // 停止使用时调一次。尚未开始或已经结束时什么都不做。
        protected override void BreakLoad()
        {
            if (loading == null)
                return;

            CoroutineHost.Stop(loading);
            loading = null;
            Discard();
        }

        protected override void Free(object raw)
        {
            GameObject instance = raw as GameObject;
            if (instance != null)
                UnityEngine.Object.Destroy(instance);
        }

        // 整个生命期内不变的修改放这里。与兄弟的挂接由父组的 OnActive 负责，这里不碰。
        // 结束分支为空：本类的 Free 直接销毁实例，开始时做的改动无处可退。
        // 改成归还对象池之后，这里要把 SetParent 和 localScale 退回去。
        protected override void OnActive(object raw, bool active)
        {
            GameObject instance = raw as GameObject;
            if (instance == null || !active)
                return;

            instance.transform.SetParent(null, false);
            instance.transform.localScale = Vector3.one;
        }

        protected override void Render(object raw)
        {
            GameObject instance = raw as GameObject;
            if (instance == null)
                return;

            instance.transform.localPosition = position;
            instance.transform.localRotation = rotation;
        }

        IEnumerator LoadRoutine()
        {
            bundleRequest = AssetBundle.LoadFromFileAsync(bundlePath);
            yield return bundleRequest;

            bundle = bundleRequest.assetBundle;
            bundleRequest = null;
            if (bundle == null)
            {
                loading = null;
                Debug.LogError("TestAsyncGameObject 打不开 bundle " + bundlePath);
                yield break;
            }

            AssetBundleRequest assetRequest = bundle.LoadAssetAsync<GameObject>(assetName);
            yield return assetRequest;

            GameObject prefab = assetRequest.asset as GameObject;

            // 实例从 prefab 复制出来之后本节点不再需要 bundle。false 保留已加载的 asset。
            bundle.Unload(false);
            bundle = null;

            if (prefab == null)
            {
                loading = null;
                Debug.LogError("TestAsyncGameObject 在 " + bundlePath + " 里找不到 " + assetName);
                yield break;
            }

            GameObject instance = UnityEngine.Object.Instantiate(prefab);

            // 先清句柄，再交出结果。交付时会开始生命期并通知上层，其中可能再次 SetActive。
            loading = null;
            OnLoadDone(instance);
        }

        // 打断时底层 IO 取消不了。等它自己结束，然后把结果收尾掉。
        void Discard()
        {
            if (bundleRequest != null)
            {
                AssetBundleCreateRequest broken = bundleRequest;
                bundleRequest = null;
                broken.completed += _ =>
                {
                    AssetBundle arrived = broken.assetBundle;
                    if (arrived != null)
                        arrived.Unload(true);
                };
            }

            if (bundle != null)
            {
                bundle.Unload(true);
                bundle = null;
            }
        }
    }
}
