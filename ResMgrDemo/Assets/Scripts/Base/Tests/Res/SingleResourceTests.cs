using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 单个资源 x 的完整生命期。
    public class SingleResourceTests
    {
        [Test]
        public void FullLifecycle()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");

            x.SetActive(true);
            Sequence(log, "x", Load);
            Assert.IsFalse(x.IsLoaded());

            x.Complete();
            Sequence(log, "x", Load, On("x#1"), Render("x#1"));
            Assert.IsTrue(x.IsLoaded());

            // 已加载后再次使用，只提交镜像。
            x.SetActive(true);
            Sequence(log, "x", Load, On("x#1"), Render("x#1"), Render("x#1"));

            x.SetActive(false);
            Sequence(log, "x", Load, On("x#1"), Render("x#1"), Render("x#1"), Off("x#1"), Free("x#1"));
            Assert.IsFalse(x.IsLoaded());
            Symmetric(log, true);
        }

        [Test]
        public void RepeatedCallsDoNotRepeatLifecycle()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");

            x.SetActive(true);
            x.SetActive(true);
            x.Complete();
            x.SetActive(false);
            x.SetActive(false);

            Sequence(log, "x", Cycle("x#1"));
            Symmetric(log, true);
        }

        [Test]
        public void StopWhileLoading()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");

            x.SetActive(true);
            x.SetActive(false);

            Sequence(log, "x", Load, BreakLoad);
            Assert.IsFalse(x.IsPending);
            Assert.IsFalse(x.IsLoaded());
            Symmetric(log, true);
        }

        [Test]
        public void EachUseIsANewLifetime()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");

            for (int i = 0; i < 2; i++)
            {
                x.SetActive(true);
                x.Complete();
                x.SetActive(false);
            }

            Sequence(log, "x", Concat(Cycle("x#1"), Cycle("x#2")));
            Symmetric(log, true);
        }

        [Test]
        public void SyncLoadDeliversInsideSetActive()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x", true, true);

            x.SetActive(true);
            Sequence(log, "x", Load, On("x#1"), Render("x#1"));

            x.SetActive(false);
            Sequence(log, "x", Cycle("x#1"));
            Symmetric(log, true);
        }

        // 底层加载取消不了：停用后才到达的结果直接 Free，不开始生命期。
        [Test]
        public void LateResultIsFreedWithoutLifetime()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x", false, false);

            x.SetActive(true);
            x.SetActive(false);
            x.Complete();

            Sequence(log, "x", Load, BreakLoad, Free("x#1"));
            Assert.IsFalse(x.IsLoaded());
            Assert.That(log.LifetimesOf("x").Count, Is.EqualTo(0));
        }
    }
}
