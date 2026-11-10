# AI 自动生成渲染/布料/光照参数

涵盖：渲染参数 · 布料参数 · 自动打光

---

## 01 AI 自动生成画面参数

目标：根据场景内容/风格需求，自动推荐后处理参数（色调、曝光、景深、Bloom 等）。

### 思路
- 场景截图 → 多模态模型理解风格 → 输出参数 JSON
- 风格参考图 → CLIP 特征匹配 → 后处理参数迁移
- 强化学习：以人类评分/风格相似度为奖励训练参数生成器

### 关键工具
- Unreal Post Process Volume API
- Unity Volume Profile
- CLIP / DINO 特征提取

---

## 02 AI 自动生成布料参数

目标：根据布料视觉参考（照片/描述），自动推断物理仿真参数（刚度、阻尼、质量等）。

### 思路
- 布料视频/图片 → 物理参数逆推（Inverse Simulation）
- LLM + 材质知识库：描述布料材质 → 推荐参数范围
- 差分渲染：可微仿真 + 梯度优化

### 关键工具
- Unreal Chaos Cloth
- NVIDIA Flex / PhysX Clothing
- DiffCloth（可微布料仿真）

### 关键论文
- [DiffCloth](https://arxiv.org/abs/2111.10127) — 可微布料仿真
- [NeuralCloth](https://arxiv.org/abs/2208.01542)

---

## 03 AI 自动打光

目标：根据场景/角色，自动推荐或生成光照方案。

### 思路
- 参考图像 → HDR 环境光估计（Light Estimation）
- 场景分析 → 主光/补光/轮廓光自动摆放
- 强化学习优化光照美感评分

### 关键技术
- 光照估计：DiffusionLight, DiLightNet, Neural Gaffer
- HDR 重建：Gardner et al. 室内光照估计
- 引擎光照 API：Unreal Lumen, Unity HDRP

### 关键论文
- [DiffusionLight](https://arxiv.org/abs/2312.09168)
- [Neural Gaffer](https://arxiv.org/abs/2406.07420)
- [DiLightNet](https://arxiv.org/abs/2402.11640)

---

## 学习路径

1. 掌握 PBR 渲染原理（BRDF、IBL、GGX）
2. 学习光照估计基础（球谐函数、环境贴图）
3. 研究可微渲染（Mitsuba3、nvdiffrast）
4. 实验：参考图 → 自动打光参数推荐

---

## 实验方向

- [ ] CLIP 驱动的风格后处理参数迁移 Demo
- [ ] DiffusionLight 接入 Blender 自动打光实验
- [ ] 布料材质描述 → 物理参数推荐工具
