# 资源生命期伪代码（临时）

推敲与实现都以本文件为准。流程有调整时，先改这里，再改代码。

当前范围：

- 不考虑在已装配的树里单独停用内部节点。
- 不考虑加载失败。
- 只考虑同步的拷贝。异步的拷贝（例如从 bundle 中取 asset）不在范围内。
- 拷贝的模板只能是单个资源。成组资源的地址拷贝，就是把它作为子资源加入别的成组资源。

## 1. 不变式

### 1.1 前提与概念

**前提。**

- 资源树的叶子节点都是单个资源，例如模型、贴图、特效。它只有一个 raw，不会被替换。
- 非叶节点都是成组资源。它的 raw 是子资源集合，可以被替换。
- 增删子资源，先改逻辑上的镜像；替换实际的 raw，前提是本资源没有与父兄资源建立联系。

**上层与下层。** 一个资源的上层，是需要它的 raw 的一方。上层有三种：

- 框架外的上层代码；
- 包含它的成组资源；
- 以它为模板的拷贝。

反过来，成组资源的子资源、拷贝的模板，是它们的下层。单个资源没有下层。

上层对下层只做几件事：计数（需要它）、放开（不再需要它）、激活或停用它、等它交付。凡是关于某个下层的步骤（加载、开始生命期、渲染、释放、替换），都由下层自己的方法完成；上层只发出这些消息，只接收下层的通知。

**计数只记账。** 框架内的上层（成组资源、拷贝）登记在下层的 `dependents` 里，登记一次就是对下层计一次数。`dependents` 是多重集合，同一个上层可以计多次。`AddDependent`、`RemoveDependent` 只改这份记录，不激活、不停用，也不检查。

- 拷贝在使用时对模板计一次。
- 成组资源在使用时按批计数：每一批对自己的每个成员各计一次（见下文「批」）。
- 成组资源按地址使用每个子资源的 raw，等同于每一批对每个子资源各持有一份地址拷贝，所以不需要 `Reference` 对象来代表这份拷贝。
- 多个成组资源共享同一个子资源，就是这个子资源有多个上层，不需要另外的机制。

激活与停用由计数的一方负责，两条规则对称：

- 上层在检查点激活它需要、却还没在使用的下层；
- 谁放开计数之后计数归零，谁就停用那个下层。

不需要使用的上层对象仍然存在，但不让下层存活：生命期属于 raw，不属于 Resource 对象。

**批。** 成组资源的子资源集合一批一批地更替。每一批是一个集合对象，生成后不再修改：

- `children`：最新的一批。每次 `AddChild`、`RemoveChild` 都换成一个新的集合对象。
- raw：在用的一批，即已建立联系、生命期进行中的那一批。它就是某一次交付时的 `children` 对象本身。

`children` 与 raw 是同一个对象时，本组没有待交付的状态；不是同一个对象时，称本组「待交付」。稳态时两者相同，每个子资源只计一次；待交付时两批各计一次，两批都有的子资源计两次，替换时计数不归零。批不修改，所以 raw 的成员在它的整个生命期里不变。

**检查点。** 增删只换批、改计数，不激活、不交付。交付只发生在检查点，即调用 `OnDependencyLoaded` 的时刻。检查点有四处：

1. 下层交付了，或者成组的下层就绪了，通知上层；
2. 上层放开了在用的一批，本组仍有计数：上层替换或停用时，让仍有计数的子成组资源检查一次；
3. 提交：对正在使用的资源调用 `SetActive(true)`；
4. 开始使用：`Load` 计数之后检查一次。

检查时，成组资源先激活最新一批里还没在使用的成员，再看能否交付。所以增删在本组的下一个检查点生效，增删加入的子资源也在那时才开始加载。增删本身不产生检查点：「增删……增删、提交」写在一起时，增删恰好在提交时生效。

**联系。** 成组资源 u 联系着子资源 x，当且仅当 x 在 u 的 raw 里。被某个上层联系着的资源，称为「已被联系」。拷贝的模板是单个资源，从不替换，不涉及联系。

**谓词。** 一个资源的状态用下面几个谓词描述，都由已有的字段推出：

| 谓词 | 含义 | 单个资源、拷贝 | 成组资源 |
| --- | --- | --- | --- |
| 有 raw | 生命期正在进行 | `raw != null` | `raw != null` |
| 待交付 | 最新的一批还不是 raw | 不涉及 | `children` 与 raw 不是同一个对象 |
| 最新 | raw 就是最新的状态 | `raw != null` | 有 raw、不待交付，且联系着的子资源都最新 |
| 已齐：`IsLoaded()` | 最新的状态现在就能就位 | `raw != null` | 有 raw，且最新的一批的成员都已齐 |

单个资源的谓词是同一件事。成组资源上它们分开，分开的方式正是 1.2 的不变式要约束的。不待交付、却有联系着的子成组资源待交付的成组资源，称为「陈旧」：它的成员没变，但要重建联系。

**抽象。** 上层把一个不是最新的下层，看作「要换成新版本的子资源」。翅膀 W 换了右翼，对角色 P 而言就是子资源 W 要换成新翅膀 W2。P 只问 W 是否已齐、是否待交付，不关心 W 内部如何轮转。

### 1.2 不变式

以下六条在每个检查点结束时成立，交付与替换的中途除外。前四条说一个资源自身，后两条说资源之间。

1. **不用就不占。** 不在使用时，没有 raw，不在加载，也不对任何下层计数。
2. **用着就要。** 在使用时，最新的状态所需要的每个下层都计着数，并且都在使用：成组资源最新的一批与在用的一批各对自己的成员计一次，拷贝对模板计一次。不是最新的，就一定在等：单个资源与拷贝等交付；成组资源等最新的一批到齐，或等联系它的上层重建。
3. **一份 raw，一次生命期。** 每次交付的 raw 恰好经历一次「开始 → 使用 → 结束 → 释放」：`OnActive(r, true)`、若干次 `Render(r)`、`OnActive(r, false)`、`Free(r)`。raw 字段只在开始与结束之间指向它，同一时刻至多一份 raw 在生命期内。停用之后才到达的 raw 不开始生命期，只释放。
4. **最新必已齐；已齐而未被联系，必最新。** 后半句说的是：能就位的都已就位。已齐而不是最新的，只能是被联系着的成组资源，它在等上层重建。
5. **需要即计数。** u 在 x 的 `dependents` 里出现的次数，等于 u 需要 x 的份数：u 是正在使用的成组资源时，x 在它的 raw 里计一次，x 在它待交付的最新一批里再计一次；u 是拷贝时，它在等交付或生命期正在进行，计一次。x 在使用，当且仅当有人需要它：根由上层代码需要，其余由 `dependents` 需要。计数与放开严格成对。
6. **下层包住上层。** 上层的一次生命期里联系着的每个下层，在这整段时间里都是同一份 raw 的生命期：比上层先开始，比上层后结束，中间不替换。

增删只换批、改计数，不激活、不交付，只停用计数归零的子资源。所以增删之后、本组的下一个检查点之前，有两处可以暂时不成立：增删加入的子资源计着数、却还没在使用（第 2、5 条），等检查点激活；已齐的新一批等检查点交付（第 4 条的后半句）。

### 1.3 从单个资源到成组资源、资源树

单个资源只有三种状态：不用（没有 raw，不加载）、在等（没有 raw，在加载）、在用（有 raw，不加载）。六条在三种资源上的样子：

| 不变式 | 单个资源 | 一级成组资源 | 资源树 |
| --- | --- | --- | --- |
| 1 不用就不占 | 停用即打断加载、结束生命期 | 另外放开最新的一批与在用的一批，停用计数归零的子资源 | 逐级成立：上层停用时放开下层，计数归零的下层随之停用 |
| 2 用着就要 | 在用与在等恰居其一 | 两批各计一次；可以既在用又在等 | 同一级成组资源 |
| 3 一份 raw 一次生命期 | 一个使用周期只有一份 raw | 一个使用周期可以有多份，前一份结束，后一份才开始 | 每个节点各自成立 |
| 4 最新必齐，齐而未被联系必最新 | 谓词都是 `raw != null`，自然成立 | 是根，从不被联系：已齐即在检查点交付 | 被联系的内层，可以已齐而未最新 |
| 5 需要即计数 | 作为子资源时成立 | 成立：检查时激活，计数归零时停用 | 成立；共享时一个下层有多个上层 |
| 6 下层包住上层 | 没有下层；作为下层，raw 本就不变 | 子资源都是单个资源，自然成立 | 靠「批不修改、被联系的成组资源不就地替换」成立 |

成组资源与资源树在三处放宽了单个资源的形态，都由前提推出：

- **既在用又在等**（第 2 条）。单个资源在用就不再等；成组资源可以一边用旧的一批、一边等新的一批。若先停用旧的再等新的，中间会有空窗；换装的中间状态（`Resource.md` 11.1 节）要求旧的照常使用。
- **一个使用周期多份 raw**（第 3 条）。同样来自可以替换。放宽的只是份数，每一份仍是完整的一次生命期，前后相接、不重叠。
- **已齐而未最新**（第 4 条）。只出现在被联系的内层：按第 6 条，被联系着的 raw 不能变，它只能等上层重建、放开联系着它的那一批时再就位。未被联系的成组资源，已齐就在检查点交付，与单个资源相同。

没有放宽的是第 1、5、6 条，以及第 3 条的「每份 raw 一次完整的生命期」。它们对三种资源一字不差地成立，是这套设计的骨架。

### 1.4 生命期顺序

由不变式 6 直接推出三种顺序。

**开始：下层先于上层。**

```text
child.OnActive(true)
child.Render()
parent.OnActive(true)
parent.Render()
```

**结束：上层先于下层。** 上层先拆联系、结束自身的生命期、释放，之后下层才可能结束生命期：

```text
parent.OnActive(false)
parent.Free()
child.OnActive(false)
```

两者的生命期不必同时结束：上层结束了，下层若还有别的上层，就继续存活。

**替换：由最上一级 P 发起，自上而下逐级就位。**

```text
P.OnActive(oldP, false)          # 拆掉 P 的旧联系
P.Free(oldP)                     # 放开旧的一批：计数归零的子资源停用，结束生命期；
                                 # 仍有计数的子成组资源检查一次，已不受 P 联系，新的一批就此就位：
    W.OnActive(oldW, false)
    W.Free(oldW)                 # 同一规则，逐级向下
    W.OnActive(newW, true)
    W.Render(newW)
                                 # W 就位后通知 P，P 的新一批已齐，就在这里开始：
    P.OnActive(newP, true)       # 按子资源的新版本建立 P 的新联系
    P.Render(newP)
```

P 的新一批在最后一个要就位的子资源就位时开始；没有要就位的子资源时，在 `Free` 之后开始。两种情况的调用顺序相同。

被联系的 W 不就地替换，否则 P 的生命期里 W 换了 raw，违反不变式 6；所以替换只能由「待交付、已齐、又没有被联系」的最上一级发起。新加入的子资源在 `P.OnActive(newP, true)` 之前已经开始生命期；两批都有的子资源，计数从不归零。被移除的子资源在 P 拆掉旧联系之后才结束，可能晚于 P 的新一批开始，这不违反不变式 6：它不在新的一批里。

### 1.5 方向

向上只传「交付或就绪」：`OnDependencyLoaded`。向下传两类消息：计数与放开（`AddDependent` / `RemoveDependent`，只记账），激活与停用（`SetActive`）。上层放开在用的一批时，让仍有计数的子成组资源检查一次，这就是「联系已拆」的通知，不需要另外的方法。任何方法都只看本节点和它的直接上下层，不回溯；「就绪」由每一级自己转给它的上层。

### 1.6 约束

1. 上层代码调用 `SetActive` 的规则：
    - `SetActive(false)` 只对没有上层的资源（根）调用。
    - 对还没使用的根调用 `SetActive(true)`，是使用。
    - 对正在被使用的资源调用 `SetActive(true)`，是提交：`Render` 它的镜像，再检查一次有没有可以就位的新状态。可以是有上层的内部节点。成组资源增删子资源后，紧接着这样提交：增删在本组的下一个检查点生效；隔帧才提交时，期间别的检查点（例如某个子资源到达、上层重建）会让增删提前生效。
    - 不要对还没被使用的内部节点调用 `SetActive(true)`：那会让它被直接使用，最后一个上层离开时又会把它停掉。上层代码要共享一个单个资源，就各自对它持有一份 `Reference`；要共享一个成组资源，就各自把它加入自己的成组资源。

    框架内部的上层在检查点激活下层、计数归零时停用下层，不受这几条规则限制。

2. 共享的资源（有多个上层）由使用者保证不可变：不改它的镜像，成组资源也不增删子资源。框架对此不做特殊处理，修改镜像时若发现本资源有多个上层，报警告；运行结果不保证。多个上层各自修改同一个共享资源时，后写者覆盖先写者；共享的成组资源增删子资源时，可能在某个上层的生命期里换了 raw（第 9 节）。

3. 成组资源在 `Render` 里只提交子资源的数据，不提交子资源的增删。子资源的增删由上层代码直接对那个成组资源 `SetActive(true)` 提交（7.4）。本组 `Render` 时正处在交付之中，子资源联系在本组的 raw 里：子资源的新一批若在这时就绪，就转告本组，本组在自己的 `Render` 里就要重建，一次交付引出第二次重建，而且重入。

4. 每个资源的 `OnActive(false)`，撤销它自己在 `OnActive(true)` 与 `Render` 里所做的全部修改。`OnActive(true)` 只放只做一次的初始化，每次都要按镜像重做的放在 `Render`。下层在它自己的 `Render` 里所做的修改归下层，由下层自己的 `OnActive(false)` 撤销：上层重建时撤销、重做的只是它自己的那一份，下层的生命期不中断，也不必再 `Render`。

## 2. 方法的语义边界

基类方法，所有资源共用，都不是虚方法：

| 方法 | 负责 | 不负责 |
| --- | --- | --- |
| `SetActive(on)` | 改 `active`。开始使用：`Load`。已在使用：提交，有 raw 就 `Render`，再检查一次。停止使用：`BreakLoad`，再结束生命期 | 不看其他节点 |
| `SetData(data)` | 只改镜像；本资源有多个上层时报警告 | 不提交 |
| `OnLoadDone(newRaw)` | 交付点：停用之后才到的直接 `Free`；持有 raw 时先结束旧 raw，放开途中新 raw 若已开始就到此为止；否则开始新 raw，`Render`，通知上层 | 不加载 |
| `AddDependent(d)` | 记一次需要：计一次数 | 不激活本资源 |
| `RemoveDependent(d)` | 去掉一次需要：放开一次 | 不停用本资源，也不检查 |

基类给出默认实现、由派生类覆盖的方法：

| 方法 | 基类（单个资源） | 成组资源 | 拷贝 |
| --- | --- | --- | --- |
| `IsLoaded()` | `raw != null` | 另要最新的一批都已齐 | 同基类 |
| `OnDependencyLoaded()` | 什么都不做 | 检查：陈旧就生成重建的一批；激活还没在使用的成员；已齐时，没有被联系就交付，被联系就转告上层 | 检查：模板没在使用就激活它；模板已加载、自己还没有 raw，就交付 |

派生类实现的方法。它们都不修改自己的 `raw` 和 `active`，这两个字段只由基类修改：

| 方法 | 单个资源 | 成组资源 | 拷贝 |
| --- | --- | --- | --- |
| `Load` | 启动加载，完成后 `OnLoadDone` 交付 | 最新的一批计数，再检查 | 对模板计数，再检查 |
| `BreakLoad` | 停止加载，回滚中间产物 | 最新的一批不是 raw 就放开，计数归零的停用 | 还没交付就放开模板，归零就停用 |
| `Free` | 销毁 raw | 放开这一批：计数归零的停用，仍有计数的子成组资源检查一次 | `DestroyClone(raw)`，再放开模板，归零就停用 |
| `OnActive` | 开始：只做一次的初始化；结束：撤销开始与 `Render` 所做的全部修改 | 开始：建立子资源之间的联系；结束：撤销本组在开始与 `Render` 里所做的全部修改 | 由具体拷贝实现，同单个资源 |
| `Render` | 应用自身镜像 | 应用自身镜像；要改用子资源时，显式地对子资源 `SetData`、`SetActive(true)`，不自动级联 | 由具体拷贝实现：应用自身镜像 |

成组资源的 `Load`、`BreakLoad`、`Free` 由 `ResourceGroup` 实现，`OnActive`、`Render` 留给具体的成组资源。拷贝的 `Load`、`BreakLoad`、`Free` 由 `Clone` 实现，`CreateClone`、`DestroyClone`、`OnActive`、`Render` 留给具体的拷贝。

成组资源另有两个公共方法：

| 方法 | 负责 | 不负责 |
| --- | --- | --- |
| `AddChild(child)` / `RemoveChild(child)` | 换成新的一批：在使用就对它计数；被取代的一批不是 raw 就放开，计数归零的子资源停用；新的一批与 raw 成员相同时直接用回 raw | 不激活、不交付 |

C# 里的可见性（`Base` 是单独的程序集，见 `Design.md` 第 4 节）：

- 要经由别的对象访问的，对程序集可见：`raw` 是 `protected internal`；`active`、`dependents`、`AddDependent`、`RemoveDependent` 是 `internal`。成组资源要读上层与子资源的 raw、子资源的 `active` 与 `dependents`，拷贝要读模板的 raw、`active` 与 `dependents`；派生类经由基类类型的引用访问不到 `protected` 成员。
- `IsLoaded` 是 `public virtual`，`OnDependencyLoaded` 是 `protected virtual`。成组资源转告上层、在 `Free` 里让子成组资源检查时，把对方转成 `ResourceGroup` 再调用；成组资源的上层只会是成组资源，因为拷贝的模板只能是单个资源。
- `OnLoadDone` 是 `protected`：派生类加载完成后调用它交付。
- `Load`、`BreakLoad`、`Free`、`OnActive`、`Render`、`CreateClone`、`DestroyClone` 是 `protected abstract`。
- `ResourceGroup`、`Clone` 是抽象类；`Reference` 是具体类。

警告用 C# 自带的 `System.Diagnostics.Trace.TraceWarning`，`Base` 不必引用 `UnityEngine`。它的输出交给 Trace 的监听器；Unity 控制台默认看不到，要看到时由 `Engine` 启动时加一个转到 `Debug.LogWarning` 的监听器，这一步先不做。

## 3. 伪代码

```text
Resource:
    data                                       # 镜像
    raw                                        # 非空当且仅当生命期正在进行
    active                                     # 唯一的状态标志：是否正被使用
    dependents                                 # 多重集合：上层的每一批需要本资源时各记一次

    SetActive(on):
        if on:
            if not active:                     # 开始使用
                active = true
                Load()
            else:                              # 提交
                if raw != null:
                    Render(raw)
                OnDependencyLoaded()           # 检查点：可能有可以就位的新状态
        else if active:                        # 停止使用
            active = false
            BreakLoad()
            if raw != null:
                oldRaw = raw
                OnActive(oldRaw, false)
                raw = null
                Free(oldRaw)

    SetData(data):                             # 只改镜像，由之后的 SetActive(true) 提交
        if dependents 里不止一个上层:
            Trace.TraceWarning("修改了共享的资源")   # 约束 2
        this.data = data

    AddDependent(d):                           # 上层的一批需要本资源：只记账
        dependents.add(d)

    RemoveDependent(d):                        # 上层的一批不再需要本资源：只记账
        断言 dependents 里有 d；去掉一次

    OnLoadDone(newRaw):                        # 交付点
        if not active:
            Free(newRaw)                       # 迟到的结果，只有单个资源会有
            return
        if raw != null:                        # 替换，只有没有被联系的成组资源会走到
            oldRaw = raw
            OnActive(oldRaw, false)            # 拆旧联系
            raw = null                         # 先置空再 Free：子资源据此看到「已不受本组联系」
            Free(oldRaw)                       # 仍有计数的子成组资源在这里就位，并通知本组
            if raw != null:
                return                         # 新的一批已在那次通知里开始了生命期
        OnActive(newRaw, true)
        raw = newRaw
        Render(raw)
        for d in dependents 中不同的上层:      # 遍历副本：上层检查时可能改动 dependents
            d.OnDependencyLoaded()

    # 虚方法与基类的默认实现
    IsLoaded(): return raw != null             # 有 raw，且最新的状态都已齐
    OnDependencyLoaded(): 什么都不做           # 检查点上的检查

    # 派生类实现
    Load()                                     # 开始使用时调一次：发起加载，完成后调 OnLoadDone
    BreakLoad()                                # 停止使用时调一次：打断加载，回滚 Load 的副作用
    Free(raw)                                  # 释放 raw，与交付对称
    OnActive(raw, on)                          # 开始：只做一次的初始化；结束：撤销开始与 Render 的全部修改
    Render(raw)                                # 按镜像修改 raw，可能重复调用

ResourceGroup : Resource:
    children                                   # 最新的一批。每次增删换成新的集合，原来的一批不改

    AddChild(child):
        断言 child != null，且不在 children 中
        if dependents 里不止一个上层: Trace.TraceWarning("修改了共享的资源")
        batch = children 的副本 ∪ {child}
        if raw 与 batch 成员相同:
            batch = raw                        # 改回在用的一批：用回它，不重建
        old = children
        children = batch
        if active:
            if batch 不是 raw:
                for c in batch: c.AddDependent(this)       # 新的一批计数；不激活，等检查点
            if old 不是 raw:
                for c in old:                              # 被取代、没在用的一批放开
                    c.RemoveDependent(this)
                    if c.dependents 为空: c.SetActive(false)   # 被放弃的子资源停用

    RemoveChild(child):
        断言 child 在 children 中
        同 AddChild，只是 batch = children 的副本 − {child}

    IsLoaded():
        if raw == null: return false
        return children 的每个成员都 IsLoaded()

    Load():                                    # 开始使用：最新的一批计数
        for c in children: c.AddDependent(this)
        OnDependencyLoaded()                   # 检查点：在这里激活成员

    BreakLoad():                               # 停止使用：没在用的最新一批放开；在用的一批由 Free 放开
        if children 不是 raw:
            for c in children:
                c.RemoveDependent(this)
                if c.dependents 为空: c.SetActive(false)

    Free(set):                                 # 放开这一批
        for c in set:
            c.RemoveDependent(this)
            if c.dependents 为空:
                c.SetActive(false)             # 不再需要：停用
            else if c 是成组资源:
                c.OnDependencyLoaded()         # 检查点：已不受本组联系，待交付的就此就位

    OnDependencyLoaded():
        if not active: return
        if children 就是 raw:
            if raw 里没有待交付的子成组资源: return          # 最新
            batch = raw 的副本                 # 陈旧：按原成员用新的一批，重建联系
            for c in batch: c.AddDependent(this)
            children = batch
        激活了成员 = false
        for c in children:                     # 激活最新一批里还没在使用的成员
            if not c.active:
                c.SetActive(true)
                激活了成员 = true
        if 激活了成员: return                  # 它们交付时会再通知本组
        for c in children:                     # 已齐？
            if not c.IsLoaded(): return
            if c 不在 raw 里，且 c 是待交付的成组资源: return  # 本组还没联系它：它要先就位
        if 某个上层的 raw 里有本组:            # 被联系：不能就地替换
            for u in dependents 中不同的成组资源: u.OnDependencyLoaded()   # 转告「就绪」
            return
        OnLoadDone(children)

    OnActive(set, true):  建立 set 中子资源之间的联系                   # 具体的成组资源实现
    OnActive(set, false): 撤销本组在 OnActive(set, true) 与 Render 里所做的全部修改
    Render(set):
        应用本组自身的镜像
        # 不级联。要改用某个子资源时，显式写出：
        #     child.SetData(…)
        #     child.SetActive(true)            # 子资源必已加载且正被使用，这一步只是提交
        # 只提交子资源的数据，不提交子资源的增删（约束 3）

Clone : Resource:
    template                                   # 构造后不再改变

    Clone(template):
        断言 template != null，且不是成组资源    # 成组资源的地址拷贝，就是把它加入别的成组资源

    Load():                                    # 开始使用：对模板计数
        template.AddDependent(this)
        OnDependencyLoaded()                   # 检查点：在这里激活模板

    BreakLoad():                               # 停止使用：还没交付就放开模板；已交付的由 Free 放开
        if raw == null:
            template.RemoveDependent(this)
            if template.dependents 为空: template.SetActive(false)

    Free(cloneRaw):                            # 先销毁拷贝，再放开模板：拷贝可能引用模板的内容
        DestroyClone(cloneRaw)
        template.RemoveDependent(this)
        if template.dependents 为空: template.SetActive(false)

    OnDependencyLoaded():
        if not active or raw != null: return
        if not template.active:
            template.SetActive(true)           # 激活模板；它交付时会再通知本拷贝
            return
        if template.IsLoaded():
            OnLoadDone(CreateClone(template.raw))

    CreateClone(templateRaw) → cloneRaw        # 派生类实现：拷贝方式；只考虑同步的拷贝
    DestroyClone(cloneRaw)                     # 派生类实现：与 CreateClone 成对
    OnActive(cloneRaw, on)                     # 派生类实现
    Render(cloneRaw)                           # 派生类实现

Reference : Clone:
    CreateClone(templateRaw): return templateRaw
    DestroyClone(cloneRaw):   什么都不做        # raw 属于模板，由模板 Free
    OnActive(cloneRaw, on):   什么都不做
    Render(cloneRaw):         什么都不做
```

成组资源与拷贝同构：都在开始使用时对下层计数，在检查点激活还没在使用的下层、看下层齐了没有，齐了就交付；放开计数后归零，就停用那个下层。区别只是下层有几个、交付什么；成组资源另外可以换批、替换 raw。

## 4. 各方法的流程

### 4.1 `Resource`

**`SetActive(on)`**：使用、提交、不使用的唯一入口，只看本节点。调用者有三处：

- 上层代码：对根使用、不使用；对正在被使用的资源提交镜像（约束 1）；
- 框架内的上层：检查时激活还没在使用的下层，放开计数后归零时停用下层；
- 成组资源的 `Render`：对子资源 `SetActive(true)`，提交镜像。

三个分支：

- 开始使用：`active = true`，`Load`。`Load` 每个使用周期只调一次。
- 提交：已在使用。有 raw 就 `Render`，把镜像立即应用到在用的 raw；再 `OnDependencyLoaded`，这是检查点：成组资源增删加入的子资源在这里激活，新的一批在这里交付或转告上层。单个资源没有可检查的，提交就是 `Render`。
- 停止使用：`active = false`，`BreakLoad`，再结束生命期：`OnActive(false)`、置空、`Free`。

重复调用无害：`SetActive(false)` 不在使用时什么都不做；`SetActive(true)` 已在使用时只是提交，没有新状态就只有 `Render`。所以停用前不必先看是否在使用，激活前却要看：对正在使用的资源 `SetActive(true)` 是提交，会 `Render`。

**`SetData(data)`**：只改镜像。本资源有多个上层时报警告：共享的资源应当不可变（约束 2）。一个上层的两批都计着本资源时，仍算一个上层。

**`AddDependent(d)` / `RemoveDependent(d)`**：只记账。计一次数、放开一次；没计过数就放开，是错误。是否激活、停用、检查，由调用者按情况决定（1.1 节「计数只记账」）。

**`OnLoadDone(newRaw)`**：所有资源唯一的交付点。

- `active` 为假：这是迟到的结果，直接 `Free`。只有单个资源会走到这里：成组资源与拷贝只在检查时交付，而检查先看 `active`。
- `raw` 非空：这是替换，只有没有被联系的成组资源会走到（不变式 6）。先结束旧 raw：`OnActive(false)`、置空、`Free`。`Free` 放开旧的一批，仍有计数的子成组资源在其中检查、就位，就位后通知本组；本组若因此已齐，就在那次通知里开始了新的一批。所以 `Free` 之后 raw 若已非空，就到此为止。
- `OnActive(true)` 先于 `raw = newRaw`，`OnActive(false)` 先于 `raw = null`：`raw` 非空的区间恰好夹在两次 `OnActive` 之间。
- 先 `Render`，再通知上层：本节点先开始使用，上层后开始生命期（1.4 节的开始顺序）。
- 通知时遍历不同上层的副本：一个上层计了两次也只通知一次；上层检查时可能停用别的上层，从而改动 `dependents`。

**`IsLoaded()`**：上层问下层的事。单个资源与拷贝：交付之后就已齐。成组资源见 4.2。

### 4.2 `ResourceGroup`

**`AddChild(child)` / `RemoveChild(child)`**：换批，分三步。

1. 生成新的一批：`children` 的副本，加上或去掉 `child`。它若与 raw 成员相同，就直接用 raw 这个对象：改回了在用的一批，不必重建，raw 的计数本来就在。
2. 换上新的一批。
3. 在使用时改计数。新的一批若不是 raw，对每个成员计一次数，只记账，不激活。被取代的一批若不是 raw，放开它的计数，计数归零的子资源停用：它们是之前的检查激活过、现在被放弃的子资源；从没激活过的，停用什么都不做。被取代的若是 raw，它还在用，留给替换时的 `Free` 放开。

增删不激活、不交付，也不产生检查点；增删加入的子资源在本组的下一个检查点激活。不在使用时，增删只换批。

**`IsLoaded()`**：有 raw，且最新的一批的成员都已齐，逐级递归。对上层来说，本组已齐就是「本组的最新状态可以就位」。

**`Load()`**：最新的一批计数，再检查一次，检查时激活成员。计数在激活之前全部完成，所以子资源同步交付、通知本组时，每个成员都已计上本组。空组当场交付空集。

**`BreakLoad()`**：停止使用。最新的一批若不是 raw（还没交付过，或者待交付），放开它的计数，计数归零的停用；raw 那一批由随后的 `Free` 放开。

**`Free(set)`**：放开这一批。计数归零的子资源停用；仍有计数的子成组资源检查一次：替换时它已不受本组联系，待交付而已齐的就此就位，这是替换时的逐级下探。单个资源与拷贝被放开而仍有计数时，没有可检查的。

**`OnDependencyLoaded()`**：检查点上的检查，分五步。

1. 不在使用：返回。
2. 不待交付时，看联系着的子成组资源有没有待交付的。没有，本组最新，返回。有，本组陈旧，要重建：按 raw 的成员生成新的一批，并对它计数。这也是换批：在用的一批在替换时放开，新的一批让仍需要的子资源计数不归零。
3. 激活最新一批里还没在使用的成员。激活了任何一个就返回：它们交付时会再通知本组，那时再看能否交付。
4. 看是否已齐：最新一批的每个成员都已齐；本组还没联系的子成组资源，还要不待交付。本组联系着的子成组资源只要已齐：它要等本组放开在用的一批才能就位。
5. 已齐时，若某个上层的 raw 里有本组，本组被联系，不能就地替换：转告每个上层「就绪」，自己不动。没有被联系：交付最新的一批。

第 4 步里，本组还没联系的子成组资源要不待交付：替换时本组放开在用的一批之后，几个仍需要的子成组资源依次就位，每个就位都通知本组。若第一个就位时本组就开始新的一批，后面那个还待交付的子成组资源就被联系上了，它就位不了，只能转告本组，本组再重建一次。

不需要「每个成员都已计上本组」这样的条件：计数总在激活之前完成，检查时最新的一批一定已经全部计上。

**`Render(set)`**：不级联。具体的成组资源要改用某个子资源时，在 `Render` 里显式地对它 `SetData`、`SetActive(true)`；只提交数据，不提交增删（约束 3）。

### 4.3 `Clone` 与 `Reference`

**`Clone`**：与成组资源同一个骨架，只是下层只有一个模板，交付的是 `CreateClone(template.raw)`。

- 模板是单个资源：它的 raw 在拷贝的生命期内不变，拷贝不必跟着模板重建。
- `Load` 同样先计数、再检查。检查时模板没在使用就激活它，然后返回；模板已加载就当场交付。
- `BreakLoad` 只在还没交付时放开模板；交付了的，由 `Free` 放开。放开后计数归零，就停用模板。每次计数恰好放开一次。
- `Free` 先 `DestroyClone`，再放开模板：拷贝可能引用模板的内容。

**`Reference`**：`CreateClone` 返回模板的 raw 本身，其余什么都不做。

- 它的用途是让上层代码共享一个单个资源：每个使用者各持一份引用，各自 `SetActive`。资源在最后一份引用停用时才停用。
- 上层代码若直接对共享资源 `SetActive(false)`，一个使用者停用就会停掉所有人，这正是约束 1 禁止的。
- 成组资源内部不需要 `Reference`：成组资源的一批直接包含资源 T，与包含 `Reference(T)` 计的是同一次数，后者只多出一层空步骤。

## 5. 单个资源

### 5.1 相关方法

单个资源只用基类与它自己的五个方法。它没有下层，不会被替换。

| 方法 | 单个资源的行为 |
| --- | --- |
| `SetActive(true)` | 未在使用：`Load`；已在使用：提交，有 raw 就 `Render` |
| `SetActive(false)` | `BreakLoad`；有 raw 就结束生命期：`OnActive(false)`、置空、`Free` |
| `Load` | 派生类：启动加载，完成后调 `OnLoadDone` |
| `OnLoadDone` | 交付：`OnActive(true)`、`Render`、通知上层；停用之后才到达：`Free` |
| `BreakLoad` | 派生类：停止加载，回滚中间产物；不在加载中时什么都不做 |
| `IsLoaded` | `raw != null` |
| `AddDependent` / `RemoveDependent` | 作为下层时只记账：由上层在检查点激活，计数归零时由放开的上层停用 |
| `OnDependencyLoaded` | 基类的默认实现，什么都不做：没有下层 |

### 5.2 生命期

```text
上层代码 X.SetActive(true)
├ X.active = true
└ X.Load()                                    # 启动加载

…… 加载完成
X.OnLoadDone(r)
├ X.active 为真；X.raw 为空
├ X.OnActive(r, true)                         # 生命期开始
├ X.raw = r
├ X.Render(r)                                 # 开始使用
└ 通知 X 的上层（若有）

已加载后，上层代码 X.SetData(…); X.SetActive(true)   # 提交镜像
├ X.Render(r)
└ X.OnDependencyLoaded() → 什么都不做

加载中提交：X.raw 为空 → 不 Render；镜像在交付时的 Render 里应用

上层代码 X.SetActive(false)
├ X.active = false
├ X.BreakLoad()                               # 加载中：停止并回滚；否则什么都不做
└ X.raw != null → X.OnActive(r, false) → X.raw = null → X.Free(r)

加载中停用：X.SetActive(false) → X.BreakLoad() 停止加载 → X.raw 为空 → 结束

停用之后才到达的结果（派生类取消不了底层加载时）
X.OnLoadDone(r) → X.active 为假 → X.Free(r)
```

派生类的约定：`Load` 每个使用周期只调一次，`BreakLoad` 在停止使用时调一次，一个使用周期至多交付一次。取消不了的加载，结果若在停用期间到达，就是迟到的结果；若下一个使用周期已经开始，`Load` 应当复用它，而不是再发起一次。

### 5.3 作为子资源

```text
成组资源 G 的一批对 X 计数：X.AddDependent(G)       # 只记账
G 检查时，X 还没在使用 → G 激活 X：X.SetActive(true) → 走 5.2 的使用

G 的一批放开 X：X.RemoveDependent(G)                # 只记账
├ 计数归零 → G 停用 X：X.SetActive(false) → 走 5.2 的停用
└ 仍有计数 → 什么都不做                             # X 的 raw 不变
```

### 5.4 推敲要点

- raw 只有 `null → r` 与 `r → null` 两种变化。一个使用周期只交付一次，`OnLoadDone` 的替换路径走不到。这就是前提里「单个资源不会被替换」。
- 迟到的结果只会出现在单个资源上。
- 作为子资源时，它由上层激活、停用；被放开而仍有计数，对它没有影响。它的镜像若被多个上层修改，`SetData` 报警告（约束 2）。

## 6. 只有一级的成组资源 G{a, b}

G 没有上层，子资源都是单个资源。下文用 S0、S1… 标记批，即集合对象本身；花括号里是它的成员。

### 6.1 相关方法

| 方法 | 一级成组资源里的作用 |
| --- | --- |
| `AddChild` / `RemoveChild` | 换批；在使用时对新的一批计数，放开被取代、没在用的一批，停用计数归零的子资源；不激活 |
| `SetActive(true)` | 未在使用：`Load`。已在使用：提交，`Render` 自身镜像，再检查 |
| `Load` | 最新的一批计数，再检查 |
| `OnDependencyLoaded` | 激活还没在使用的成员；待交付且已齐就交付。G 是根，从不被联系，也不会陈旧 |
| `OnLoadDone` | 首次交付：开始生命期；替换：先结束在用的一批，再开始新的一批 |
| `Free` | 放开在用的一批：计数归零的子资源停用 |
| `BreakLoad` | 停止使用时，放开没在用的最新一批，停用计数归零的 |
| `IsLoaded` | 有 raw，且最新的一批都已加载 |

### 6.2 使用、加载与交付

```text
G.children 是 S0 = {a, b}

上层代码 G.SetActive(true)
├ G.active = true
└ G.Load()
     ├ a.AddDependent(G); b.AddDependent(G)  # 只记账
     └ G.OnDependencyLoaded()
          ├ a 没在使用 → a.SetActive(true) → a.Load
          ├ b 没在使用 → b.SetActive(true) → b.Load
          └ 激活了成员 → 返回

a 到达：a.OnLoadDone(ra)
├ a.OnActive(ra, true); a.raw = ra; a.Render(ra)
└ G.OnDependencyLoaded() → 成员都在使用；b 尚未加载 → 返回

b 到达：b.OnLoadDone(rb)
├ b.OnActive(rb, true); b.raw = rb; b.Render(rb)
└ G.OnDependencyLoaded() → 都已加载；没有被联系
     └ G.OnLoadDone(S0)                       # S0 这个集合对象成为 raw
          ├ G.OnActive(S0, true)              # 建立 a、b 之间的联系
          ├ G.raw = S0
          └ G.Render(S0)                      # 应用 G 自身的镜像
```

子资源命中缓存、在激活时同步交付：交付通知 G，G 的检查接着激活其余成员；最后一个成员交付时的那次检查交付 G。计数在激活之前已全部完成。空组同理，当场交付空集。

### 6.3 提交数据

```text
上层代码 G.SetData(…); G.SetActive(true)
├ G.Render(S0)
└ G.OnDependencyLoaded() → 不待交付，联系着的子资源里没有成组资源 → 返回
```

`Render` 不级联：a、b 不重复 `Render`。要改用某个子资源，G 的 `Render` 里显式地对它 `SetData`、`SetActive(true)`。

### 6.4 增删子资源

换一个子资源：G 正在用 S0 = {a, b}，换成 {a, c}。a、b 各计 1 次。

```text
上层代码 G.RemoveChild(b)
├ 新的一批 S1 = {a}；G.children = S1
├ a.AddDependent(G)                            # a 计 2 次，只记账
└ 被取代的 S0 是 raw → 不放开

上层代码 G.AddChild(c)
├ 新的一批 S2 = {a, c}；G.children = S2
├ a.AddDependent(G); c.AddDependent(G)         # a 计 3 次，c 计 1 次；c 不激活
└ 被取代的 S1 不是 raw → a.RemoveDependent(G)  # a 计 2 次

# 两次增删都没有触发任何调用，G 照常使用 S0

上层代码 G.SetActive(true)                     # 提交
├ G.Render(S0)
└ G.OnDependencyLoaded() → c 没在使用 → c.SetActive(true) → c.Load → 返回

c 到达：c.OnActive(true); c.Render → G.OnDependencyLoaded() → 已齐，没有被联系
└ G.OnLoadDone(S2)                            # 持有 raw：替换
     ├ G.OnActive(S0, false)                  # 拆旧联系
     ├ G.raw = null
     ├ G.Free(S0)
     │    ├ a.RemoveDependent(G)              # a 计 1 次
     │    └ b.RemoveDependent(G) → 计数归零 → b.SetActive(false) → b.OnActive(false); b.Free
     ├ G.raw 仍为空 → 继续
     ├ G.OnActive(S2, true); G.raw = S2       # 建新联系
     └ G.Render(S2)
```

c 命中缓存时，提交时激活 c，c 当场交付、通知 G，G 就在这次提交里替换，同样只替换一次。先加后删结果相同：S1 = {a, b, c}，S2 = {a, c}，c 都在提交时才激活。a 的计数从未归零，生命期不中断；b 在 G 拆掉旧联系之后才结束；c 在 G 建新联系之前已经开始。

只删不增：G 正在用 S0 = {a, b}，换成 {a}。

```text
上层代码 G.RemoveChild(b)                     # S1 = {a}，a 计 2 次；没有检查点，G 照常使用 S0
上层代码 G.SetActive(true)                    # 提交
├ G.Render(S0)
└ G.OnDependencyLoaded() → 成员都在使用；待交付，已齐，没有被联系 → G.OnLoadDone(S1) → 替换：放开 S0，b 停用并结束
```

只删不增靠提交生效。提交时先 `Render` 旧 raw、再检查：同步替换时，旧 raw 与新 raw 各 `Render` 一次。

改回：G 正在用 S0 = {a, b}，先去掉 b、再加回 b。

```text
G.RemoveChild(b)  → S1 = {a}，a 计 2 次
G.AddChild(b)     → 新的一批与 raw 成员相同 → 直接用 S0，不计数；G.children = S0
                  → 被取代的 S1 不是 raw → 放开，a 计 1 次
G.SetActive(true) → G.Render(S0)；不待交付 → 不重建
```

放弃已激活的子资源：G 正在用 S0 = {a, b}。先加 c 并提交，c 开始加载；c 到达之前，又加 d、删 c，再提交。

```text
G.AddChild(c); G.SetActive(true) → S1 = {a, b, c}；提交时激活 c，c 开始加载
G.AddChild(d)     → S2 = {a, b, c, d}，d 只记账；放开 S1
G.RemoveChild(c)  → S3 = {a, b, d}；放开 S2 → c 计数归零 → c.SetActive(false) → c.BreakLoad 停止加载
G.SetActive(true) → 激活 d，d 开始加载
d 到达            → G 交付 S3：替换，放开 S0
```

c 被放弃时已在加载，删掉它的那次增删就停用它。这是增删唯一会触发的停用：c 没有被 G 联系，G 的生命期不受影响。若 c 在那之前从没被激活过（增删加入、还没到检查点又删掉），停用什么都不做。

### 6.5 停用

```text
已加载：上层代码 G.SetActive(false)            # 先上层后下层
├ G.active = false
├ G.BreakLoad() → children 就是 raw → 什么都不做
└ G.OnActive(S0, false); G.raw = null; G.Free(S0)
     ├ a.RemoveDependent(G) → 计数归零 → a.SetActive(false) → a.OnActive(ra, false); a.raw = null; a.Free(ra)
     └ b 同上

加载中（a 已到达，b 未到达）：上层代码 G.SetActive(false)
├ G.active = false
├ G.BreakLoad() → children 不是 raw（raw 为空）→ 放开 S0
│    ├ a.RemoveDependent(G) → 计数归零 → a.SetActive(false) → a 结束生命期并 Free
│    └ b.RemoveDependent(G) → 计数归零 → b.SetActive(false) → b.BreakLoad() 停止加载
└ G.raw 为空 → 结束

替换途中（raw 是 S0 = {a, b}，children 是 S2 = {a, c}，c 已激活、还在加载）：上层代码 G.SetActive(false)
├ G.BreakLoad() → 放开 S2：a 计 1 次；c 计数归零 → c.SetActive(false) → c 停止加载
└ G.OnActive(S0, false); G.raw = null; G.Free(S0) → a、b 计数归零，停用并结束生命期
```

### 6.6 推敲要点

- 一级成组资源是根，从不被联系，替换都是就地完成。
- 子资源都是单个资源，被放开而仍有计数时什么都不做。替换就是本组的「拆旧联系、放开旧的一批、建新联系」。
- 计数不断：新的一批先计数，被取代的一批后放开；在用的一批在替换时才放开。两批都有的子资源，生命期贯穿替换。
- 换装中间状态：新的一批交付之前，旧的一批照常使用。
- 增删只记账：不激活、不交付，也不产生检查点。先删后加、先加后删、新子资源同步与否，都只在提交时（或新子资源到达时）替换一次。
- 激活与停用对称：检查时激活还没在使用的成员；放开后计数归零的，由放开的一方停用。
- 每一批恰好放开一次：被取代而没在用的，当场放开；在用的，替换时由 `Free` 放开；停用时，没在用的最新一批由 `BreakLoad` 放开，在用的一批由 `Free` 放开。

## 7. 递归嵌套的资源树 R{s, G{a, b}}

R 是根，s 是单个资源，G 是内层成组资源。

### 7.1 相关方法

比一级成组资源多出的，是成组资源作为子资源时的几件事：

| 方法 | 嵌套里新增的作用 |
| --- | --- |
| `OnDependencyLoaded`（G）的「被联系」 | R 的 raw 里有 G：G 已齐也不能就地替换，向上转告「就绪」 |
| `OnDependencyLoaded`（R）的「陈旧」 | R 联系着的 G 待交付：R 按原成员生成重建的一批 |
| `OnDependencyLoaded`（R）的「已齐」 | 对 R 联系着的 G，只要 G 已齐；对 R 还没联系的 G，还要 G 不待交付 |
| `IsLoaded`（G） | G 有 raw，且 G 最新的一批都已齐：R 据此判断 G 的新状态能否就位 |
| `Free`（R） | R 替换时放开在用的一批，G 仍有计数，R 让 G 检查一次：G 已不受 R 联系，就此就位 |

### 7.2 使用、逐级加载与交付

到达顺序取 a、s、b：中间的兄弟节点 s 先于 G 齐备。

```text
上层代码 R.SetActive(true) → R.Load()
├ s.AddDependent(R); G.AddDependent(R)        # 只记账
└ R.OnDependencyLoaded() → 激活还没在使用的成员
     ├ s.SetActive(true) → s.Load
     ├ G.SetActive(true) → G.Load()
     │    ├ a.AddDependent(G); b.AddDependent(G)
     │    └ G.OnDependencyLoaded() → 激活 a、b：a.Load; b.Load → 返回
     └ 激活了成员 → 返回

a 到达 → a.OnActive(true); a.Render → G.OnDependencyLoaded() → b 尚未加载 → 返回
s 到达 → s.OnActive(true); s.Render → R.OnDependencyLoaded() → G 没有 raw，未齐 → 返回
b 到达 → b.OnActive(true); b.Render → G.OnDependencyLoaded() → 已齐，没有被联系（R 还没有 raw）
└ G.OnLoadDone({a, b})
     ├ G.OnActive({a, b}, true); G.raw = {a, b}; G.Render
     └ R.OnDependencyLoaded() → s、G 都已齐，G 不待交付
          └ R.OnLoadDone({G, s})
               └ R.OnActive({G, s}, true); R.raw = {G, s}; R.Render
```

首次装配自下而上增量完成：G 齐了就装配，不等兄弟 s，因为此时 R 还没联系 G。

### 7.3 内部节点的提交

```text
上层代码 G.SetData(…); G.SetActive(true)        # G 正被 R 使用：这是提交，不是使用
├ G.Render({a, b})
└ G.OnDependencyLoaded() → 不待交付 → 返回
```

只改数据不改联系，R 不受影响。

### 7.4 内层增删：就绪向上，重建向下

R{s, G{a, b}} 已加载，G 换成 {a, c}：

```text
上层代码 G.RemoveChild(b); G.AddChild(c)       # G 的新一批 {a, c}，只记账
上层代码 G.SetActive(true)                      # 提交
├ G.Render({a, b})
└ G.OnDependencyLoaded() → 激活 c：c.Load → 返回
# 在此期间 R、G 照常使用旧的状态

c 到达 → G.OnDependencyLoaded() → 待交付、已齐，但 R 的 raw 里有 G → 不能就地替换
└ R.OnDependencyLoaded()
     ├ 不待交付，但联系着的 G 待交付 → 陈旧：生成重建的一批 {G, s}，G、s 各再计一次
     ├ 成员都在使用；已齐：G 已齐（R 联系着它，不必不待交付）；s 已加载
     ├ 没有被联系：R 是根
     └ R.OnLoadDone(重建的一批)                 # 替换，成员没变
          ├ R.OnActive({G, s}, false)          # 拆掉 R 的旧联系
          ├ R.raw = null
          ├ R.Free(在用的一批 {G, s})
          │    ├ s.RemoveDependent(R) → 仍有计数 → 单个资源，什么都不做
          │    └ G.RemoveDependent(R) → 仍有计数 → R 让 G 检查：G.OnDependencyLoaded()
          │         └ 待交付、已齐，已不受 R 联系 → G.OnLoadDone({a, c})      # G 就地替换
          │              ├ G.OnActive({a, b}, false); G.raw = null
          │              ├ G.Free({a, b}) → a 仍有计数；b 计数归零 → b 停用并结束
          │              ├ G.OnActive({a, c}, true); G.raw = {a, c}; G.Render
          │              └ 通知 R → R.OnDependencyLoaded() → 已齐，G 不待交付，没有被联系
          │                   └ R.OnLoadDone(重建的一批)                       # 嵌套：R 在这里开始
          │                        ├ R.OnActive({G, s}, true)                 # 按 G 的新版本建立 R 的新联系
          │                        └ R.Render
          └ R.raw 已非空 → 返回
```

G 的增删对 R 而言就是「子资源 G 换成新版本」：R 的成员没变，联系照样重建，因为联系指向 G 的 raw。顺序是：R 结束、G 结束旧的、G 开始新的、R 开始，符合 1.4 节的替换顺序。s 在 `Free` 里排在 G 之前还是之后都一样，它只被放开一次，不再 `Render`。

更深的链 R{G1{G2{x}}} 里 G2 增删并提交后，同理逐级向上转告：G2 被 G1 联系，转告 G1；G1 陈旧，生成重建的一批，已齐，又被 R 联系，转告 R；R 陈旧，生成重建的一批，是根，替换。R 放开在用的一批时让 G1 检查，G1 就位；G1 放开在用的一批时让 G2 检查，G2 就位。G2 就位后通知 G1，G1 开始，再通知 R，R 开始。

### 7.5 两级同时增删

角色 P{W, body}：翅膀 W 自己是成组资源 W{l, r}，body 是身体。全部已加载。

```text
上层代码给角色换身体：P.RemoveChild(body); P.AddChild(body2); P.SetActive(true)
└ 提交时激活 body2，body2 开始加载；P 照常使用 {W, body}

body2 到达之前，上层代码给翅膀换右翼：W.RemoveChild(r); W.AddChild(r2); W.SetActive(true)
└ 提交时 W 激活 r2，r2 当场交付 → W 待交付、已齐，但被 P 联系 → 转告 P
     └ P.OnDependencyLoaded() → P 待交付；body2 未加载 → 未齐 → 返回

# P 仍是 {W, body}，W 仍是 {l, r}：角色照常显示旧身体、旧右翼

body2 到达 → P.OnDependencyLoaded() → 待交付，已齐（W 已齐，P 联系着它），没有被联系
└ P.OnLoadDone({W, body2})                     # P 替换
     ├ P.OnActive({W, body}, false); P.raw = null
     ├ P.Free({W, body})
     │    ├ W 仍有计数 → P 让 W 检查 → W 已不受 P 联系 → W 就地替换：拆 {l, r}，停用 r，建 {l, r2}
     │    │    └ 通知 P → 已齐，W 不待交付 → P.OnActive({W, body2}, true); P.Render   # 新身体、新右翼一起建立联系
     │    └ body 计数归零 → P 停用 body → 旧身体结束
     └ P.raw 已非空 → 返回
```

W 的新状态齐了，但整个角色 P 的新状态还没齐（body2 未到），P 不能重建；P 不放开联系着 W 的那一批，W 也就不能替换。两处改动在 body2 到达时一起生效，中间没有空窗。

### 7.6 外层移除一个待交付的子资源

P{G} 已加载；G 加了 c 并已提交，c 还在加载；此时 P 移除 G：

```text
上层代码 P.RemoveChild(G)                      # P 的新一批 {}，只记账
上层代码 P.SetActive(true)                     # 提交
├ P.Render({G})
└ P.OnDependencyLoaded() → 待交付、已齐（空集）、没有被联系 → P.OnLoadDone({})
     ├ P.OnActive({G}, false); P.raw = null
     ├ P.Free({G}) → G.RemoveDependent(P) → 计数归零 → P 停用 G：G.SetActive(false)
     │    ├ G.BreakLoad() → 放开没在用的 {a, b, c}：a、b 仍有计数；c 计数归零 → c.SetActive(false) → c 停止加载
     │    └ G.OnActive({a, b}, false); G.raw = null; G.Free({a, b}) → a、b 停用并结束
     ├ P.raw 仍为空 → 继续
     ├ P.OnActive({}, true)
     └ P.Render({})
```

G 的新一批随 G 的停用一起放弃，每一批恰好放开一次。

### 7.7 停用

```text
已加载：上层代码 R.SetActive(false)             # 先上层后下层
├ R.BreakLoad() → children 就是 raw → 什么都不做
└ R.OnActive({G, s}, false); R.raw = null; R.Free({G, s})
     ├ s.RemoveDependent(R) → 计数归零 → s.SetActive(false) → s 结束生命期并 Free
     └ G.RemoveDependent(R) → 计数归零 → G.SetActive(false)
          ├ G.BreakLoad() → 什么都不做
          └ G.OnActive({a, b}, false); G.raw = null; G.Free({a, b}) → a、b 停用并结束

部分加载（G 已装配，s 还在加载）：上层代码 R.SetActive(false)
├ R.BreakLoad() → R 还没有 raw → 放开最新的一批 {G, s}
│    ├ s.RemoveDependent(R) → 计数归零 → s.SetActive(false) → s.BreakLoad() 停止加载
│    └ G.RemoveDependent(R) → 计数归零 → G.SetActive(false) → 走 G 的「已加载」停用
└ R.raw 为空 → 结束

G 有已提交、待交付的新一批时停用 R：G 随 R.Free 停用，G.BreakLoad 放开它的新一批，同 7.6
```

### 7.8 推敲要点

- 抽象成立：R 只问 G 两件事：G 已齐没有（`IsLoaded`）、G 待交付没有（G 的 `children` 是不是 G 的 raw）。G 内部怎么换，R 不知道；R 把「联系着的 G 待交付」当作自己陈旧、要重建，把「G 已齐」当作自己的一项齐备条件。
- 替换只由「待交付、已齐、没有被联系」的最上一级发起。从它到变动点的路径上，每一级依次重建；路径外的兄弟子树只是被放开一次，自身不重建，也不再 `Render`。
- 内层一齐就向上转告，外层未齐就等，内层不动（7.5）。改动总在整棵子树的新状态都齐了之后一起生效，没有空窗。
- 下探靠替换的顺序：R 的 raw 先置空，再放开在用的一批，并让仍有计数的 G 检查一次；这时 R 已不联系 G。
- 上探靠嵌套的交付：G 就位后通知 R，R 的新一批若已齐，就在那次通知里开始；R 放开在用的一批之后看到 raw 已非空，不再重复开始。几个子成组资源都要就位时，R 等最后一个就位才开始，只重建一次。
- 首次装配不经过「联系」：R 还没有 raw 时 G 没有被联系，G 齐了就自己装配（7.2）。
- 代价：任何一处增删，都让从根到变动点的每一级重建联系；`IsLoaded` 逐级递归。先不考虑效率。

## 8. 拷贝与引用

拷贝是按模板复制出来的资源。拷贝方式随资源而不同：

| 拷贝方式 | 例子 | 拷贝出的 raw |
| --- | --- | --- |
| 完整拷贝 | prefab asset 实例化成 GameObject | 新对象，每份拷贝各自一个 |
| 部分拷贝 | 从 bundle 中取一个 asset | 模板的一部分 |
| 地址拷贝 | texture、bundle 之间的依赖 | 模板的 raw 本身 |

`Clone` 只决定「何时拷贝、何时销毁拷贝」，「怎样拷贝」留给派生类的 `CreateClone` / `DestroyClone`。`Reference` 是地址拷贝。模板只能是单个资源；成组资源的地址拷贝，就是把它作为子资源加入别的成组资源。

`Reference` 的 raw 就是模板的 raw，多份引用拿到的是同一个对象，所以引用自己的 `OnActive`、`Render` 不修改它。

拷贝自己也是 `Resource`，也可以再作为模板：从 prefab 实例化出的 Item，还可以再拷贝多份。按约束 1，这样的 Item 只经由它的拷贝被使用。

两份拷贝 C1、C2 共享模板 T：

```text
上层代码 C1.SetActive(true) → C1.Load()
├ T.AddDependent(C1)                            # 只记账
└ C1.OnDependencyLoaded() → T 没在使用 → T.SetActive(true) → T.Load → 返回

上层代码 C2.SetActive(true) → C2.Load()
├ T.AddDependent(C2)
└ C2.OnDependencyLoaded() → T 在使用、尚未加载 → 返回

T 到达：T.OnLoadDone(rt)
├ T.OnActive(rt, true); T.raw = rt; T.Render(rt)
└ 对 {C1, C2} 各调 OnDependencyLoaded
     ├ C1：在使用、没有 raw、T 已加载 → C1.OnLoadDone(C1.CreateClone(rt) = r1)
     │     ├ C1.OnActive(r1, true); C1.raw = r1; C1.Render(r1)
     │     └ 通知 C1 的上层（若有）
     └ C2：同上，得到 r2

T 已加载后，上层代码 C3.SetActive(true)         # 同步完成
└ C3.Load() → T.AddDependent(C3) → C3.OnDependencyLoaded() → T 已加载 → C3.OnLoadDone(C3.CreateClone(rt))

上层代码 C1.SetActive(false)，C1 已加载          # 先上层后下层；下层继续存活
├ C1.BreakLoad() → 已有 raw → 什么都不做
└ C1.OnActive(r1, false); C1.raw = null; C1.Free(r1)
     ├ C1.DestroyClone(r1)
     └ T.RemoveDependent(C1) → 仍有 C2、C3 → T 继续存活

最后一份拷贝停用
└ …… T.RemoveDependent(…) → 计数归零 → T.SetActive(false) → T.OnActive(rt, false); T.raw = null; T.Free(rt)

T 到达前，上层代码 C1.SetActive(false)，且 C1 是唯一的拷贝
├ C1.BreakLoad() → 还没有 raw → T.RemoveDependent(C1) → 计数归零 → T.SetActive(false) → T.BreakLoad() 停止加载
└ C1.raw 为空 → 结束
```

引用 R1、R2 共享 texture 模板 T 时流程相同，只是 `CreateClone` 返回 `rt` 本身，`DestroyClone` 什么都不做：R1、R2 与 T 的 raw 是同一个对象，T 在最后一份引用 `Free` 之后才 `Free(rt)`，所以引用持有的 raw 不会先于引用被销毁。

成组资源包含拷贝 G{C}，C 的模板是 T：

```text
G.Load() → C.AddDependent(G) → G 检查 → 激活 C → C.Load() → T.AddDependent(C) → C 检查 → 激活 T → T.Load

T 到达 → T.OnActive(true); T.Render → C.OnDependencyLoaded()
└ C.OnLoadDone(CreateClone(rt)) → C.OnActive(true); C.Render → G.OnDependencyLoaded()
     └ G.OnLoadDone({C}) → G.OnActive(true); G.Render
```

开始的顺序是 T、C、G，拆除的顺序是 G、C、T，每一层都是同一组步骤。在资源树里，拷贝是叶子：它只有一个 raw，不会被替换。

## 9. 共享

两个成组资源 G1{s}、G2{s} 共享单个资源 s：

```text
G1.Load() → s.AddDependent(G1) → G1 检查 → 激活 s → s.Load
G2.Load() → s.AddDependent(G2) → G2 检查 → s 已在使用、尚未加载 → 返回

s 到达 → s.OnActive(true); s.Render
└ 对 {G1, G2} 各调 OnDependencyLoaded
     # G1、G2 各自按自己的其他子资源是否齐了，决定是否交付

G1 停用 → G1.OnActive(false) → G1.Free → s.RemoveDependent(G1) → 仍有 G2 → s 继续存活
G2 停用 → …… → s.RemoveDependent(G2) → 计数归零 → G2 停用 s → s 结束生命期并 Free
```

谁先停用、谁后停用都一样：s 的生命期覆盖 G1、G2 两者的生命期，这就是不变式 6。G2 把 s 移出自己的集合时，s 在 G2 替换时被放开，G1 仍在使用它。

共享的资源由使用者保证不可变（约束 2）。`SetData`、`AddChild`、`RemoveChild` 发现本资源有多个上层时报警告，框架不做别的处理。共享的成组资源 X 若仍被增删：

- X 的新一批齐了，被联系，转告每个上层。每个联系它的上层都放开了联系着它的那一批，它才能就位。
- 联系它的上层都已齐、能接连重建时，X 在最后一个上层放开它时就位，各上层随后在通知里开始新的一批，结果正确。
- 否则先重建的上层联系回 X 的旧版本；X 在另一个上层重建时就位，换了 raw，而先重建的那个上层还联系着它，违反不变式 6。结果不保证。

## 10. 设计记录

### 10.1 「使用期间不能增删子资源」从何而来

上一版实现里有这条断言。它不是设计规则，是那一版的范围限制：伪代码当时声明「不考虑成组资源增删子资源」，断言只是守住这个前提。

那一版的 `children` 身兼两职，既是镜像，又是本组登记过的子资源集合：

- `Load` 对 `children` 登记，`BreakLoad` 对 `children` 离开；
- 「齐了」查 `children`，交付的也是 `children`。

加载途中改了 `children`，`BreakLoad` 就会离开从未登记过的子资源（断言失败），又漏掉登记过、却已被移除的子资源（计数泄漏）；交付出去的集合里，可能有没计上本组的子资源，别的上层一离开它就被停掉。已加载之后改 `children`，`SetActive(true)` 只会 `Render`，改动永远不生效。

现在每一批是一个不再修改的集合对象，计数跟着批走：在使用时每一批对自己的成员各计一次，被取代或被替换时放开。增删换上新的一批，旧的一批原样留着，它登记过哪些子资源由它自己记着。计数只记账，激活等检查点，所以增删不触发加载；到检查点，最新的一批就能交付。

### 10.2 被联系的成组资源不就地替换：就绪向上，重建向下

曾经的写法是：内层一齐就当场替换，替换之前用一条「将要替换」的通知，强迫上层先结束生命期、替换之后再重建。它有两个问题：

- 违反前提：上层被迫拆联系的时机由下层决定。上层自己若也在等新状态（7.5 里 P 在等 body2），被迫结束之后只能等自己的新状态齐了才重建，中间整个角色没有生命期。
- 违反抽象：上层的状态轮转被下层的内部轮转打断，上层必须知道下层「将要替换」。

现在的写法：

- 被联系的成组资源，新的一批齐了只向上转告「就绪」，自己不动。
- 上层把「联系着的子成组资源待交付」当作自己陈旧，按原成员生成重建的一批；把「子资源已齐」当作自己的一项齐备条件。
- 一路向上，直到「待交付且已齐、又没有被联系」的那一级，由它发起替换。它放开在用的一批时，让仍有计数的子成组资源各检查一次，它们已不受它联系，自上而下依次就位；子资源就位后通知它，它在通知里开始新的一批。

向上的通知只有「交付或就绪」一种；向下只有计数、放开与激活、停用。

### 10.3 不回溯父级

早先的单参数 `SetActive` 要回溯到根，只为算出 `isHierarchyLoaded`，用来在「整树加载完毕之前不 Render」。现在不需要了：

- 1.4 节的开始顺序让每个节点到达即 `Render`，不再等整树加载完毕，`isHierarchyLoaded` 原本的用途已经不存在。
- 共享子资源之后，向上的路径本来也不唯一：一个资源可以有多个上层，资源树是有向无环图，没有唯一的根。

所以 `parent`、`GetHierarchyRoot()`、`isHierarchyLoaded` 与两参数 `SetActive` 都已去掉。需要知道上层的地方，只问直接上层：成组资源看每个上层的 raw 里有没有自己；「就绪」由每一级自己转给它的上层。

### 10.4 成组资源内部不持有引用

曾经的写法是：成组资源为每个子资源在内部创建一份 `Reference`，由引用登记在子资源上。它带来的额外复杂度：

- `parent` 只有内部引用会用到，原本的资源与成组资源的 `parent` 永远为空。
- 向上通知有两种通道（`clones` 与 `parent`），每升一级要走两跳。
- `children` 变成「子资源 → 引用」的映射，`Free(set)` 还要反查引用。
- 判断齐了必须查引用而不是子资源：共享时，子资源可能已经加载，而本组的引用还没收到通知。
- 内部引用的 `active`、`raw`、`loading` 都只是子资源状态的复本；它的 `OnActive`、`Render` 是空的，构建与拆除时多出一组空步骤。
- `Reference` 同时承担上层持有的地址拷贝、成组资源内部的计数器两种角色。

现在的写法让成组资源自己登记在子资源上，`Reference` 类只用于上层代码自己持有的、单个资源的地址拷贝。成组资源的每一批仍可以看作一组引用，增删就是换一组引用；这只是看法，不落成对象。

### 10.5 去掉 `OnUnlinked`：放开在用的一批即检查

曾经的写法：上层重建时，对仍需要的子资源发一条「已拆联系」的通知 `OnUnlinked`，子资源据此检查能否就位。它不对称：向下多了一种只为这一刻服务的消息，还要靠 `committed` 区分「仍需要」与「不再需要」。

现在按批计数，上层替换时放开在用的一批：

- 计数归零的子资源，由上层停用；
- 仍有计数的子成组资源，由上层让它检查一次。

「已拆联系」就是「联系着本资源的那一批放开了」，不需要另外的方法。只有放开在用的一批才需要检查：别的批没有联系任何子资源。时机也恰好：raw 先置空、再 `Free`，子资源检查时看到上层已不联系它；上层的新联系在子资源就位的通知里或者 `Free` 之后才建立。

### 10.6 去掉的成员与方法

| 去掉的 | 曾经表示 | 现在从哪里推出 |
| --- | --- | --- |
| `committed`，以及推敲中的 `next` | 最近一次提交的快照、下一批 | `children` 就是最新的一批；待交付即 `children` 不是 raw |
| `loading` | 交付回调；交付途中置空以防重入 | 交付由检查点驱动，检查先看 `active`；嵌套交付由「`Free` 之后 raw 已非空就返回」处理 |
| `IsPending`、`NeedsLoad`、`Links`、`IsLinked` | 待交付、要不要加载、是否联系 | `children` 与 raw 是否同一个对象；`Load` 每个使用周期只调一次；上层的 raw 里有没有本组 |
| `TryDeliver`、`Release`、`EndLifetime`、`OnUnlinked` | 交付检查、放开、结束生命期、已拆联系 | 合进 `OnDependencyLoaded`、`Free`、`BreakLoad`、`SetActive`、`OnLoadDone` |
| `AddDependent`、`RemoveDependent` 里的激活、停用与检查 | 第一次计数时开始使用，全部放开时不再使用，放开而仍有计数时检查 | 由计数的一方负责：检查时激活，放开后归零就停用；放开在用的一批时，`Free` 让仍有计数的子成组资源检查 |

### 10.7 增删只记账：不激活、不交付

曾经的写法：增删立刻对新的一批计数，而计数会激活新子资源，新子资源当场开始加载。同步交付的子资源在增删途中交付，这次交付是检查点，本组就交付了还没增删完的上一批：多一次生命期，中间有空窗。

两种直接的修法都要增加实体：

- 挡住增删途中的检查，要一个标志（`counting`）。
- 完全按「增删只改镜像、提交才生效」，要记住已提交的一批（`committed`）：提交之后、交付之前又有增删时，下一次提交要放开上次提交计过数的成员，它们可能已既不在镜像里、也不在 raw 里，组这边找不到。还要一个只在提交时调用的方法，把提交与其他检查点区分开。

现在把计数与激活分开：`AddDependent`、`RemoveDependent` 只记账；激活由上层在检查点做，停用由放开计数后归零的一方做。增删照样换批、计数，却不激活、不检查，增删途中没有检查点；提交是检查点，新子资源在那时激活。不增加成员，也不增加方法，代价是两处放宽：

- 被放弃的子资源，在删掉它的那次增删里停用。它是之前的检查激活过、现在不再需要的子资源，没有被本组联系，停用它不影响本组的生命期。
- 增删在本组的下一个检查点生效。「增删……增删、提交」写在一起时就是提交；隔帧才提交时，期间的检查点会让增删提前生效（约束 1）。

## 11. 待确认

1. **`IsLoaded` 的递归与检查的代价。** `IsLoaded` 逐级看子资源；陈旧检查看每个联系着的子资源；就绪逐级转告时，每一级都要再算一遍。先不考虑效率。
2. **有上层的资源，`active` 与 `dependents` 重复。** 一个资源只要有上层、且已到过检查点，它的 `active` 就等于「`dependents` 非空」。目前不改，记下备查。
3. **`Engine` 层的成组资源如何读取子资源的 raw。** 具体的成组资源在 `OnActive` 里建立子资源之间的联系，需要读每个子资源的 raw。`raw` 是 `protected internal`：`Engine` 程序集里的派生类只能经由自己类型的引用读它，读不到 `Resource` 类型的子资源的 raw。要不要给成组资源的派生类一个读取子资源 raw 的途径，等写第一个 `Engine` 层成组资源时再定。影响 `Resource`、`ResourceGroup`。
4. **经由下层的环。** 一个资源若（经由子资源或模板）成了自己的下层，它等下层、下层又等它，永远加载不完。使用期间也能 `AddChild`，环可能在使用中引入。检查要沿 `children` 与 `template` 两条依赖边求依赖闭包（`Resource.md` 15.8 节），放在 `AddChild` 里做还是检查点上做，待定。影响 `ResourceGroup.AddChild` 或 `OnDependencyLoaded`。
