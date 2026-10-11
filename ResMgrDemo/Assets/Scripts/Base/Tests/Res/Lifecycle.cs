using System.Collections.Generic;
using NUnit.Framework;

namespace Base.Res.Tests
{
    // 调用的书写形式，用来拼期望的序列。
    public static class Calls
    {
        public const string Load = "Load";
        public const string BreakLoad = "BreakLoad";

        public static string On(string raw)
        {
            return "OnActive(true, " + raw + ")";
        }

        public static string Render(string raw)
        {
            return "Render(" + raw + ")";
        }

        public static string Off(string raw)
        {
            return "OnActive(false, " + raw + ")";
        }

        public static string Free(string raw)
        {
            return "Free(" + raw + ")";
        }

        // 一次完整的使用：加载、开始生命期、Render、结束生命期、释放。
        public static string[] Cycle(string raw)
        {
            return new string[] { Load, On(raw), Render(raw), Off(raw), Free(raw) };
        }

        public static string[] Concat(params string[][] parts)
        {
            List<string> result = new List<string>();
            foreach (string[] part in parts)
                result.AddRange(part);
            return result.ToArray();
        }
    }

    // 生命期的断言。失败时附上全部调用。
    public static class LifecycleAssert
    {
        // 生命期的阶段，见 Symmetric。
        enum Phase
        {
            Idle,
            Loading,
            Activated,
            Alive,
            Ended,
            Freed,
        }

        // 节点自己的调用恰好是这个序列，不多不少。
        public static void Sequence(LifecycleLog log, string node, params string[] expected)
        {
            Assert.That(log.Of(node), Is.EqualTo(expected), node + " 的调用序列不符\n" + log);
        }

        // 每个节点的调用都合乎生命期，开始与结束成对：
        // Load 之后要么被 BreakLoad 打断，要么交付；交付时 OnActive(true) 紧跟 Render；
        // 此后只有同一个 raw 的 Render，直到 OnActive(false)，再 Free 同一个 raw。
        // Free 之后，要么是成组资源的替换（另一个 raw 的 OnActive(true)），要么是新的使用周期（Load）。
        // ended 为真时，每个节点最后都没有生命期。
        public static void Symmetric(LifecycleLog log, bool ended)
        {
            foreach (string node in log.Nodes())
            {
                List<Call> calls = log.CallsOf(node);
                Phase phase = Phase.Idle;
                string raw = null;
                for (int i = 0; i < calls.Count; i++)
                {
                    Phase before = phase;
                    if (!Advance(ref phase, ref raw, calls[i]))
                        Assert.Fail(node + " 的第 " + (i + 1) + " 次调用 " + calls[i] + " 不合生命期，此前处于 " + before + "\n" + log);
                }
                if (ended && phase != Phase.Idle && phase != Phase.Freed)
                    Assert.Fail(node + " 的生命期没有结束，停在 " + phase + "\n" + log);
            }
        }

        // lower 的生命期包住 upper 的每一次生命期：
        // lower 先开始并 Render，upper 才开始；upper 先结束并 Free，lower 才结束。
        public static void Nested(LifecycleLog log, string lower, string upper)
        {
            List<Lifetime> lowers = log.LifetimesOf(lower);
            List<Lifetime> uppers = log.LifetimesOf(upper);
            Assert.That(uppers.Count, Is.GreaterThan(0), upper + " 没有生命期\n" + log);
            foreach (Lifetime u in uppers)
            {
                Lifetime l = null;
                foreach (Lifetime candidate in lowers)
                {
                    if (candidate.On < u.On && (candidate.Off < 0 || candidate.Off > u.On))
                        l = candidate;
                }
                Assert.IsNotNull(l, upper + " 开始生命期时，" + lower + " 不在生命期内\n" + log);
                Assert.IsTrue(l.FirstRender >= 0 && l.FirstRender < u.On,
                    lower + " 要先 Render，" + upper + " 才开始生命期\n" + log);
                if (l.Off >= 0)
                {
                    Assert.IsTrue(u.Off >= 0 && u.Off < l.Off, upper + " 要先结束生命期，" + lower + " 才结束\n" + log);
                    Assert.IsTrue(u.Free >= 0 && u.Free < l.Off, upper + " 要先 Free，" + lower + " 才结束生命期\n" + log);
                }
            }
        }

        // nodeA 的 callA 先于 nodeB 的 callB 发生。
        public static void Before(LifecycleLog log, string nodeA, string callA, string nodeB, string callB)
        {
            int a = log.IndexOf(nodeA, callA);
            int b = log.IndexOf(nodeB, callB);
            Assert.IsTrue(a >= 0, nodeA + "." + callA + " 没有发生\n" + log);
            Assert.IsTrue(b >= 0, nodeB + "." + callB + " 没有发生\n" + log);
            Assert.IsTrue(a < b, nodeA + "." + callA + " 要先于 " + nodeB + "." + callB + "\n" + log);
        }

        // 按这次调用推进阶段。返回 false 表示这次调用在当前阶段不合法。
        static bool Advance(ref Phase phase, ref string raw, Call call)
        {
            switch (phase)
            {
                case Phase.Idle:
                    if (call.Kind != CallKind.Load)
                        return false;
                    phase = Phase.Loading;
                    return true;
                case Phase.Loading:
                    if (call.Kind == CallKind.BreakLoad)
                    {
                        phase = Phase.Idle;
                        return true;
                    }
                    if (call.Kind != CallKind.ActiveOn)
                        return false;
                    phase = Phase.Activated;
                    raw = call.Raw;
                    return true;
                case Phase.Activated:
                    if (call.Kind != CallKind.Render || call.Raw != raw)
                        return false;
                    phase = Phase.Alive;
                    return true;
                case Phase.Alive:
                    if (call.Kind == CallKind.Render && call.Raw == raw)
                        return true;
                    if (call.Kind != CallKind.ActiveOff || call.Raw != raw)
                        return false;
                    phase = Phase.Ended;
                    return true;
                case Phase.Ended:
                    if (call.Kind != CallKind.Free || call.Raw != raw)
                        return false;
                    phase = Phase.Freed;
                    raw = null;
                    return true;
                default:
                    if (call.Kind == CallKind.Load)
                    {
                        phase = Phase.Loading;
                        return true;
                    }
                    if (call.Kind != CallKind.ActiveOn)
                        return false;
                    phase = Phase.Activated;
                    raw = call.Raw;
                    return true;
            }
        }
    }
}
