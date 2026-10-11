using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 嵌套的资源树 R{s, G{a, b}}。
    public class NestedTreeTests
    {
        // 三个叶子的全部到达顺序。
        [TestCase("a", "s", "b")]
        [TestCase("a", "b", "s")]
        [TestCase("s", "a", "b")]
        [TestCase("s", "b", "a")]
        [TestCase("b", "a", "s")]
        [TestCase("b", "s", "a")]
        public void FullLifecycle(string first, string second, string third)
        {
            Tree t = new Tree();
            LifecycleLog log = t.Log;

            t.R.SetActive(true);
            foreach (string node in new string[] { "R", "G", "s", "a", "b" })
                Sequence(log, node, Load);
            // 使用自上而下，逐级拉起。
            Before(log, "R", Load, "s", Load);
            Before(log, "R", Load, "G", Load);
            Before(log, "G", Load, "a", Load);
            Before(log, "G", Load, "b", Load);

            t.Leaf(first).Complete();
            t.Leaf(second).Complete();
            // G 齐了就交付，不等兄弟节点 s；R 要等全部叶子。
            if (third == "s")
                Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));
            else
                Sequence(log, "G", Load);
            Sequence(log, "R", Load);

            t.Leaf(third).Complete();
            Sequence(log, "G", Load, On("{a,b}"), Render("{a,b}"));
            Sequence(log, "R", Load, On("{G,s}"), Render("{G,s}"));

            t.R.SetActive(false);
            Sequence(log, "R", Cycle("{G,s}"));
            Sequence(log, "G", Cycle("{a,b}"));
            Sequence(log, "s", Cycle("s#1"));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Nested(log, "s", "R");
            Nested(log, "G", "R");
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Nested(log, "a", "R");
            Nested(log, "b", "R");
            Symmetric(log, true);
        }

        // G 已装配，s 还在加载时停用 R。
        [Test]
        public void StopWhenSubtreeAssembledAndSiblingLoading()
        {
            Tree t = new Tree();
            LifecycleLog log = t.Log;

            t.R.SetActive(true);
            t.A.Complete();
            t.B.Complete();
            t.R.SetActive(false);

            Sequence(log, "R", Load, BreakLoad);
            Sequence(log, "s", Load, BreakLoad);
            Sequence(log, "G", Cycle("{a,b}"));
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Cycle("b#1"));
            Before(log, "R", BreakLoad, "s", BreakLoad);
            Before(log, "R", BreakLoad, "G", Off("{a,b}"));
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
        }

        // 只有最深处的 a 到达时停用 R。
        [Test]
        public void StopWhenOnlyDeepLeafArrived()
        {
            Tree t = new Tree();
            LifecycleLog log = t.Log;

            t.R.SetActive(true);
            t.A.Complete();
            t.R.SetActive(false);

            Sequence(log, "R", Load, BreakLoad);
            Sequence(log, "G", Load, BreakLoad);
            Sequence(log, "s", Load, BreakLoad);
            Sequence(log, "a", Cycle("a#1"));
            Sequence(log, "b", Load, BreakLoad);
            Before(log, "R", BreakLoad, "G", BreakLoad);
            Before(log, "G", BreakLoad, "a", Off("a#1"));
            Before(log, "G", BreakLoad, "b", BreakLoad);
            Symmetric(log, true);
        }

        [Test]
        public void EachUseIsANewLifetime()
        {
            Tree t = new Tree();
            LifecycleLog log = t.Log;

            for (int i = 0; i < 2; i++)
            {
                t.R.SetActive(true);
                t.A.Complete();
                t.S.Complete();
                t.B.Complete();
                t.R.SetActive(false);
            }

            Sequence(log, "R", Concat(Cycle("{G,s}"), Cycle("{G,s}")));
            Sequence(log, "G", Concat(Cycle("{a,b}"), Cycle("{a,b}")));
            Sequence(log, "s", Concat(Cycle("s#1"), Cycle("s#2")));
            Sequence(log, "a", Concat(Cycle("a#1"), Cycle("a#2")));
            Sequence(log, "b", Concat(Cycle("b#1"), Cycle("b#2")));
            Nested(log, "s", "R");
            Nested(log, "G", "R");
            Nested(log, "a", "G");
            Nested(log, "b", "G");
            Symmetric(log, true);
        }

        // 四层的链 R{G1{G2{x}}}：开始自下而上逐级，结束自上而下逐级。
        [Test]
        public void DeepChain()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf x = new TestLeaf(log, "x");
            TestGroup g2 = new TestGroup(log, "G2", x);
            TestGroup g1 = new TestGroup(log, "G1", g2);
            TestGroup r = new TestGroup(log, "R", g1);

            r.SetActive(true);
            Before(log, "R", Load, "G1", Load);
            Before(log, "G1", Load, "G2", Load);
            Before(log, "G2", Load, "x", Load);

            x.Complete();
            Sequence(log, "R", Load, On("{G1}"), Render("{G1}"));

            r.SetActive(false);
            Sequence(log, "x", Cycle("x#1"));
            Sequence(log, "G2", Cycle("{x}"));
            Sequence(log, "G1", Cycle("{G2}"));
            Sequence(log, "R", Cycle("{G1}"));
            Nested(log, "x", "G2");
            Nested(log, "G2", "G1");
            Nested(log, "G1", "R");
            Nested(log, "x", "R");
            Symmetric(log, true);
        }

        sealed class Tree
        {
            public readonly LifecycleLog Log;
            public readonly TestLeaf S;
            public readonly TestLeaf A;
            public readonly TestLeaf B;
            public readonly TestGroup G;
            public readonly TestGroup R;

            public Tree()
            {
                Log = new LifecycleLog();
                S = new TestLeaf(Log, "s");
                A = new TestLeaf(Log, "a");
                B = new TestLeaf(Log, "b");
                G = new TestGroup(Log, "G", A, B);
                R = new TestGroup(Log, "R", S, G);
            }

            public TestLeaf Leaf(string name)
            {
                if (name == "s")
                    return S;
                return name == "a" ? A : B;
            }
        }
    }
}
