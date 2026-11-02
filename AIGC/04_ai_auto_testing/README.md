# AI 自动测试

涵盖：玩法测试 · 画面测试 · Bug 检测

---

## 子方向

### 01 玩法测试
- **强化学习 Agent 自动探索** — PPO/DQN Agent 玩游戏、发现卡关/穿墙
- **LLM 驱动测试用例生成** — 根据设计文档自动生成测试场景
- **行为树 + AI 模拟玩家** — 不同类型玩家行为仿真

### 02 画面测试
- **感知哈希 + 异常检测** — 帧间差异检测、渲染错误
- **CLIP 语义对齐验证** — "场景应该是白天室外" → 视觉验证
- **IQA 图像质量评估** — BRISQUE、CLIP-IQA、NIQE

### 03 Bug 检测
- **视觉异常检测** — 模型穿插、贴图丢失、粒子爆炸
- **LLM 描述 + 规则核对** — 截图 → 多模态 LLM 描述 → 规则引擎判断
- **日志 + 崩溃智能分析** — Crash Log → LLM 根因分析

---

## 学习路径

1. 了解游戏测试现状（人工 QA 痛点）
2. 学习强化学习基础（PPO、环境封装）
3. 研究游戏 AI Agent 测试框架（GameDriver、Appium for Games）
4. 学习多模态模型用于画面理解（GPT-4V、LLaVA、InternVL）
5. 设计异常检测 Pipeline：截图采集 → 模型推理 → 告警系统

---

## 关键论文与资源

- [Atari Deep RL](https://arxiv.org/abs/1312.5602) — DQN 玩 Atari（基础）
- [Game Testing Survey](https://arxiv.org/abs/2007.00767)
- [ClipBERT for Video QA](https://arxiv.org/abs/2102.06183)
- [Visual Anomaly Detection Survey](https://arxiv.org/abs/2401.16402)
- Unity ML-Agents Toolkit 官方文档

---

## 工具链

- **RL 框架**: Stable-Baselines3, RLlib, Unity ML-Agents
- **游戏自动化**: GameDriver, PyAutoGUI, ADB（移动）
- **视觉模型**: LLaVA, InternVL2, GPT-4V
- **异常检测**: PatchCore, EfficientAD, Anomalib
- **测试管理**: Allure, TestRail

---

## 实验方向

- [ ] Unity 小场景 + ML-Agents 自动探索玩法边界
- [ ] 截图 → GPT-4V → 结构化 Bug 报告自动生成
- [ ] 渲染帧视觉异常检测 Demo（穿插/贴图缺失）
