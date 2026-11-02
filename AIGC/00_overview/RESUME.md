# 项目恢复手册（RESUME）

> 生成时间：2026-09-18
> 用途：旧版 CodeBuddy 会话丢失后，重建本工程的完整上下文，可直接接续工作。

---

## 1. 项目定位

**AI 辅助游戏开发 — 学习与工程实验工程**

以 AI-Native 工作模式为导向，在游戏研发四个维度建立可复用实践：

| 维度 | 内容 |
|------|------|
| 组织效率 | AI Coding、自动化工作流、数字员工 |
| AIGC 资产工程化 | 原画→模型→动画→绑定→贴图→剧情动画全链路 |
| 新范式研发 | PCG+AI 场景、AI 自动测试、AI 镜头、AI 渲染参数 |
| 知识沉淀推广 | 0→1 验证，再 1→N 规模化 |

工程路径：`D:\proj\gizmos\AIGC`（父仓库 `D:\proj\gizmos`，git remote `https://github.com/qlli/gizmos.git`，分支 main）

---

## 2. 时间线与当前进度

| 时间 | 动作 | 产物 |
|------|------|------|
| 2026-09-16 10:30 | 工程初始化 | 根 README + 10 个方向目录骨架 |
| 2026-09-16 10:30–10:34 | 各方向 README 落地 | 11 个方向 README（学习路径 + 论文 + 工具链） |
| 2026-09-17 02:14 | Phase 1 第一子方向完成 | `00_overview/phase1_01_cv_basics.md`（10.7 KB，ViT/Diffusion/NeRF/3DGS 知识地图） |
| 2026-09-17 02:14 | roadmap 更新 | 标记"计算机视觉基础回顾"为**进行中** |
| 2026-09-18 06:21–06:22 | **AI 自动镜头方向集中推进** | 5 篇文档 + 05 目录 README 重写 |
| 2026-11-02 | 工作汇报图表 | `00_overview/ai_gamedev_directions_report.html`（10 方向总结） |
| 2026-11-02 | **新增"增效"路线：体验创新** | `11_experience_innovation/` 12 篇（方法论 + 7 个专题 + 28 领域清单 + 资料清单 + 机会矩阵） |

**最后停留位置：`05_ai_auto_camera`（AI 自动镜头）** — 这是当前活跃分支。
`11_experience_innovation/10_opportunity_matrix.md` 给出的主线建议：以 05 为核心，在 **MOBA 团战高光与回放** 场景做 P0–P5 闭环验证（团战检测 → 规则镜头 → 导播剪辑 → 学习镜头 → 声画统一 → 实时化）。

---

## 3. 完成度矩阵

| 方向 | 目录 | 状态 |
|------|------|------|
| 整体规划 | `00_overview/` | ✅ roadmap + decisions + CV 基础 |
| AIGC 资产 | `01_aigc_assets/` | 🟡 仅 README + 原画子目录 README |
| AI Coding | `02_ai_coding/` | 🟡 仅 README（4 个子目录空） |
| PCG+AI 场景 | `03_pcg_scene_generation/` | 🟡 仅 README |
| AI 自动测试 | `04_ai_auto_testing/` | 🟡 仅 README（3 个子目录空） |
| **AI 自动镜头** | `05_ai_auto_camera/` | 🟢 **两层已完成，两层待补** |
| 资产管线适配 | `06_asset_pipeline_adaptation/` | 🟡 仅 README |
| AI 渲染参数 | `07_ai_rendering_params/` | 🟡 仅 README（3 个子目录空） |
| Agent 工作流 | `08_ai_agent_workflow/` | 🟡 仅 README |
| 实验记录 | `09_experiments/` | 🟡 仅 README |
| 通用资料 | `10_resources/` | 🟡 仅 README |
| **体验创新（增效）** | `11_experience_innovation/` | 🟢 首版完成：README + 00–10 共 12 篇 |

### 05_ai_auto_camera 内部进度

| 层级 | 内容 | 状态 |
|------|------|------|
| 第一层 | 电影镜头语言基础 | ✅ 理论框架 / 书单 / 课程 / 视频资源 4 篇齐备 |
| 第二层 | 电影→游戏映射 | ✅ `film_to_game_mapping.md`（控制权分配、景别运动剪辑实现、状态机驱动、情感驱动镜头） |
| 第三层 | GDC/SIGGRAPH 顶会论文 | ⬜ `02_gdc_siggraph/` 空 |
| 第三层 | 引擎教程（UE Sequencer / Unity Cinemachine） | ⬜ `03_engine_tutorials/` 空 |
| 第三层 | 开源项目走读 | ⬜ `04_open_source/` 空 |
| 第四层 | AI 自动镜头研究前沿 | ⬜ `05_ai_camera/` 空 |

---

## 4. Phase 1 学习路线进度

来源：`00_overview/roadmap.md`

| 子项 | 状态 |
|------|------|
| 计算机视觉基础回顾（ViT、Diffusion、NeRF/3DGS） | 🔵 进行中（文档已写，待消化/实验） |
| 多模态大模型原理（CLIP、LLaVA、GPT-4V） | ⬜ |
| Diffusion 模型体系（SD、SDXL、Flux、ControlNet、LoRA） | ⬜ |
| 3D 生成基础（TripoSR、Zero123、Instant3D、DreamFusion） | ⬜ |
| AI Coding 工具链（Cursor、Copilot、CodeAgent） | ⬜ |
| Agent 框架（LangChain、LangGraph、AutoGen、CrewAI） | ⬜ |

**待决策事项**（`00_overview/decisions.md`，全部未决）：

- 3D 生成主路线：TripoSR vs InstantMesh vs Rodin
- Agent 框架主选：LangGraph vs AutoGen vs CrewAI
- 代码生成 LLM：DeepSeek-Coder vs Qwen-Coder vs GPT-4o
- 场景生成方案：PCG+LLM vs 端到端 3D Diffusion
- 贴图生成：ComfyUI 工作流 vs Substance AI vs 自建管线

---

## 5. 下一步候选（三选一）

### A. 继续深耕 AI 自动镜头（推荐，顺势）
1. 补 `02_gdc_siggraph/`：Virtual Cinematographer (SIGGRAPH 1996)、Example-driven Cinematography (2020)、Camera Keyframing with Style (SIGGRAPH Asia 2021)、50 Game Camera Mistakes (GDC 2014)
2. 补 `03_engine_tutorials/`：UE5 Cine Camera Actor + Sequencer + Camera Cut Track 实操（与本职 UE5 开发强相关）
3. 补 `05_ai_camera/`：Cine-AI 开源项目走读、LLM 剧情→情绪→镜头 JSON 方案设计

### B. 回到 Phase 1 主线
推进"多模态大模型原理（CLIP / LLaVA / GPT-4V）"，保持与 roadmap 一致的节奏。

### C. 做工程实验
`09_experiments/` 目前为空，可落地最小闭环：UE5 Sequencer + LLM 生成镜头脚本 → 自动出一段过场动画。

---

## 6. 工程技术判断原则（沿用）

1. 先看能否用，再看能否改，最后才考虑自研
2. 工程化 > 算法精度：美术/研发可用的工具 > 指标最好的论文复现
3. 闭环验证：每个方向都要有可度量的效果指标
4. 美术视角优先：从美术痛点出发设计方案，而非从技术倒推

**资源优先级**：P0 = Siggraph/CVPR/ICCV 游戏资产相关 best paper、Unity/Unreal 官方 AI 方案；P1 = HuggingFace 模型卡 Demo、行业 Blog；P2 = arXiv 预印本。

---

## 7. 恢复操作指引

- **切换工作区**：在 WorkBuddy / CodeBuddy 中打开文件夹 `D:\proj\gizmos\AIGC`
- **接续对话**：直接说"读 `00_overview/RESUME.md` 并继续 XX 方向"，即可恢复上下文
- **更新本文档**：每次阶段性收尾时刷新第 2、3 节的进度表
