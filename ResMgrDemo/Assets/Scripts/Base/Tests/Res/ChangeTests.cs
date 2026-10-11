using System.Collections.Generic;
using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 使用中增删子资源：增删只换批、改计数，不激活、不交付；提交时激活新的成员，到齐后替换。
    // 替换由没有被联系的最上一级发起，自上而下就位。
    public class ChangeTests
    {
        // 使用中的增删不触发任何调用：加入又删掉、还没提交过的子资源，即使命中缓存也不加载。
        [Test]
        public void EditsOnUsedGroupTriggerNothing()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestLeaf d = new TestLeaf(log, "d", true, true);
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();
            string before = log.ToString();

            g.RemoveChild(b);
            g.AddChild(c);
            g.AddChild(d);
            g.RemoveChild(d);
            Assert.That(log.ToString(), Is.EqualTo(before), "使用中的增删不应触发任何调用");

            g.SetActive(true);
            Sequence(log, "c", Load);
            Sequence(log, "d");

            c.Complete();
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a,c}"), Render("{a,c}"));
            Sequence(log, "b", Cycle("b#1"));

            g.SetActive(false);
            Symmetric(log, true);
        }

        // 换一个子资源：先删后加、先加后删，c 都在提交时才激活，到达时替换一次。
        [TestCase(true)]
        [TestCase(false)]
        public void SwapChild(bool removeFirst)
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            if (removeFirst)
            {
                g.RemoveChild(b);
                g.AddChild(c);
            }
            else
            {
                g.AddChild(c);
                g.RemoveChild(b);
            }
            Sequence(log, "c");

            g.SetActive(true);
            // c 到达之前，G 照常使用旧的一批。
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"));
            Sequence(log, "b", Load, On("b#1"), Render("b#1"));
            Sequence(log, "c", Load);

            c.Complete();
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a,c}"), Render("{a,c}"));
            Sequence(log, "a", Load, On("a#1"), Render("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "c", Load, On("c#1"), Render("c#1"));
            Before(log, "G", Off("{a,b}"), "b", Off("b#1"));
            Before(log, "c", Render("c#1"), "G", On("{a,c}"));

            g.SetActive(false);
            Sequence(log, "G", Concat(
                new string[] { Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}") },
                new string[] { On("{a,c}"), Render("{a,c}"), Off("{a,c}"), Free("{a,c}") }));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "c", Cycle("c#1"));
            Nested(log, "a", "G");
            Symmetric(log, true);
        }

        // c 命中缓存：两种顺序都在提交时替换一次，没有只剩 {a} 或 {a,b,c} 的中间状态。
        [TestCase(true)]
        [TestCase(false)]
        public void SwapWithSyncChild(bool removeFirst)
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c", true, true);
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            if (removeFirst)
            {
                g.RemoveChild(b);
                g.AddChild(c);
            }
            else
            {
                g.AddChild(c);
                g.RemoveChild(b);
            }
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));
            Sequence(log, "c");

            g.SetActive(true);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a,c}"), Render("{a,c}"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "c", Load, On("c#1"), Render("c#1"));
            Before(log, "c", Render("c#1"), "G", On("{a,c}"));

            g.SetActive(false);
            Nested(log, "a", "G");
            Before(log, "G", Free("{a,c}"), "c", Off("c#1"));
            Symmetric(log, true);
        }

        // 只删不增：没有子资源到达来触发，靠提交生效。
        [Test]
        public void PureRemovalTakesEffectOnCommit()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            g.RemoveChild(b);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));
            Sequence(log, "b", Load, On("b#1"), Render("b#1"));

            g.SetActive(true);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a}"), Render("{a}"));
            Sequence(log, "b", Cycle("b#1"));
            Before(log, "G", Free("{a,b}"), "b", Off("b#1"));

            g.SetActive(false);
            Sequence(log, "a", Cycle("a#1"));
            Symmetric(log, true);
        }

        // 改回正在用的一批：提交时不重建，子资源不受影响。
        [Test]
        public void RevertDoesNotRebuild()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            g.RemoveChild(b);
            g.AddChild(b);
            g.SetActive(true);

            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"));
            Sequence(log, "a", Load, On("a#1"), Render("a#1"));
            Sequence(log, "b", Load, On("b#1"), Render("b#1"));

            g.SetActive(false);
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"));
            Symmetric(log, true);
        }

        // 提交过、还在加载的子资源又被删掉：删掉它的那次增删就停用它。
        [Test]
        public void AbandonedChildStopsAtEdit()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestLeaf d = new TestLeaf(log, "d");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            g.AddChild(c);
            g.SetActive(true);
            Sequence(log, "c", Load);

            g.AddChild(d);
            g.RemoveChild(c);
            Sequence(log, "c", Load, BreakLoad);
            Assert.IsFalse(c.IsPending);
            Sequence(log, "d");

            g.SetActive(true);
            Sequence(log, "d", Load);

            d.Complete();
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a,b,d}"), Render("{a,b,d}"));

            g.SetActive(false);
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "d", Cycle("d#1"));
            Symmetric(log, true);
        }

        // 新的一批还没齐时停用：旧的一批结束生命期，已激活的新子资源停止加载。
        [Test]
        public void StopWhilePending()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestGroup g = new TestGroup(log, "G", a, b);
            g.SetActive(true);
            a.Complete();
            b.Complete();

            g.AddChild(c);
            g.SetActive(true);
            g.SetActive(false);

            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "c", Load, BreakLoad);
            Before(log, "G", Off("{a,b}"), "a", Off("a#1"));
            Symmetric(log, true);
        }

        // 不在使用时增删只改镜像；开始使用时加载最新的一批。
        [Test]
        public void EditsOnUnusedGroupOnlyChangeMirror()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestGroup g = new TestGroup(log, "G", a, b);

            g.RemoveChild(b);
            g.AddChild(c);
            Assert.That(log.Nodes().Count, Is.EqualTo(0), "不在使用时增删不应触发任何调用\n" + log);

            g.SetActive(true);
            a.Complete();
            c.Complete();
            Sequence(log, "G", Load, On("{a,c}"), Render("{a,c}"));
            Sequence(log, "b");

            g.SetActive(false);
            Symmetric(log, true);
        }

        // 嵌套 R{s, G{a, b}}，G 换成 {a, c} 并提交：只重建从根到 G 的路径，兄弟 s 不再 Render。
        [Test]
        public void InnerChangeRebuildsPathOnly()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf s = new TestLeaf(log, "s");
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestGroup g = new TestGroup(log, "G", a, b);
            TestGroup r = new TestGroup(log, "R", s, g);
            r.SetActive(true);
            a.Complete();
            b.Complete();
            s.Complete();

            g.RemoveChild(b);
            g.AddChild(c);
            g.SetActive(true);
            Sequence(log, "R", Load, On("{G,s}"), Render("{G,s}"));
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"));
            Sequence(log, "c", Load);

            c.Complete();
            Sequence(log, "R", Load, On("{G,s}"), Render("{G,s}"), Off("{G,s}"), Free("{G,s}"), On("{G,s}"), Render("{G,s}"));
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"), On("{a,c}"), Render("{a,c}"));
            Sequence(log, "s", Load, On("s#1"), Render("s#1"));
            Sequence(log, "a", Load, On("a#1"), Render("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Sequence(log, "c", Load, On("c#1"), Render("c#1"));

            // R 先结束，G 结束旧的一批，b 结束；G 开始新的一批并 Render，R 才重新开始。
            List<Lifetime> rLives = log.LifetimesOf("R");
            List<Lifetime> gLives = log.LifetimesOf("G");
            Assert.IsTrue(rLives[0].Off < gLives[0].Off, "R 要先结束，G 的旧一批才结束\n" + log);
            Assert.IsTrue(gLives[0].Off < log.IndexOf("b", Off("b#1")), "G 拆掉旧联系之后 b 才结束\n" + log);
            Assert.IsTrue(gLives[1].FirstRender < rLives[1].On, "G 的新一批先 Render，R 才重新开始\n" + log);

            Before(log, "c", Render("c#1"), "G", On("{a,c}"));

            r.SetActive(false);
            Nested(log, "s", "R");
            Nested(log, "G", "R");
            Nested(log, "a", "G");
            Symmetric(log, true);
        }

        // 左子树的变化不让右子树重建：R{L{x, y}, Rt{z}}，L 去掉 y。
        [Test]
        public void SiblingSubtreeIsNotRebuilt()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");
            TestLeaf y = new TestLeaf(log, "y");
            TestLeaf z = new TestLeaf(log, "z");
            TestGroup left = new TestGroup(log, "L", x, y);
            TestGroup right = new TestGroup(log, "Rt", z);
            TestGroup r = new TestGroup(log, "R", left, right);
            r.SetActive(true);
            x.Complete();
            y.Complete();
            z.Complete();

            left.RemoveChild(y);
            left.SetActive(true);

            Sequence(log, "L", Load, On("{x,y}"), Render("{x,y}"), Render("{x,y}"), Off("{x,y}"), Free("{x,y}"), On("{x}"), Render("{x}"));
            Sequence(log, "R", Load, On("{L,Rt}"), Render("{L,Rt}"), Off("{L,Rt}"), Free("{L,Rt}"), On("{L,Rt}"), Render("{L,Rt}"));
            Sequence(log, "Rt", Load, On("{z}"), Render("{z}"));
            Sequence(log, "z", Load, On("z#1"), Render("z#1"));
            Sequence(log, "y", Cycle("y#1"));

            r.SetActive(false);
            Nested(log, "Rt", "R");
            Nested(log, "z", "Rt");
            Symmetric(log, true);
        }

        // 两级同时增删：角色 P{W{l, r}, body} 换身体，翅膀 W 换右翼，各自提交。
        // W 的新一批先齐，但整个 P 的新状态要等 body2；两处改动在 body2 到达时一起生效。
        [Test]
        public void TwoLevelsChangeTogether()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf l = new TestLeaf(log, "l");
            TestLeaf rightWing = new TestLeaf(log, "r");
            TestLeaf newRightWing = new TestLeaf(log, "r2", true, true);
            TestLeaf body = new TestLeaf(log, "body");
            TestLeaf body2 = new TestLeaf(log, "body2");
            TestGroup w = new TestGroup(log, "W", l, rightWing);
            TestGroup p = new TestGroup(log, "P", w, body);
            p.SetActive(true);
            l.Complete();
            rightWing.Complete();
            body.Complete();

            p.RemoveChild(body);
            p.AddChild(body2);
            p.SetActive(true);
            w.RemoveChild(rightWing);
            w.AddChild(newRightWing);
            w.SetActive(true);

            // 角色照常显示旧身体、旧右翼。
            Sequence(log, "P", Load, On("{W,body}"), Render("{W,body}"), Render("{W,body}"));
            Sequence(log, "W", Load, On("{l,r}"), Render("{l,r}"), Render("{l,r}"));
            Sequence(log, "r", Load, On("r#1"), Render("r#1"));
            Sequence(log, "body", Load, On("body#1"), Render("body#1"));
            Sequence(log, "body2", Load);

            body2.Complete();
            Sequence(log, "P", Load, On("{W,body}"), Render("{W,body}"), Render("{W,body}"), Off("{W,body}"), Free("{W,body}"), On("{W,body2}"), Render("{W,body2}"));
            Sequence(log, "W", Load, On("{l,r}"), Render("{l,r}"), Render("{l,r}"), Off("{l,r}"), Free("{l,r}"), On("{l,r2}"), Render("{l,r2}"));
            Sequence(log, "r", Cycle("r#1"));
            Sequence(log, "body", Cycle("body#1"));
            Sequence(log, "l", Load, On("l#1"), Render("l#1"));
            Sequence(log, "r2", Load, On("r2#1"), Render("r2#1"));

            List<Lifetime> pLives = log.LifetimesOf("P");
            List<Lifetime> wLives = log.LifetimesOf("W");
            Assert.IsTrue(pLives[0].Off < wLives[0].Off, "P 要先结束，W 的旧一批才结束\n" + log);
            Assert.IsTrue(wLives[1].FirstRender < pLives[1].On, "W 的新一批先 Render，P 才重新开始\n" + log);

            p.SetActive(false);
            Nested(log, "W", "P");
            Nested(log, "l", "W");
            Symmetric(log, true);
        }

        // 两个子成组资源都有新的一批：根只重建一次，等两者都就位才重新开始。
        [Test]
        public void TwoChildGroupsChangeBeforeOneRebuild()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf a2 = new TestLeaf(log, "a2");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf b2 = new TestLeaf(log, "b2");
            TestGroup g1 = new TestGroup(log, "G1", a);
            TestGroup g2 = new TestGroup(log, "G2", b);
            TestGroup r = new TestGroup(log, "R", g1, g2);
            r.SetActive(true);
            a.Complete();
            b.Complete();

            g1.AddChild(a2);
            g1.SetActive(true);
            g2.AddChild(b2);
            g2.SetActive(true);
            a2.Complete();
            // G1 的新一批已齐，但 G2 的还没齐，R 不重建。
            Sequence(log, "R", Load, On("{G1,G2}"), Render("{G1,G2}"));

            b2.Complete();
            Sequence(log, "R", Load, On("{G1,G2}"), Render("{G1,G2}"), Off("{G1,G2}"), Free("{G1,G2}"), On("{G1,G2}"), Render("{G1,G2}"));
            Sequence(log, "G1", Load, On("{a}"), Render("{a}"), Render("{a}"), Off("{a}"), Free("{a}"), On("{a,a2}"), Render("{a,a2}"));
            Sequence(log, "G2", Load, On("{b}"), Render("{b}"), Render("{b}"), Off("{b}"), Free("{b}"), On("{b,b2}"), Render("{b,b2}"));

            r.SetActive(false);
            Nested(log, "G1", "R");
            Nested(log, "G2", "R");
            Symmetric(log, true);
        }

        // 外层移除一个还有新一批在等的子资源：子资源随之停用，它的新一批一起放弃。
        [Test]
        public void OuterRemovesPendingChild()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf a = new TestLeaf(log, "a");
            TestLeaf b = new TestLeaf(log, "b");
            TestLeaf c = new TestLeaf(log, "c");
            TestGroup g = new TestGroup(log, "G", a, b);
            TestGroup p = new TestGroup(log, "P", g);
            p.SetActive(true);
            a.Complete();
            b.Complete();

            g.AddChild(c);
            g.SetActive(true);
            p.RemoveChild(g);
            p.SetActive(true);

            Sequence(log, "P", Load, On("{G}"), Render("{G}"), Render("{G}"), Off("{G}"), Free("{G}"), On("{}"), Render("{}"));
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"), Render("{a,b}"), Off("{a,b}"), Free("{a,b}"));
            Sequence(log, "c", Load, BreakLoad);
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Before(log, "P", Free("{G}"), "G", Off("{a,b}"));

            p.SetActive(false);
            Symmetric(log, true);
        }
    }
}
