# AI Agent 与自动化工作流

核心目标：构建游戏研发场景下的数字员工和自动化协同系统。

---

## 应用场景

| 场景 | 描述 |
|------|------|
| 需求拆解 Agent | PRD → 任务列表 + 技术方案自动生成 |
| 代码生成 Agent | 需求描述 → 代码实现 + 单测 |
| 资产生产 Agent | 概念描述 → 原画 → 3D 模型 → 绑定 全链路 |
| QA Agent | 测试用例自动生成 + 执行 + 报告 |
| 知识库 Agent | 项目文档问答、规范查询 |
| 研发协同 Agent | PR 审查、代码规范检查、技术债务分析 |

---

## 技术框架对比

| 框架 | 特点 | 适用场景 |
|------|------|---------|
| LangChain | 工具链丰富，成熟 | 快速原型 |
| LangGraph | 有向图工作流，可控 | 复杂多步 Agent |
| AutoGen | 多 Agent 对话协作 | 代码生成/评审 |
| CrewAI | 角色化 Agent 团队 | 跨职能协同 |
| Agno | 轻量，高性能 | 生产部署 |
| Dify | 无代码工作流 | 快速业务落地 |

---

## 学习路径

1. 理解 ReAct / CoT / Tool Use 基本 Agent 模式
2. 掌握 LangGraph 有向图工作流设计
3. 学习 Function Calling / Tool Calling 规范（OpenAI / Anthropic）
4. 研究 Multi-Agent 协作模式（AutoGen、CrewAI）
5. 设计游戏研发场景的 Agent 角色体系
6. 实践：从单 Agent 工具调用 → 多 Agent 协同系统

---

## 关键概念

- **Memory**: 短期（对话历史）+ 长期（向量数据库）
- **Planning**: CoT、ToT、MCTS 推理
- **Tool Use**: 代码执行、API 调用、文件操作
- **Reflection**: 自我批评、结果验证、循环优化
- **Human-in-the-Loop**: 关键决策节点人工确认

---

## 关键论文与资源

- [ReAct](https://arxiv.org/abs/2210.03629) — Reasoning + Acting
- [AutoGen](https://arxiv.org/abs/2308.08155) — Multi-Agent Conversation
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [Toolformer](https://arxiv.org/abs/2302.04761)
- [HuggingGPT](https://arxiv.org/abs/2303.17580)
- [AgentBench](https://arxiv.org/abs/2308.03688) — Agent 能力基准

---

## 实验方向

- [ ] LangGraph 实现资产生产工作流（文本 → 原画 → 模型）
- [ ] AutoGen 实现代码 Review + 修复多 Agent 系统
- [ ] 游戏项目知识库 RAG Agent（文档/规范问答）
- [ ] PRD 解析 → 自动拆解任务并分配给不同工具 Agent
