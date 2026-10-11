using System.Collections;
using UnityEngine;

namespace Engine.Resource
{
    // 协程宿主。Base 层不轮询引擎、不提供驱动器，异步加载的驱动放在这里。
    public class CoroutineHost : MonoBehaviour
    {
        static CoroutineHost instance;

        public static Coroutine Start(IEnumerator routine)
        {
            if (routine == null)
                return null;
            return Host().StartCoroutine(routine);
        }

        // 协程已经自己跑完时，停止是空操作。
        public static void Stop(Coroutine routine)
        {
            if (routine == null || instance == null)
                return;
            instance.StopCoroutine(routine);
        }

        static CoroutineHost Host()
        {
            if (instance != null)
                return instance;

            GameObject holder = new GameObject("CoroutineHost");
            holder.hideFlags = HideFlags.HideAndDontSave;
            Object.DontDestroyOnLoad(holder);
            instance = holder.AddComponent<CoroutineHost>();
            return instance;
        }
    }
}
