# 整体路线图与方法论

## 核心目标

以 AI-Native 工作模式为导向，在游戏研发的以下四个维度建立可复用实践：

1. **组织效率提升** — AI Coding、自动化工作流、数字员工
2. **AIGC 资产工程化** — 原画→模型→动画→绑定→贴图→剧情动画全链路
3. **新范式研发** — PCG+AI 场景、AI 自动测试、AI 镜头、AI 渲染参数
4. **知识沉淀与推广** — 从 0→1 验证，再到 1→N 规模化

---

## 学习阶段划分

### Phase 1 — 基础补齐（扎根）
目标：建立各方向的技术认知地图，了解 SOTA 模型和工具链。

- [→] 计算机视觉基础回顾（ViT、Diffusion、NeRF/3DGS）← **当前进行中** → [详细文档](phase1_01_cv_basics.md)
- [ ] 多模态大模型原理（CLIP、LLaVA、GPT-4V）
- [ ] Diffusion 模型体系（SD、SDXL、Flux、ControlNet、LoRA）
- [ ] 3D 生成基础（TripoSR、Zero123、Instant3D、DreamFusion）
- [ ] AI Coding 工具链（Cursor、Copilot、CodeAgent 框架）
- [ ] Agent 框架（LangChain、LangGraph、AutoGen、CrewAI）

### Phase 2 — 方向深耕（立柱）
目标：在 2-3 个核心方向完成从 0→1 的工程落地。

- [ ] AIGC 原画管线（ComfyUI + ControlNet + LoRA 微调）
- [ ] AI 角色动画（MoCap + Motion Diffusion + RetargetNet）
- [ ] PCG+AI 场景生成（WFC/Grammar + LLM 语义约束）
- [ ] AI 自动 Bug 检测（视觉异常检测 + LLM 描述）
- [ ] AI Coding Agent 接入真实研发流程

### Phase 3 — 系统化（扩面）
目标：将验证的单点能力系统化，建立可推广的工作流。

- [ ] AIGC 资产适配游戏管线（LOD、碰撞、材质标准化）
- [ ] AI 自动打光与渲染参数生成
- [ ] AI 镜头系统（关键帧驱动 + 情绪感知）
- [ ] 数字员工 / 自动化协同系统
- [ ] 团队培养与方法论文档化

---

## 关键技术判断原则

1. **先看能否用，再看能否改，最后才考虑自研**
2. **工程化 > 算法精度**：美术/研发可用的工具 > 指标最好的论文复现
3. **闭环验证**：每个方向都要有可度量的效果指标
4. **美术视角优先**：从美术痛点出发设计方案，而非从技术倒推

---

## 资源优先级排序

| 优先级 | 类型 |
|--------|------|
| P0 | Siggraph / CVPR / ICCV 游戏/资产相关 best paper |
| P0 | Unity/Unreal 官方 AI 集成方案 |
| P1 | Hugging Face 模型卡与 Demo |
| P1 | 行业 Blog（Activision、EA、Epic 技术博客）|
| P2 | arXiv 预印本（按方向订阅）|

---

## 进度追踪

见各方向 `README.md` 中的 checklist，以及 `decisions.md` 记录关键技术选型。
