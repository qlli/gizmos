# PCG + AI 场景生成

核心问题：如何结合传统程序化生成与 AI 模型，生成语义合理、视觉丰富的游戏场景。

---

## 技术体系

### 传统 PCG 层
- **WFC (Wave Function Collapse)** — 基于约束的 Tile 拼接
- **Grammar-based** — L-System、Split Grammar（建筑/植被）
- **Noise-based** — Perlin/Simplex Noise 地形基础
- **Graph-based** — 空间图结构（房间、道路网络）

### AI 增强层
- **LLM 语义约束** — 自然语言描述 → 场景规则/参数
- **Diffusion 纹理/细节生成** — 场景贴图的 AI 填充
- **3D 场景理解** — 用视觉模型检查生成结果合理性
- **风格迁移** — 将参考美术风格迁移到生成场景

---

## 学习路径

1. 掌握经典 PCG 算法：Noise、WFC、BSP、Voronoi
2. 学习 LLM + 结构化输出驱动参数生成（JSON Schema / Function Calling）
3. 研究语义场景图（Scene Graph）与 3D 扩散模型
4. 实验：Blender/Unreal 中接入 LLM 自动摆放资产
5. 探索端到端场景生成（如 SceneScript、HoloDeck、InstructScene）

---

## 关键技术与论文

- [WFC 原理](https://github.com/mxgmn/WaveFunctionCollapse)
- [ProcGen Survey](https://arxiv.org/abs/2210.10078)
- [HoloDeck](https://arxiv.org/abs/2312.09067) — LLM 驱动 3D 场景生成
- [SceneScript](https://arxiv.org/abs/2403.13064) — 结构化场景描述生成
- [InstructScene](https://arxiv.org/abs/2402.04717) — 指令驱动室内场景
- [Set-the-Scene](https://arxiv.org/abs/2303.14613) — 可控 3D 场景合成

---

## 工具链

- **PCG 引擎**: Unreal PCG Graph, Houdini, Unity DOTS
- **LLM 接入**: OpenAI Function Calling, LangChain
- **3D 场景生成**: BlenderLM, ProcTHOR, AI2-THOR
- **可视化验证**: Unreal Sequencer, Blender EEVEE

---

## 实验方向

- [ ] LLM 输出 JSON 场景描述 → Unreal 自动实例化资产
- [ ] WFC + LLM 语义后处理：生成后检查逻辑合理性
- [ ] Diffusion 辅助场景贴图变体生成
