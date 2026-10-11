using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 只有一级的成组资源 G{a, b}，G 没有上层。
    public class OneLevelGroupTests
    {
        [TestCase("a", "b")]
        [TestCase("b", "a")]
        public void FullLifecycle(string first, string second)
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);
            TestLeaf firstLeaf = first == "a" ? a : b;
            TestLeaf secondLeaf = second == "a" ? a : b;

            g.SetActive(true);
            Sequence(log, "G", Load);
            Sequence(log, "a", Load);
            Sequence(log, "b", Load);
            // 使用自上而下：G 先 Load，再拉起子资源。
            Before(log, "G", Load, "a", Load);
            Before(log, "G", Load, "b", Load);

            firstLeaf.Complete();
            // 子资源到达即开始生命期；G 未齐，不交付。
            Sequence(log, first, Load, On(first + "#1"), Render(first + "#1"));
            Sequence(log, "G", Load);

            secondLeaf.Complete();
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));
            Assert.IsTrue(g.IsLoaded());

            g.SetActive(false);
            Sequence(log, "G", Cycle("{a,b}"));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            // 开始自下而上，结束自上而下。
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
            Assert.IsFalse(g.IsLoaded() || a.IsLoaded() || b.IsLoaded());
        }

        [Test]
        public void StopAfterPartialArrival()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);

            g.SetActive(true);
            a.Complete();
            g.SetActive(false);

            // G 没有生命期可结束；已到达的 a 结束生命期，未到达的 b 被打断。
            Sequence(log, "G", Load, BreakLoad);
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Load, BreakLoad);
            Before(log, "G", BreakLoad, "a", Off("a#1"));
            Before(log, "G", BreakLoad, "b", BreakLoad);
            Symmetric(log, true);
            Assert.IsFalse(b.IsPending);
        }

        [Test]
        public void StopBeforeAnyArrival()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);

            g.SetActive(true);
            g.SetActive(false);

            Sequence(log, "G", Load, BreakLoad);
            Sequence(log, "a", Load, BreakLoad);
            Sequence(log, "b", Load, BreakLoad);
            Before(log, "G", BreakLoad, "a", BreakLoad);
            Before(log, "G", BreakLoad, "b", BreakLoad);
            Symmetric(log, true);
        }

        [Test]
        public void EachUseIsANewLifetime()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);

            for (int i = 0; i < 2; i++)
            {
                g.SetActive(true);
                a.Complete();
                b.Complete();
                g.SetActive(false);
            }

            Sequence(log, "G", Concat(Cycle("{a,b}"), Cycle("{a,b}")));
            Sequence(log, "a", Concat(Cycle("a#1"), Cycle("a#2")));
            Sequence(log, "b", Concat(Cycle("b#1"), Cycle("b#2")));
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
        }

        // 子资源命中缓存，G 在 SetActive(true) 之内就交付。
        [Test]
        public void SyncChildrenDeliverInsideSetActive()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a", true, true);
            TestLeaf b = new TestLeaf(log, "b", true, true);
            TestGroup g = new TestGroup(log, "G", a, b);

            g.SetActive(true);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));

            g.SetActive(false);
            Sequence(log, "G", Cycle("{a,b}"));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
        }

        // Render 不级联：对已加载的 G 再次使用，只提交 G 自身的镜像。
        [Test]
        public void CommitOnLoadedGroupRendersOnlyTheGroup()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);

            g.SetActive(true);
            a.Complete();
            b.Complete();
            g.SetActive(true);

            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"));
            Sequence(log, "a", Load, On("a#1"), Render("a#1"));
            Sequence(log, "b", Load, On("b#1"), Render("b#1"));

            g.SetActive(false);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"));
            Symmetric(log, true);
        }

        // G 在自己的 Render 里显式提交子资源 a 的镜像；这不改变 a 的使用计数。
        [Test]
        public void RenderCommitsChildExplicitly()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetRenderHook(group =>
            {
                a.SetData("pose");
                a.SetActive(true);
            });

            g.SetActive(true);
            a.Complete();
            b.Complete();
            Sequence(log, "a", Load, On("a#1"), Render("a#1"), Render("a#1"));

            g.SetActive(false);
            Sequence(log, "a", Load, On("a#1"), Render("a#1"), Render("a#1"), Off("a#1"), Free("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "G", Cycle("{a,b}"));
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
        }

        // G 在自己的 Render 里停用自己：生命期照样成对，子资源只被放开一次。
        [Test]
        public void GroupStopsItselfInRender()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a", true, true);
            TestGroup g = new TestGroup(log, "G", a);
            g.SetRenderHook(group => group.SetActive(false));

            g.SetActive(true);

            Sequence(log, "G", Cycle("{a}"));
            Sequence(log, "a", Cycle("a#1"));
            Nested(log, "a", "G");
            Symmetric(log, true);
            Assert.IsFalse(g.IsLoaded() || a.IsLoaded());
        }

        [Test]
        public void EmptyGroupDeliversAtOnce()
        {
            LifecycleLog log = new LifecycleLog();
            TestGroup e = new TestGroup(log, "E");

            e.SetActive(true);
            Sequence(log, "E", Load, On("{}"), Render("{}"));

            e.SetActive(false);
            Sequence(log, "E", Cycle("{}"));
            Symmetric(log, true);
        }
    }
}
