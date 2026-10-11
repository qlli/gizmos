using System.Collections.Generic;
using System.Text;

namespace Base.Res.Tests
{
    // 生命期调用的种类。BreakLoad 只在确有加载被打断时才记。
    public enum CallKind
    {
        Load,
        BreakLoad,
        ActiveOn,
        Render,
        ActiveOff,
        Free,
    }

    // 一次调用：哪个节点、哪种调用、作用在哪个 raw 上。
    public sealed class Call
    {
        public readonly string Node;
        public readonly CallKind Kind;
        public readonly string Raw;

        public Call(string node, CallKind kind, string raw)
        {
            Node = node;
            Kind = kind;
            Raw = raw;
        }

        public override string ToString()
        {
            switch (Kind)
            {
                case CallKind.Load:
                    return Calls.Load;
                case CallKind.BreakLoad:
                    return Calls.BreakLoad;
                case CallKind.ActiveOn:
                    return Calls.On(Raw);
                case CallKind.Render:
                    return Calls.Render(Raw);
                case CallKind.ActiveOff:
                    return Calls.Off(Raw);
                default:
                    return Calls.Free(Raw);
            }
        }
    }

    // 一个节点的一次生命期。各字段是对应调用在全体调用中的位置，没有发生的为 -1。
    public sealed class Lifetime
    {
        public readonly string Raw;
        public readonly int On;
        public int FirstRender;
        public int Off;
        public int Free;

        public Lifetime(string raw, int on)
        {
            Raw = raw;
            On = on;
            FirstRender = -1;
            Off = -1;
            Free = -1;
        }
    }

    // 按发生顺序记下全部节点的生命期调用。
    public sealed class LifecycleLog
    {
        List<Call> calls;

        public LifecycleLog()
        {
            calls = new List<Call>();
        }

        public void Add(string node, CallKind kind, string raw)
        {
            calls.Add(new Call(node, kind, raw));
        }

        // 出现过的节点，按第一次出现的顺序。
        public List<string> Nodes()
        {
            List<string> nodes = new List<string>();
            foreach (Call call in calls)
            {
                if (!nodes.Contains(call.Node))
                    nodes.Add(call.Node);
            }
            return nodes;
        }

        public List<Call> CallsOf(string node)
        {
            List<Call> result = new List<Call>();
            foreach (Call call in calls)
            {
                if (call.Node == node)
                    result.Add(call);
            }
            return result;
        }

        // 某个节点全部调用的书写形式，按发生顺序，用来与期望的序列比较。
        public List<string> Of(string node)
        {
            List<string> result = new List<string>();
            foreach (Call call in CallsOf(node))
                result.Add(call.ToString());
            return result;
        }

        // 某个节点第一次发生这次调用的位置；没有发生时为 -1。
        public int IndexOf(string node, string call)
        {
            for (int i = 0; i < calls.Count; i++)
            {
                if (calls[i].Node == node && calls[i].ToString() == call)
                    return i;
            }
            return -1;
        }

        // 某个节点的各次生命期。停用后才到达、直接 Free 的结果不算生命期。
        public List<Lifetime> LifetimesOf(string node)
        {
            List<Lifetime> result = new List<Lifetime>();
            Lifetime current = null;
            for (int i = 0; i < calls.Count; i++)
            {
                Call call = calls[i];
                if (call.Node != node)
                    continue;
                switch (call.Kind)
                {
                    case CallKind.ActiveOn:
                        current = new Lifetime(call.Raw, i);
                        result.Add(current);
                        break;
                    case CallKind.Render:
                        if (current != null && current.FirstRender < 0)
                            current.FirstRender = i;
                        break;
                    case CallKind.ActiveOff:
                        if (current != null && current.Off < 0)
                            current.Off = i;
                        break;
                    case CallKind.Free:
                        if (current != null && current.Off >= 0 && current.Free < 0)
                            current.Free = i;
                        break;
                }
            }
            return result;
        }

        public override string ToString()
        {
            StringBuilder text = new StringBuilder("全部调用：\n");
            for (int i = 0; i < calls.Count; i++)
                text.Append("  ").Append(i).Append(' ').Append(calls[i].Node).Append('.').Append(calls[i]).Append('\n');
            return text.ToString();
        }
    }
}
