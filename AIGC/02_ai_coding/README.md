# AI Coding 工程化

涵盖：代码生成 · 测试辅助 · 代码评审 · 研发协同

---

## 子方向索引

| 子方向 | 核心问题 | 关键技术 |
|--------|---------|---------|
| [01 代码生成](01_code_generation/README.md) | LLM 辅助游戏逻辑/Shader/工具编写 | Copilot / Cursor / CodeLlama |
| [02 测试辅助](02_test_assistance/README.md) | 自动生成单测、玩法回归测试用例 | LLM + 测试框架 |
| [03 代码评审](03_code_review/README.md) | AI 辅助 Code Review，规范检查 | CodeAgent + AST 分析 |
| [04 研发协同](04_dev_collaboration/README.md) | 数字员工、自动化工作流接入 | AutoGen / CrewAI / 企业级 Agent |

---

## 学习路径

1. 熟悉主流 AI Coding 工具：GitHub Copilot、Cursor、Codeium
2. 理解 Code LLM 原理（CodeLlama、DeepSeek-Coder、Qwen-Coder）
3. 学习 Agent 框架：LangChain → LangGraph → AutoGen → CrewAI
4. 研究 CodeAgent 在游戏研发场景中的落地：Shader 生成、蓝图辅助、工具脚本
5. 设计企业级研发协同系统：PR 审查 → 需求拆解 → 代码生成 → 测试 → 部署

---

## 工具链

- **IDE 集成**: GitHub Copilot, Cursor, Codeium, Tabnine
- **Code LLM**: DeepSeek-Coder, Qwen2.5-Coder, CodeLlama, StarCoder2
- **Agent 框架**: LangGraph, AutoGen, CrewAI, Agno
- **代码分析**: Tree-sitter (AST), SonarQube, semgrep
- **CI/CD 集成**: GitHub Actions, GitLab CI + LLM Hook

---

## 关键论文与资源

- [Copilot Evaluation](https://arxiv.org/abs/2302.06590) — GitHub Copilot 实证研究
- [CodeAgent](https://arxiv.org/abs/2402.01030) — 代码生成 Agent 框架
- [SWE-bench](https://arxiv.org/abs/2310.06770) — 代码 Agent 基准测试
- [AutoCodeRover](https://arxiv.org/abs/2404.05427) — 自动软件工程 Agent
- DeepSeek-Coder 技术报告

---

## 游戏研发特化场景

- **Shader/HLSL 辅助生成** — 特效美术需求转代码
- **Unreal Blueprint ↔ C++ 互转**
- **Unity Editor 工具脚本自动生成**
- **游戏逻辑 BUG 定位辅助**
- **性能优化建议生成**
