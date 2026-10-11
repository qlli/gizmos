using System;
using NUnit.Framework;
using static Base.Res.Tests.Calls;
using static Base.Res.Tests.LifecycleAssert;

namespace Base.Res.Tests
{
    // 拷贝与引用：拷贝在使用时登记在模板上，模板在最后一份拷贝停用后才停用。
    public class CloneTests
    {
        [Test]
        public void TwoCopiesShareTemplate()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf t = new TestLeaf(log, "T");
            TestCopy c1 = new TestCopy(log, "C1", t);
            TestCopy c2 = new TestCopy(log, "C2", t);

            c1.SetActive(true);
            c2.SetActive(true);
            Sequence(log, "T", Load);

            t.Complete();
            Sequence(log, "C1", Load, On("C1<T#1>#1"), Render("C1<T#1>#1"));
            Sequence(log, "C2", Load, On("C2<T#1>#1"), Render("C2<T#1>#1"));
            Before(log, "T", Render("T#1"), "C1", On("C1<T#1>#1"));

            c1.SetActive(false);
            Sequence(log, "T", Load, On("T#1"), Render("T#1"));

            c2.SetActive(false);
            Sequence(log, "T", Cycle("T#1"));
            Nested(log, "T", "C1");
            Nested(log, "T", "C2");
            Symmetric(log, true);
        }

        [Test]
        public void CopyOfLoadedTemplateDeliversAtOnce()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf t = new TestLeaf(log, "T");
            TestCopy c1 = new TestCopy(log, "C1", t);
            TestCopy c2 = new TestCopy(log, "C2", t);
            c1.SetActive(true);
            t.Complete();

            c2.SetActive(true);
            Sequence(log, "C2", Load, On("C2<T#1>#1"), Render("C2<T#1>#1"));
            Sequence(log, "T", Load, On("T#1"), Render("T#1"));

            c1.SetActive(false);
            c2.SetActive(false);
            Symmetric(log, true);
        }

        [Test]
        public void StopCopyBeforeTemplateArrives()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf t = new TestLeaf(log, "T");
            TestCopy c = new TestCopy(log, "C", t);

            c.SetActive(true);
            c.SetActive(false);

            Sequence(log, "C", Load, BreakLoad);
            Sequence(log, "T", Load, BreakLoad);
            Assert.IsFalse(t.IsPending);
            Symmetric(log, true);
        }

        [Test]
        public void ReferenceSharesTemplateRaw()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf t = new TestLeaf(log, "T");
            TestRef r1 = new TestRef(t);
            TestRef r2 = new TestRef(t);

            r1.SetActive(true);
            r2.SetActive(true);
            t.Complete();
            Assert.That(r1.CurrentRaw, Is.SameAs(t.CurrentRaw));
            Assert.That(r2.CurrentRaw, Is.SameAs(t.CurrentRaw));

            r1.SetActive(false);
            Sequence(log, "T", Load, On("T#1"), Render("T#1"));

            r2.SetActive(false);
            Sequence(log, "T", Cycle("T#1"));
            Symmetric(log, true);
        }

        // 成组资源包含拷贝 G{C}：开始的顺序是 T、C、G，拆除的顺序是 G、C、T。
        [Test]
        public void GroupContainingCopy()
        {
            LifecycleLog log = new LifecycleLog();
            TestLeaf t = new TestLeaf(log, "T");
            TestCopy c = new TestCopy(log, "C", t);
            TestGroup g = new TestGroup(log, "G", c);

            g.SetActive(true);
            t.Complete();
            Sequence(log, "G", Load, On("{C}"), Render("{C}"));

            g.SetActive(false);
            Sequence(log, "T", Cycle("T#1"));
            Sequence(log, "C", Cycle("C<T#1>#1"));
            Sequence(log, "G", Cycle("{C}"));
            Nested(log, "T", "C");
            Nested(log, "C", "G");
            Symmetric(log, true);
        }

        [Test]
        public void TemplateMustBeSingleResource()
        {
            LifecycleLog log = new LifecycleLog();
            TestGroup g = new TestGroup(log, "G");
            Assert.Throws<ArgumentException>(() => new TestRef(g));
            Assert.Throws<ArgumentNullException>(() => new TestRef(null));
        }
    }
}
