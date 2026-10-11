using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 共享子资源的资源树：一个子资源被多个成组资源包含。
    public class SharedChildTests
    {
        // G1{s}、G2{s}，两种停用顺序。
        [TestCase(true)]
        [TestCase(false)]
        public void TwoGroupsShareOneChild(bool stopG1First)
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s);
            TestGroup stoppedFirst = stopG1First ? g1 : g2;
            TestGroup stoppedLast = stopG1First ? g2 : g1;

            g1.SetActive(true);
            g2.SetActive(true);
            // 共享子资源只加载一次。
            Sequence(log, "s", Load);

            s.Complete();
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Sequence(log, "G1", Load, On("{s}"), Render("{s}"));
            Sequence(log, "G2", Load, On("{s}"), Render("{s}"));

            stoppedFirst.SetActive(false);
            // 一个上层停用，共享子资源继续存活。
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Assert.IsTrue(s.IsLoaded());
            Assert.IsTrue(stoppedLast.IsLoaded());

            stoppedLast.SetActive(false);
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "G1", Cycle("{s}"));
            Sequence(log, "G2", Cycle("{s}"));
            Nested(log, "s", "G1");
            Nested(log, "s", "G2");
            Before(log, stoppedLast.Name, Free("{s}"), "s", Off("s#1"));
            Symmetric(log, true);
        }

        // G1{s} 已加载，G2{s, t} 后加入：s 不重复 Load，也不重复 Render。
        [Test]
        public void SecondGroupJoinsAfterChildLoaded()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestLeaf t = new TestLeaf(log, "t");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s, t);

            g1.SetActive(true);
            s.Complete();
            g2.SetActive(true);
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Sequence(log, "t", Load);
            Sequence(log, "G2", Load);

            t.Complete();
            Sequence(log, "G2", Load, On("{s,t}"), Render("{s,t}"));

            g2.SetActive(false);
            // G1 仍在使用 s。
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Sequence(log, "t", Cycle("t#1"));

            g1.SetActive(false);
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "G1", Cycle("{s}"));
            Sequence(log, "G2", Cycle("{s,t}"));
            Nested(log, "s", "G1");
            Nested(log, "s", "G2");
            Nested(log, "t", "G2");
            Symmetric(log, true);
        }

        // 同一棵树里的共享 R{G1{s}, G2{s}}。
        [Test]
        public void SharedInsideOneTree()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s);
            TestGroup r = new TestGroup(log, "R", g1, g2);

            r.SetActive(true);
            Sequence(log, "s", Load);

            s.Complete();
            Sequence(log, "R", Load, On("{G1,G2}"), Render("{G1,G2}"));

            r.SetActive(false);
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "G1", Cycle("{s}"));
            Sequence(log, "G2", Cycle("{s}"));
            Sequence(log, "R", Cycle("{G1,G2}"));
            Nested(log, "s", "G1");
            Nested(log, "s", "G2");
            Nested(log, "G1", "R");
            Nested(log, "G2", "R");
            Nested(log, "s", "R");
            // s 在两个上层都放开之后才结束。
            Before(log, "G1", Free("{s}"), "s", Off("s#1"));
            Before(log, "G2", Free("{s}"), "s", Off("s#1"));
            Symmetric(log, true);
        }

        // G2{s, t} 还在等 t 时停用：t 被打断，G1 仍在使用的 s 不受影响。
        [Test]
        public void StopLoadingGroupKeepsSharedChild()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestLeaf t = new TestLeaf(log, "t");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s, t);

            g1.SetActive(true);
            s.Complete();
            g2.SetActive(true);
            g2.SetActive(false);

            Sequence(log, "G2", Load, BreakLoad);
            Sequence(log, "t", Load, BreakLoad);
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Assert.IsTrue(g1.IsLoaded());

            g1.SetActive(false);
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "G1", Cycle("{s}"));
            Symmetric(log, true);
        }

        // G1{s} 先停用，G2{s, t} 还在等 t：G2 对 s 的计数让 s 继续存活。
        [Test]
        public void FirstGroupStopsWhileSecondWaits()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestLeaf t = new TestLeaf(log, "t");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s, t);

            g1.SetActive(true);
            s.Complete();
            g2.SetActive(true);
            g1.SetActive(false);
            Sequence(log, "G1", Cycle("{s}"));
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));

            t.Complete();
            Sequence(log, "G2", Load, On("{s,t}"), Render("{s,t}"));

            g2.SetActive(false);
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "t", Cycle("t#1"));
            Sequence(log, "G2", Cycle("{s,t}"));
            Nested(log, "s", "G1");
            Nested(log, "s", "G2");
            Nested(log, "t", "G2");
            Symmetric(log, true);
        }

        // 两个组都在等 s：一个组停用，s 的加载不被打断；最后一个组停用才打断。
        [Test]
        public void SharedChildKeepsLoadingWhileAnyGroupWaits()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestGroup g1 = new TestGroup(log, "G1", s);
            TestGroup g2 = new TestGroup(log, "G2", s);

            g1.SetActive(true);
            g2.SetActive(true);
            g1.SetActive(false);
            Sequence(log, "G1", Load, BreakLoad);
            Sequence(log, "s", Load);
            Assert.IsTrue(s.IsPending);

            g2.SetActive(false);
            Sequence(log, "G2", Load, BreakLoad);
            Sequence(log, "s", Load, BreakLoad);
            Symmetric(log, true);
        }

        // c1 当场交付，c2 已由 G0 加载。G{c1, c2} 交付前必须已计上 c2：
        // G 在自己的 Render 里停用 G0，c2 也不能随之停用。
        [Test]
        public void GroupCountsEveryChildBeforeDelivering()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf c1 = new TestLeaf(log, "c1", true, true);
            TestLeaf c2 = new TestLeaf(log, "c2");
            TestGroup g0 = new TestGroup(log, "G0", c2);
            g0.SetActive(true);
            c2.Complete();

            TestGroup g = new TestGroup(log, "G", c1, c2);
            g.SetRenderHook(group => g0.SetActive(false));
            g.SetActive(true);

            Sequence(log, "G", Load, On("{c1,c2}"), Render("{c1,c2}"));
            Sequence(log, "G0", Cycle("{c2}"));
            Sequence(log, "c2", Load, On("c2#1"), Render("c2#1"));
            Assert.IsTrue(c2.IsLoaded());

            g.SetActive(false);
            Sequence(log, "G", Cycle("{c1,c2}"));
            Sequence(log, "c1", Cycle("c1#1"));
            Sequence(log, "c2", Cycle("c2#1"));
            Nested(log, "c2", "G0");
            Nested(log, "c2", "G");
            Nested(log, "c1", "G");
            Symmetric(log, true);
        }
    }
}
