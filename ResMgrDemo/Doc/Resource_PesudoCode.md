# 有组合性的异步资源框架：设计与实现

本文分两部分。第一部分「设计」分析问题域：概念、前提、正确性要求，以及由它们推出的结论；涉及多种做法时，只列各自的条件与后果，不做取舍。第二部分「实现」说明本框架的取舍、采用的不变式、协议与伪代码，代码以第二部分为准。流程调整时，先改本文，再改代码。

范围：不考虑加载失败；只考虑同步完成的拷贝；不考虑在已装配的树里单独停用内部节点。

# 第一部分 设计

## 1. 问题

上层代码要以同一种方式使用三类资源：

- **单个资源**：一次异步加载得到一个原始对象，例如从 bundle 实例化出的 GameObject、一张贴图。
- **成组资源**：由若干子资源组成，把子资源的原始对象联系成一个整体，例如角色 P = {翅膀 W, 身体 body}，翅膀 W = {左翼 l, 右翼 r}。成组资源可以嵌套成树。
- **拷贝**：按模板的原始对象同步得到，例如实例化 prefab、从 bundle 取 asset、引用同一张贴图。

资源可以被多个使用者共享；加载可能被打断，结果可能在不再需要之后才到达；成组资源在使用中可能改变组成，例如换装，换装期间不能出现空窗。框架要在这些条件下给出确定、成对的生命期。

## 2. 概念

**raw 与生命期。** raw 是资源持有的原始对象；成组资源的 raw 是它的子资源集合。生命期属于 raw，不属于资源对象：

开始 `OnActive(raw, true)` → 使用 `Render(raw)`，一次或多次 → 结束 `OnActive(raw, false)` → 释放 `Free(raw)`

一个资源对象可以先后经历多份 raw：每次使用一份；成组资源在一次使用中还可以替换。raw 可用称为**交付**；资源已不再使用之后才到达的 raw 称为**迟到**。

**镜像。** 上层代码写入的期望状态，包括资源自身的数据和成组资源的组成。写镜像不触及 raw。数据部分由 `Render` 应用，raw 存在时可以立即应用；组成部分要加载新成员、替换 raw，只能在新组成齐备时生效。**提交**是上层代码要求资源按镜像更新 raw。

**上层与下层。** x 的上层是需要 x 的 raw 的一方：上层代码、包含 x 的成组资源、以 x 为模板的拷贝。反过来，子资源、模板是下层。一个资源可以有多个上层，依赖关系是有向无环图，没有唯一的父级或根。

**联系。** 成组资源的生命期要使用子资源的 raw，例如挂接变换、绑定骨骼。成组资源 u 当前的 raw 含有 x 时，称 u **联系**着 x；有上层联系着 x 时，称 x **被联系**。

**状态谓词。** 资源的**目标**是它应当到达的状态；成组资源的目标组成由镜像与提交决定（第 6 节）。

| 谓词 | 含义 |
| --- | --- |
| 待交付 | 目标与在用的 raw 不同；只对成组资源有意义 |
| 最新 | 有 raw，不待交付，联系着的子资源都最新 |
| 已齐 | 目标现在就能就位：单个资源与拷贝已交付；成组资源目标中的每个成员都已齐 |

单个资源只有三种状态：不用、在等、在用，三个谓词是同一件事。成组资源上它们可以分开：一边用旧组成、一边等新组成；一次使用中先后有多份 raw；被联系时可以已齐而不是最新（5.2）。

## 3. 前提

1. 叶子都是单个资源，一次使用只有一份 raw，不替换。
2. 非叶节点都是成组资源，raw 是子资源集合，可以替换。
3. 被联系的 raw 不能替换：替换一个资源的 raw，前提是没有上层联系着它。
4. 拷贝同步完成；模板只能是单个资源。成组资源的地址拷贝，就是被别的成组资源包含。
5. 共享的资源由使用者保证不可变。
6. 成组资源的 `Render` 不级联：要改子资源，在自己的 `Render` 里显式提交子资源的数据。
7. 每个资源的 `OnActive(false)` 撤销它自己在 `OnActive(true)` 与 `Render` 里的全部修改；只做一次的初始化放在 `OnActive(true)`，每次按镜像重做的放在 `Render`。

## 4. 正确性要求

- **R1 生命期完整。** 每份交付的 raw 恰好经历一次开始、至少一次使用、一次结束、一次释放，依此顺序；迟到的 raw 只释放。同一资源同一时刻至多一份 raw 在生命期内。
- **R2 下层包住上层。** 上层一次生命期里联系着的每个下层，在这整段时间里是同一份 raw 的生命期：先于上层开始并 `Render`，晚于上层释放才结束，中间不替换。
- **R3 不用就不占。** 没有上层需要的资源，不持有 raw，不加载，也不占用它的下层。
- **R4 进展。** 提交之后，只要加载都会完成，在用的资源最终是最新的。
- **R5 不断档。** 成组资源换成新组成时，旧组成照常使用，直到新组成就位（`Resource.md` 11.1 节）。
- **R6 局部。** 一处变动只让必须重建的资源重新开始生命期；其余资源既不重新开始，也不重复 `Render`。

## 5. 推论

### 5.1 生命期顺序

由 R2：

- **开始自下而上**：`child.OnActive(true)`、`child.Render`，然后 `parent.OnActive(true)`、`parent.Render`。
- **结束自上而下**：`parent.OnActive(false)`、`parent.Free`，然后下层才可能 `OnActive(false)`。
- 两者不必同时结束：下层还有别的上层时继续存活。

### 5.2 替换：就绪向上，重建向下

由前提 3 与 R2，被联系的成组资源即使新组成已齐，也不能就地替换。联系由上层当前的 raw 决定，上层不再联系它的唯一途径，是结束自己这份 raw 的生命期。所以：

- 新组成已齐的内层，只能向联系它的上层报告「就绪」。上层把它看作「这个子资源要换成新版本」，自己也就要重建，即使上层自己的组成没变。
- 报告沿联系向上传，直到没有被联系的祖先。这个祖先结束生命期、拆掉旧联系；内层这时已不被联系，可以就位；内层就位之后，祖先按子资源的新版本重新开始。

```text
P.OnActive(oldP, false)      # P 拆掉旧联系
P.Free(oldP)                 # 不再需要的子资源结束；仍需要的子资源已不被 P 联系：
    W.OnActive(oldW, false)
    W.Free(oldW)             # 同一规则，逐级向下
    W.OnActive(newW, true)
    W.Render(newW)
P.OnActive(newP, true)       # 按子资源的新版本重新建立联系
P.Render(newP)
```

- 重建的只有从变动点到这个祖先的一条链。链外的兄弟子树 raw 不变，只被重新联系；由前提 6、7，它们既不重新开始，也不必重复 `Render`，满足 R6。
- 新加入的子资源在祖先重新开始之前已经开始生命期；新旧组成都有的子资源在整个替换过程中一直存活；被移除的子资源在祖先拆掉旧联系之后才结束。

### 5.3 多层改动一起生效

祖先自己也在等新组成时（P 在等新身体 body2），内层 W 的新组成即使先齐，也因仍被 P 联系而不能就位；P 的新组成没齐，P 也不能重建。两处改动只能在 P 齐备时一起生效，期间旧身体、旧翅膀照常使用，满足 R5。

### 5.4 评估时机

成组资源能否交付，取决于四个条件：它在使用、待交付、目标中每个成员已齐、没有被联系。这些条件只会在下面的事件之后改变，所以必须在这些时刻重新评估，其余时刻不必：

1. 某个下层交付了，或某个成组的下层报告就绪；
2. 某个上层不再联系它，即上层结束了联系着它的那份 raw；
3. 它的目标变了：开始使用、提交，或者组成的变化在目标上生效。

事件可以同步发生：命中缓存的加载在发起它的调用里就交付，交付又通知上层。所以评估可能嵌套在别的操作中途发生，各个操作都要能重入。

### 5.5 共享

- 下层要存活到最后一个需要它的上层离开，所以「需要」要按上层记录。
- 替换期间，成组资源同时需要旧组成（还在用）和新组成（在等），同一个子资源可能两者都需要（R5）。所以「需要」还要能按组成区分，而不只是按上层。
- 共享的成组资源被多个上层联系时，只有这些上层在同一时段都拆掉联系，它才能就位；否则要么一直不能就位，要么在某个上层的生命期里换了 raw，违反 R2。前提 5 的来由在此。
- 向上的路径不唯一：任何向上的通知都要发给所有直接上层；不存在可以回溯到的唯一的根。

### 5.6 中断与放弃

- 停止使用时，进行中的加载要打断；打断不了的，结果迟到，只释放（R1）。
- 一个子资源可能只被成组资源待交付的新组成需要：它在加载，或已开始生命期但还没被联系。新组成被取代、或成组资源停止使用时，它不再被需要，按 R3 要停用。

### 5.7 拷贝

| 拷贝方式 | 例子 | 拷贝出的 raw |
| --- | --- | --- |
| 完整拷贝 | prefab 实例化成 GameObject | 新对象，每份拷贝各一个 |
| 部分拷贝 | 从 bundle 取一个 asset | 模板的一部分 |
| 地址拷贝（引用） | 贴图、bundle 之间的依赖 | 模板的 raw 本身 |

- 拷贝的 raw 可能引用模板的内容，所以模板是拷贝的下层，模板的生命期要包住拷贝的：拷贝先释放，模板才能结束。
- 地址拷贝之间共享同一个对象，它们既不能修改它，也不能释放它；它由模板释放。
- 模板若是成组资源，它的组成一变，所有拷贝都要重建。前提 4 排除了这种情况；成组资源的地址拷贝，就是被包含。

## 6. 使用中改变组成

### 6.1 三份集合与四种状态

成组资源在使用中改变组成时，可能同时存在三份子资源集合：

- 镜像 M：增删的最新结果；
- 目标 T：要就位的组成，其中的新成员在加载；
- 在用 R：raw，被本组联系着。

| 状态 | 关系 | 如何到达 |
| --- | --- | --- |
| 稳态 | M = T = R | 交付之后没有再增删 |
| 增删未生效 | M ≠ T = R | 只改了镜像 |
| 待交付 | M = T ≠ R | 增删已生效，新成员还没齐 |
| 待交付时又增删 | M、T、R 两两不同 | 生效之后、交付之前继续增删 |

### 6.2 各流程需要的信息

| 流程 | 需要 |
| --- | --- |
| 增删 | M |
| 增删生效 | 以 M 取代 T：M 与 T 的全部成员，以便放开只在 T 中的成员 |
| 评估与交付 | T：齐了交付 T，而不是 M |
| 停止使用 | T 与 R：两者都要放开 |
| 上层评估本组 | 本组是否待交付、T 是否已齐 |

### 6.3 T 能否推出

T 若既不同于 M、也不同于 R，就推不出来：T 中的成员可能已被后来的增删删掉，又不在 R 里。对下层的需要记在下层那里，成组资源能列举的只有 M 与 R 的成员，找不到这样的成员。

例：R = {a, b}；加入 c 并生效，T = {a, b, c}，c 在加载；c 到达之前删掉 c、加入 d，M = {a, b, d}。此后无论放开 c，还是 c 先到时交付含 c 的 T，都要能找到 c，而 c 既不在 M 也不在 R 里。

所以第四种状态要么另外记住 T，要么不让它出现。

### 6.4 增删何时生效：三种做法的后果

- **甲：增删立即生效，并立即开始加载新成员。** T 就是 M，不必另记。增删会开始、停止加载；命中缓存的新成员在增删途中就交付，这是一次评估时机，可能交付增删到一半的组成。
- **乙：增删只改镜像，提交时生效。** 增删不引起任何加载与生命期事件。第四种状态里 M、T、R 互不相同，T 要另记；还要能把提交与其他评估时机区分开，否则别的评估时机会让还没提交的增删生效。
- **丙：增删立即记下需要，但不开始加载，到本组下一次评估时才开始加载。** 需要的记录就是 M，T 不必另记。增删不开始加载。已开始加载又被放弃的成员，要么在增删时停用，要么另记。增删在下一次评估时生效；评估若来自提交以外的事件，增删就提前生效。

# 第二部分 实现

## 7. 取舍

1. **最少的状态。** `Resource` 只有 `data`、`raw`、`active`、`dependents` 四个字段，`ResourceGroup` 只多一个 `children`，`Clone` 只多一个 `template`。待交付、被联系、已齐、陈旧都由它们推出（8.2）。
2. **批。** 成组资源的组成按批更替：每次增删生成一个新的集合对象，生成后不再修改。`children` 是最新的一批；raw 是某次交付时的 `children` 对象本身。待交付即 `children` 与 raw 不是同一个对象。
3. **按批记账。** 在使用时，每一批对自己的每个成员各记一次需要，`dependents` 是多重集合。替换期间新旧两批各自记账（5.5）；放开一批，就是放开它自己记下的那些，不必另记「已登记」的集合。
4. **记账与激活分开（6.4 的做法丙）。** `AddDependent`、`RemoveDependent` 只记账。上层在检查点激活它需要、却还没在使用的下层；谁放开之后计数归零，谁就停用那个下层。增删只改记录，不开始加载，也不交付，所以既不必另记 T，也不必区分提交与其他检查点。代价是两处放宽：
    - 已激活又被放弃的子资源，在删掉它的那次增删里就停用（5.6）；
    - 增删在本组的下一个检查点生效，通常就是紧接着的提交；隔帧才提交时，期间的其他检查点会让增删提前生效。
5. **检查点。** 交付只发生在 5.4 列出的评估时机，称为检查点，即调用 `OnDependencyLoaded` 的时刻。增删不是检查点。
6. **替换协议。** 被联系的成组资源已齐时只转告上层（5.2）。上层发现联系着的子成组资源待交付（陈旧），就按原成员生成一个重建批。放开在用的一批时，让仍有计数的子成组资源检查一次，它们就此就位。子资源就位后通知上层，上层可能就在这次通知里开始新的一批，所以上层的替换在 `Free` 之后要看 raw 是否已经设好。
7. **拷贝与成组资源同构。** 拷贝对模板记账，在检查点激活模板，模板已齐就交付；放开之后计数归零就停用模板。成组资源直接对子资源记账，不在内部为每个子资源建 `Reference`。
8. **共享的可变资源只报警告。** 修改有多个上层的资源时，用 `System.Diagnostics.Trace.TraceWarning` 报警告，不做别的处理（前提 5、5.5）。

## 8. 结构

### 8.1 字段

| 字段 | 含义 |
| --- | --- |
| `data` | 镜像中的数据部分，只由 `SetData` 修改 |
| `raw` | 当前的 raw；非空当且仅当生命期正在进行 |
| `active` | 是否正被使用，唯一的状态标志 |
| `dependents` | 多重集合：上层的每一批需要本资源时记一次 |
| `children`（成组资源） | 最新的一批 |
| `template`（拷贝） | 模板，构造后不变 |

`active` 不能由 `dependents` 推出：根由上层代码使用，没有记账；增删之后、检查点之前，新成员已被记账，却还没在使用。

### 8.2 派生量

| 量 | 推导 |
| --- | --- |
| 待交付（成组资源 g） | `g.children` 与 `g.raw` 不是同一个对象 |
| 被联系（x） | 某个上层的 raw 含有 x |
| 已齐 `IsLoaded()` | 单个资源与拷贝：`raw != null`；成组资源：`raw != null`，且 `children` 的每个成员都已齐 |
| 陈旧（成组资源 g） | 不待交付，但联系着的某个子成组资源待交付 |
| 最新 | 有 raw，不待交付，联系着的子资源都最新 |

成组资源的「已齐」要求已有 raw：首次装配时，最后一个成员到达的那次检查就会交付，上层据此看到的总是已交付过的子成组资源。

### 8.3 方法

| 方法 | 所在 | 职责 |
| --- | --- | --- |
| `SetActive(on)` | 基类 | 不在使用时开始使用：`Load`；已在使用时提交：`Render`，再检查；停止使用：`BreakLoad`，再结束生命期 |
| `SetData(data)` | 基类 | 只改镜像；有多个上层时报警告 |
| `AddDependent` / `RemoveDependent` | 基类，`internal` | 只记账 |
| `OnLoadDone(newRaw)` | 基类，`protected` | 唯一的交付点：迟到的直接释放；替换时先结束旧 raw；开始新 raw，`Render`，通知上层 |
| `IsLoaded()` | 虚方法 | 已齐 |
| `OnDependencyLoaded()` | 虚方法 | 检查点上的检查；基类什么都不做 |
| `Load` / `BreakLoad` / `Free` | 抽象 | 单个资源由具体资源实现；`ResourceGroup`、`Clone` 各自实现 |
| `OnActive` / `Render` | 抽象 | 由具体资源实现 |
| `AddChild` / `RemoveChild` | 成组资源 | 换批、改记账 |
| `CreateClone` / `DestroyClone` | 拷贝，抽象 | 拷贝方式，二者成对 |

只有基类修改 `raw` 与 `active`。派生类改的是自己的批和对下层的记账；激活、停用下层，也只经由下层的 `SetActive`。

## 9. 不变式

以下四条用 8.2 的派生量表述。「始终」指方法执行中途之外的任何时刻；「检查点之后」指相关资源的检查结束时。

### 9.1 记账精确（始终）

对任意上层 u 与下层 x，u 在 `x.dependents` 中出现的次数，等于 u 对 x 的需要份数：

- u 是正在使用的成组资源：x 在 `u.raw` 里计 1；x 在待交付的 `u.children` 里再计 1。
- u 是拷贝，x 是它的模板：从 `Load` 起，到交付前的 `BreakLoad` 或交付后的 `Free` 为止，计 1。
- 其余情况为 0。

批生成后不再修改，`u.raw` 总是某次交付时的 `u.children` 对象。

### 9.2 在用即需要

- **不用就不占（始终）**：`active` 为假时，没有 raw，加载已打断，对下层没有记账。
- **不需要就不用（始终）**：不被任何上层记账、也不是上层代码在用的根，`active` 就为假。
- **需要就在用（记账一方的检查点之后）**：u 的检查结束时，u 记账的每个下层都在使用。

### 9.3 能就位即就位（检查点之后）

已齐而没有被联系的资源，都是最新的。等价地：已齐而不是最新的，只能是被联系的成组资源；它已把就绪转告上层，在等上层重建。

反方向的「最新必已齐」由定义直接成立，不必维护。

### 9.4 生命期成对且嵌套（始终）

- **一份 raw，一次生命期**：每份交付的 raw 恰好一次 `OnActive(true)`、至少一次 `Render`、一次 `OnActive(false)`、一次 `Free`，依此顺序；`raw` 字段只在 `OnActive(true)` 之后、`OnActive(false)` 之前非空；迟到的 raw 只 `Free`。
- **下层包住上层**：上层一次生命期里联系着的每个下层，整段时间是同一份 raw 的生命期，先于上层开始并 `Render`，晚于上层 `Free` 才结束。

### 9.5 放宽与例外

- 增删之后、本组的下一个检查点之前：9.2 的「需要就在用」对新加入的成员不成立；9.3 对本组不成立。
- 共享的成组资源被增删时（违反前提 5），9.3 与「下层包住上层」都不保证。

### 9.6 如何维持

| 不变式 | 维持它的地方 |
| --- | --- |
| 记账精确 | 增删：新批记账，被取代且不在用的一批放开；`Load`：最新批记账；检查：重建批记账；`BreakLoad`：放开不在用的最新批；`Free`：放开在用批；拷贝的 `Load`、`BreakLoad`、`Free` |
| 不用就不占 | `SetActive(false)`：`BreakLoad` 放开不在用的最新批；结束生命期之后，`Free` 放开在用批 |
| 不需要就不用 | 放开之后计数归零就停用：增删、`BreakLoad`、`Free`，拷贝的 `BreakLoad`、`Free` |
| 需要就在用 | 成组资源的检查激活最新批里没在使用的成员；拷贝的检查激活模板 |
| 能就位即就位 | 检查点覆盖 5.4 的全部评估时机；被联系时转告；陈旧时重建；`Free` 让仍有计数的子成组资源检查；替换时允许嵌套开始 |
| 一份 raw，一次生命期 | 只有基类改 `raw`；`Load`、`BreakLoad` 每个使用周期各调一次；迟到的结果直接 `Free` |
| 下层包住上层 | 被联系的成员由在用批记账，计数不会归零；批不修改；被联系时只转告、不替换；交付要求成员都已齐；上层先 `OnActive(false)`、置空 raw，再 `Free` 放开 |

R4 由此得出：提交时，检查激活新成员；新成员交付是检查点；本组齐了就交付，被联系就转告；转告到没有被联系的祖先，它重建，内层逐级就位。

## 10. 协议

### 10.1 检查点

| 检查点 | 谁调用谁的 `OnDependencyLoaded` |
| --- | --- |
| 下层交付 | 下层的 `OnLoadDone` 结束时，调用它每个不同的上层 |
| 成组的下层已齐但被联系 | 下层转告它的每个成组上层 |
| 上层放开在用的一批 | 上层的 `Free`，对仍有计数的子成组资源 |
| 提交 | `SetActive(true)`，对已在使用的资源自身 |
| 开始使用 | 成组资源与拷贝的 `Load`，记账之后 |

### 10.2 激活与停用

- **激活**：上层在检查时，对它记账、却还没在使用的下层调用 `SetActive(true)`。激活前要看 `active`：对正在使用的资源调用 `SetActive(true)` 是提交，会 `Render`。
- **停用**：放开之后计数归零，就调用 `SetActive(false)`。它对不在使用的资源什么都不做，所以停用前不必看 `active`。
- 只有放开在用的一批（`Free`）时，才让仍有计数的子成组资源检查：只有在用的一批联系着子资源，放开它才可能让子资源可以替换。

### 10.3 成组资源的检查

1. 不在使用：返回。
2. 不待交付时：联系着的子成组资源都不待交付，就返回。有待交付的（陈旧），按 raw 的成员生成重建批，记账，换上；重建批让替换期间仍需要的成员计数不归零。
3. 激活最新批里没在使用的成员；激活了任何一个就返回，它们交付时会再通知本组。
4. 已齐：每个成员都已齐；本组还没联系的子成组资源，还要不待交付。
5. 被联系：转告每个成组上层，返回。否则交付最新批。

第 4 步的附加条件，防的是多重建一次：替换时本组放开在用批之后，几个仍需要的子成组资源依次就位，每个就位都通知本组。若第一个就位时本组就开始新的一批，后面那个还待交付的子成组资源就被联系上了，它就位不了，只能转告本组，本组再重建一次。

不需要「每个成员都已记账」的条件：记账总在激活之前完成。

### 10.4 交付与替换

`OnLoadDone(newRaw)`：

1. 不在使用：迟到的结果，`Free(newRaw)`，返回。只有单个资源会走到这里：成组资源与拷贝只在检查时交付，而检查先看 `active`。
2. 持有 raw，即替换（只有没被联系的成组资源会走到）：`OnActive(old, false)`，raw 置空，`Free(old)`。`Free` 里仍需要的子成组资源检查、就位，并通知本组；本组若因此已齐，就在那次通知里开始了新的一批。所以 `Free` 之后 raw 若已非空，就返回。
3. `OnActive(newRaw, true)`，`raw = newRaw`，`Render`，通知每个不同的上层。

raw 先置空再 `Free`，子资源检查时看到本组已不联系它。`OnActive(true)` 先于赋值、`OnActive(false)` 先于置空，raw 非空的区间恰好夹在两次 `OnActive` 之间。

### 10.5 增删

1. 新批 = `children` 的副本加上或去掉 child；若与 raw 成员相同，就用 raw 本身：改回了在用的一批，不重建。
2. 换上新批。
3. 在使用时：新批不是 raw 就记账；被取代的一批不是 raw 就放开，计数归零的停用。

增删不激活、不交付，也不是检查点。不在使用时只换批。

### 10.6 拷贝

`Load` 对模板记账，再检查。检查时模板没在使用，就激活它并返回；模板已齐，就交付 `CreateClone(template.raw)`。`BreakLoad` 只在还没交付时放开模板，交付了的由 `Free` 放开；`Free` 先 `DestroyClone`，再放开模板；放开后计数归零，就停用模板。`Reference` 的 `CreateClone` 返回模板的 raw 本身，其余方法为空。

## 11. 伪代码

```text
Resource:
    data                                       # 镜像
    raw                                        # 非空当且仅当生命期正在进行
    active                                     # 是否正被使用
    dependents                                 # 多重集合：上层的每一批需要本资源时各记一次

    SetActive(on):
        if on:
            if not active:                     # 开始使用
                active = true
                Load()
            else:                              # 提交
                if raw != null: Render(raw)
                OnDependencyLoaded()           # 检查点
        else if active:                        # 停止使用
            active = false
            BreakLoad()
            if raw != null:
                oldRaw = raw
                OnActive(oldRaw, false)
                raw = null
                Free(oldRaw)

    SetData(data):                             # 只改镜像
        if dependents 里不止一个上层: Trace.TraceWarning("修改了共享的资源")
        this.data = data

    AddDependent(d):    dependents.add(d)                              # 只记账
    RemoveDependent(d): 断言 dependents 里有 d；去掉一次                # 只记账

    OnLoadDone(newRaw):                        # 唯一的交付点
        if not active:
            Free(newRaw)                       # 迟到的结果
            return
        if raw != null:                        # 替换
            oldRaw = raw
            OnActive(oldRaw, false)
            raw = null                         # 先置空再 Free：子资源据此看到已不被本组联系
            Free(oldRaw)                       # 仍有计数的子成组资源在此就位，并通知本组
            if raw != null: return             # 新的一批已在那次通知里开始
        OnActive(newRaw, true)
        raw = newRaw
        Render(raw)
        for d in dependents 中不同的上层: d.OnDependencyLoaded()       # 遍历副本

    IsLoaded(): return raw != null
    OnDependencyLoaded(): 什么都不做
    Load(), BreakLoad(), Free(raw), OnActive(raw, on), Render(raw): 抽象

ResourceGroup : Resource:
    children                                   # 最新的一批；每次增删换成新的集合，旧批不改

    AddChild(child):
        断言 child != null，且不在 children 中
        if dependents 里不止一个上层: Trace.TraceWarning("修改了共享的资源")
        batch = children 的副本 ∪ {child}
        if raw 与 batch 成员相同: batch = raw  # 改回在用的一批
        old = children
        children = batch
        if not active: return
        if batch 不是 raw:
            for c in batch: c.AddDependent(this)
        if old 不是 raw:
            for c in old:
                c.RemoveDependent(this)
                if c.dependents 为空: c.SetActive(false)        # 被放弃的子资源

    RemoveChild(child):
        断言 child 在 children 中
        同 AddChild，只是 batch = children 的副本 − {child}

    IsLoaded():
        return raw != null and children 的每个成员都 IsLoaded()

    Load():
        for c in children: c.AddDependent(this)
        OnDependencyLoaded()

    BreakLoad():
        if children 是 raw: return             # 在用的一批由 Free 放开
        for c in children:
            c.RemoveDependent(this)
            if c.dependents 为空: c.SetActive(false)

    Free(set):
        for c in set:
            c.RemoveDependent(this)
            if c.dependents 为空: c.SetActive(false)
            else if c 是成组资源: c.OnDependencyLoaded()        # 已不被本组联系

    OnDependencyLoaded():
        if not active: return
        if children 是 raw:
            if raw 里没有待交付的子成组资源: return             # 最新
            batch = raw 的副本                                 # 陈旧：重建批
            for c in batch: c.AddDependent(this)
            children = batch
        激活了 = false
        for c in children:
            if not c.active: c.SetActive(true); 激活了 = true
        if 激活了: return                                      # 它们交付时会再通知本组
        for c in children:
            if not c.IsLoaded(): return
            if c 不在 raw 里，且 c 是待交付的成组资源: return
        if 某个上层的 raw 里有本组:
            for u in dependents 中不同的成组资源: u.OnDependencyLoaded()   # 转告就绪
            return
        OnLoadDone(children)

    OnActive(set, on), Render(set): 由具体的成组资源实现

Clone : Resource:
    template                                   # 构造后不变

    Clone(template): 断言 template != null，且不是成组资源

    Load():
        template.AddDependent(this)
        OnDependencyLoaded()

    BreakLoad():
        if raw != null: return                 # 已交付的由 Free 放开
        template.RemoveDependent(this)
        if template.dependents 为空: template.SetActive(false)

    Free(cloneRaw):
        DestroyClone(cloneRaw)                 # 先销毁拷贝，再放开模板
        template.RemoveDependent(this)
        if template.dependents 为空: template.SetActive(false)

    OnDependencyLoaded():
        if not active or raw != null: return
        if not template.active:
            template.SetActive(true)           # 模板交付时会再通知本拷贝
            return
        if template.IsLoaded(): OnLoadDone(CreateClone(template.raw))

    CreateClone(templateRaw) → cloneRaw, DestroyClone(cloneRaw), OnActive, Render: 由具体的拷贝实现

Reference : Clone:
    CreateClone(templateRaw): return templateRaw
    DestroyClone、OnActive、Render: 什么都不做
```

## 12. 关键流程

记法：S0、S1… 是批，即集合对象本身，花括号里是成员；「记账」「放开」指 `AddDependent`、`RemoveDependent`。

### 12.1 一级成组资源 G{a, b}

```text
G.SetActive(true) → G.Load：a、b 记账 → 检查：激活 a、b（a.Load、b.Load）→ 返回
a 到达 → a 开始、Render → G 检查：b 未齐 → 返回
b 到达 → b 开始、Render → G 检查：已齐，未被联系 → G.OnLoadDone(S0)：G 开始、Render

换子资源 S0 = {a, b} → {a, c}：
G.RemoveChild(b)   → S1 = {a}：记账；S0 是 raw，不放开
G.AddChild(c)      → S2 = {a, c}：记账；放开 S1          # 两次增删没有任何生命期调用
G.SetActive(true)  → G.Render(S0)；检查：激活 c → c.Load → 返回
c 到达 → G 检查：已齐 → G.OnLoadDone(S2)
    G.OnActive(S0, false); raw = null
    G.Free(S0)：a 仍有计数；b 归零 → b 停用：OnActive(false)、Free
    G.OnActive(S2, true); raw = S2; G.Render(S2)

G.SetActive(false) → BreakLoad：最新批就是 raw，什么都不做
                   → G.OnActive(S2, false); raw = null; G.Free(S2)：a、c 归零 → 停用
```

c 命中缓存时，提交里激活 c，c 当场交付并通知 G，G 在同一次提交里替换；先加后删也一样，都只替换一次。只删不增时，提交的那次检查直接交付。改回在用的组成（删 b 再加 b）时，新批就是 raw，提交不重建。

### 12.2 资源树 R{s, G{a, b}}：内层增删

```text
G.RemoveChild(b); G.AddChild(c); G.SetActive(true)        # 提交：激活 c
c 到达 → G 检查：已齐，但 R 联系着 G → 转告 R
R 检查：陈旧 → 重建批 {G, s}，记账 → 已齐（G 被 R 联系，已齐即可）→ R 是根 → R.OnLoadDone(重建批)
    R.OnActive({G, s}, false); raw = null
    R.Free({G, s})
        s 仍有计数：单个资源，什么都不做
        G 仍有计数 → G 检查：已不被联系 → G.OnLoadDone({a, c})
            G.OnActive({a, b}, false); raw = null; G.Free({a, b})：b 归零 → 停用
            G.OnActive({a, c}, true); G.Render
            通知 R → R 检查：已齐，G 不待交付 → R.OnLoadDone(重建批)      # 嵌套：R 在此开始
                R.OnActive({G, s}, true); R.Render
    R.raw 已非空 → 返回
```

顺序是 R 结束、G 结束旧的、G 开始新的、R 开始。兄弟 s 只被放开、重新联系，不再 `Render`。几个子成组资源都要就位时，R 在最后一个就位时开始，只重建一次。更深的链同理：逐级向上转告，逐级向下就位。

### 12.3 两级同时改动

P{W{l, r}, body}：P 换身体并提交，激活 body2，body2 开始加载。body2 到达之前，W 换右翼并提交，r2 当场交付；W 已齐但被 P 联系，转告 P；P 还在等 body2，不重建。body2 到达时 P 重建：放开在用批时 W 就位，P 按新身体、新翅膀重新开始。在此之前，角色照常显示旧身体、旧翅膀。

### 12.4 放弃已激活的子资源

```text
G.AddChild(c); G.SetActive(true)   → c 激活，开始加载
G.AddChild(d); G.RemoveChild(c)    → 放开上一批：c 归零 → c 停用，加载被打断；d 只记账
G.SetActive(true)                  → 激活 d
d 到达                             → G 交付 {a, b, d}
```

### 12.5 拷贝与共享

```text
C1.SetActive(true) → C1.Load：T 记账 → C1 检查：T 没在使用 → 激活 T → T.Load
C2.SetActive(true) → C2.Load：T 记账 → C2 检查：T 在使用、未齐 → 返回
T 到达 → T 开始、Render → 通知 C1、C2 → 各自交付 CreateClone(rt)
C1 停用 → C1 结束生命期 → C1.Free：DestroyClone；放开 T，仍有 C2 → T 继续存活
C2 停用 → …… 放开 T，计数归零 → 停用 T
```

成组资源 G1{s}、G2{s} 共享 s 时同理：s 只加载一次，到达时通知 G1、G2；谁先停用都一样，最后放开 s 的一方停用它。G{C} 包含拷贝 C 时，开始的顺序是 T、C、G，结束的顺序是 G、C、T。

## 13. 使用约束

上层代码：

1. `SetActive(false)` 只对根调用；有上层的资源由上层停用。
2. 对还没使用的根调用 `SetActive(true)`，是使用；对正在使用的资源调用，是提交，可以是内部节点。不要对还没使用的内部节点调用 `SetActive(true)`：它会被直接使用，最后一个上层离开时又会被停掉。要共享单个资源，各持一份 `Reference`；要共享成组资源，各自把它加入自己的成组资源。
3. 增删之后紧接着提交（第 7 节第 4 条的第二处放宽）。
4. 共享的资源不改镜像，共享的成组资源不增删（前提 5）；违反时只报警告，结果不保证。

具体资源的实现者：

5. 单个资源的 `Load` 每个使用周期只被调用一次，至多交付一次；`BreakLoad` 打断加载、回滚中间产物。取消不了的加载，结果若在停用期间到达，就是迟到的结果；若下一个使用周期已经开始，`Load` 应复用它，而不是再发起一次。
6. `OnActive(false)` 撤销自己在 `OnActive(true)` 与 `Render` 里的全部修改（前提 7）。
7. 成组资源的 `Render` 只提交子资源的数据，不提交子资源的增删。本组 `Render` 时正处在交付之中，子资源联系在本组的 raw 里；子资源的新一批若在这时就绪，本组就要在自己的 `Render` 里重入重建。

## 14. C# 细节

- `Base` 是单独的程序集（`Design.md` 第 4 节），不引用 `UnityEngine`。
- 经由别的对象访问的成员对程序集可见：`raw` 是 `protected internal`；`active`、`dependents`、`AddDependent`、`RemoveDependent` 是 `internal`。派生类经由基类类型的引用访问不到 `protected` 成员。
- `IsLoaded` 是 `public virtual`；`OnDependencyLoaded` 是 `protected virtual`。成组资源转告上层、在 `Free` 里让子成组资源检查时，先把对方转成 `ResourceGroup` 再调用。成组资源的上层只会是成组资源，因为模板只能是单个资源。
- `OnLoadDone` 是 `protected`，具体资源加载完成后调用它交付。`Load`、`BreakLoad`、`Free`、`OnActive`、`Render`、`CreateClone`、`DestroyClone` 是 `protected abstract`。
- `ResourceGroup`、`Clone` 是抽象类，`Reference` 是具体类。
- 警告用 `System.Diagnostics.Trace.TraceWarning`。要在 Unity 控制台看到，需在 `Engine` 启动时加一个转到 `Debug.LogWarning` 的监听器，尚未做。
- 单元测试在 `Assets/Scripts/Base/Tests`；没有 Unity 时，用 `dotnet test Tools/DotnetTests/BaseTests/BaseTests.csproj` 运行。

## 15. 已知限制与待定

1. **检查的代价。** `IsLoaded` 逐级递归，陈旧检查遍历联系着的子资源，就绪逐级转告时每一级都要重算。目前不考虑效率。
2. **`Engine` 层成组资源读取子资源的 raw。** 具体的成组资源要在 `OnActive` 里读每个子资源的 raw，而 `raw` 是 `protected internal`：`Engine` 程序集里的派生类读不到 `Resource` 类型的子资源的 raw。读取途径等写第一个 `Engine` 层成组资源时再定。
3. **环。** 一个资源若经由子资源或模板成了自己的下层，就永远加载不完。检查要沿 `children` 与 `template` 两条依赖边求依赖闭包（`Resource.md` 15.8 节）；放在 `AddChild` 里做还是在检查点上做，待定。
