# Phase 1 · 第一子方向：计算机视觉基础回顾

> 覆盖：ViT · Diffusion 扩散模型 · NeRF · 3D Gaussian Splatting
> 目标：建立这四条技术线的完整认知地图，理解原理、演进脉络与游戏场景下的应用价值。

---

## 知识地图总览

```
计算机视觉基础
│
├── A. 视觉表征（理解图像）
│   ├── CNN 体系（ResNet, EfficientNet）      ← 前置知识
│   └── Transformer 体系
│       ├── ViT（Vision Transformer）         ← 核心
│       ├── DINO / DINOv2（自监督视觉）
│       └── SAM（Segment Anything Model）
│
├── B. 图像生成（生成图像）
│   └── Diffusion 扩散模型体系
│       ├── DDPM（去噪扩散概率模型）          ← 理论基础
│       ├── DDIM（加速采样）
│       ├── LDM（Latent Diffusion = SD基础）  ← 核心
│       └── Flow Matching（Flux的基础）
│
├── C. 场景三维重建（理解空间）
│   ├── NeRF                                  ← 核心
│   │   ├── Instant-NGP（加速版）
│   │   └── Mip-NeRF 360（无界场景）
│   └── 3D Gaussian Splatting（3DGS）         ← 核心（当前SOTA）
│       └── 2D Gaussian Splatting（2DGS）
│
└── D. 联结点（游戏方向应用）
    ├── ViT → CLIP → 多模态理解
    ├── Diffusion → SD/Flux → 原画/贴图生成
    └── NeRF/3DGS → 场景重建 → 资产捕获管线
```

---

## A. ViT — Vision Transformer

### 核心思想
将图像切成 Patch（16×16 像素块），展平后当作 token 序列，送入标准 Transformer Encoder，用 [CLS] token 做分类。

### 关键演进

| 模型 | 年份 | 贡献 |
|------|------|------|
| ViT | 2020 | 图像分类首用纯 Transformer |
| DeiT | 2021 | 无需大规模预训练数据的知识蒸馏 |
| Swin Transformer | 2021 | 层级化窗口注意力，适合密集预测 |
| DINO | 2021 | 自监督 ViT，特征强大 |
| DINOv2 | 2023 | 大规模自监督，通用视觉骨干 |
| SAM | 2023 | ViT + 提示驱动分割 |

### 学习重点
1. Multi-Head Self-Attention 的计算过程（Q/K/V）
2. Patch Embedding 的实现方式
3. 位置编码（可学习 vs 正弦）
4. ViT vs CNN：归纳偏置的差异

### 代码入门
```python
# 安装
pip install timm transformers

# 加载预训练 ViT
import timm
model = timm.create_model('vit_base_patch16_224', pretrained=True)

# 或用 HuggingFace
from transformers import ViTModel
model = ViTModel.from_pretrained('google/vit-base-patch16-224')
```

### 关键论文
- [An Image is Worth 16x16 Words: ViT](https://arxiv.org/abs/2010.11929) ⭐ 必读
- [Swin Transformer](https://arxiv.org/abs/2103.14030) ⭐ 必读
- [DINO](https://arxiv.org/abs/2104.14294)
- [DINOv2](https://arxiv.org/abs/2304.07193)
- [SAM](https://arxiv.org/abs/2304.02643)

### 游戏场景应用
- DINOv2 特征 → 场景语义分割（自动标注地形类型）
- SAM → 资产自动抠图（原画分层、贴图提取）
- ViT 特征 → 图像风格相似度计算（AIGC 质量评估）

---

## B. Diffusion 扩散模型

### 核心思想
**正向过程**：逐步向图像添加高斯噪声，直到变成纯噪声。
**反向过程**：训练神经网络（U-Net/DiT）学习逐步去噪，从噪声还原图像。

### 关键演进

| 模型 | 年份 | 贡献 |
|------|------|------|
| DDPM | 2020 | 扩散模型基础，1000步采样 |
| DDIM | 2020 | 非马尔科夫加速，50步可用 |
| Classifier-Free Guidance | 2022 | 文本/条件引导生成 |
| LDM (Stable Diffusion) | 2022 | 在潜空间扩散，大幅降低计算量 ⭐ |
| SDXL | 2023 | 更大分辨率，双文本编码器 |
| DiT | 2022 | 用 Transformer 替换 U-Net 做去噪 |
| Flux.1 | 2024 | Flow Matching + DiT，当前最强 |

### 核心概念

#### 1. DDPM 数学基础
```
正向（加噪）：q(x_t | x_{t-1}) = N(x_t; √(1-β_t)·x_{t-1}, β_t·I)
反向（去噪）：p_θ(x_{t-1} | x_t) = N(x_{t-1}; μ_θ(x_t,t), Σ_θ(x_t,t))
目标：训练 ε_θ 预测噪声 → L = ||ε - ε_θ(x_t, t)||²
```

#### 2. Latent Diffusion（SD 的核心）
```
原始图像 → VAE Encoder → 潜空间 (64×64×4)
                              ↓
                    在潜空间做扩散/去噪（U-Net）
                              ↓
潜码 → VAE Decoder → 高分辨率图像 (512×512×3)

文本条件：CLIP 文本编码器 → 交叉注意力注入 U-Net
```

#### 3. Classifier-Free Guidance（CFG）
```python
# 推理时混合有条件和无条件预测
noise_pred = uncond_pred + guidance_scale * (cond_pred - uncond_pred)
# guidance_scale 越大 → 越遵循文字描述，多样性降低
```

### 代码入门
```python
pip install diffusers transformers accelerate

from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

image = pipe("a fantasy game character, concept art").images[0]
```

### 关键论文
- [DDPM](https://arxiv.org/abs/2006.11239) ⭐ 必读（理论基础）
- [DDIM](https://arxiv.org/abs/2010.02502) ⭐ 必读（加速采样）
- [LDM (Stable Diffusion)](https://arxiv.org/abs/2112.10752) ⭐ 必读
- [Classifier-Free Guidance](https://arxiv.org/abs/2207.12598)
- [DiT](https://arxiv.org/abs/2212.09748)
- [Flow Matching](https://arxiv.org/abs/2210.02747)（Flux 基础）

### 游戏场景应用
- 原画概念图批量生成
- 贴图变体与风格化
- 角色服装/道具设计辅助
- Inpainting 局部内容替换

---

## C. NeRF — Neural Radiance Field

### 核心思想
用 MLP 隐式表示三维场景：输入 3D 坐标 (x,y,z) + 观察方向 (θ,φ) → 输出颜色 (RGB) + 体积密度 (σ)。通过体渲染公式合成 2D 图像，与真实照片对比训练。

### 关键演进

| 模型 | 年份 | 贡献 |
|------|------|------|
| NeRF | 2020 | 隐式神经表示基础 ⭐ |
| NeRF-W | 2021 | 野外场景（光照变化）|
| Mip-NeRF | 2021 | 抗混叠，多尺度 |
| Instant-NGP | 2022 | Hash 编码加速，秒级训练 ⭐ |
| Mip-NeRF 360 | 2022 | 无界场景 |
| Zip-NeRF | 2023 | 结合 Mip + Hash |

### 核心原理
```
体渲染公式：
C(r) = ∫ T(t)·σ(r(t))·c(r(t),d) dt
T(t) = exp(-∫₀ᵗ σ(r(s)) ds)   # 透射率

其中：
- r(t) = o + td  光线方程
- σ      体积密度（不透明度）
- c      颜色
- T      累积透射率（前面遮挡的影响）
```

### 代码入门
```bash
# Instant-NGP（最实用）
git clone https://github.com/NVlabs/instant-ngp
# 或使用 nerfstudio（更友好）
pip install nerfstudio
ns-train nerfacto --data /path/to/images
```

### 关键论文
- [NeRF](https://arxiv.org/abs/2003.08934) ⭐ 必读（原始论文）
- [Instant-NGP](https://arxiv.org/abs/2201.05989) ⭐ 必读（实用版）
- [Mip-NeRF 360](https://arxiv.org/abs/2111.12077)

### 游戏场景应用
- 实景扫描 → NeRF 重建 → 资产捕获（替代传统摄影测量）
- NeRF 渲染新视角 → 3D 模型生成的监督信号
- 场景级 NeRF → PCG 场景合成素材库

---

## D. 3D Gaussian Splatting（3DGS）

### 核心思想
用大量 3D 高斯椭球体（Gaussian Primitives）显式表示场景，每个高斯有位置、形状（协方差）、颜色（球谐系数）、不透明度参数，通过光栅化（而非光线步进）渲染，速度极快。

### 对比 NeRF

| 维度 | NeRF | 3DGS |
|------|------|------|
| 表示方式 | 隐式 MLP | 显式高斯点云 |
| 渲染速度 | 慢（光线步进）| 实时（光栅化）|
| 训练速度 | 分钟~小时 | 分钟级 |
| 编辑能力 | 困难 | 相对容易 |
| 内存占用 | 小 | 大 |
| 适合场景 | 静态场景重建 | 实时渲染、动态场景 |

### 关键演进

| 模型 | 年份 | 贡献 |
|------|------|------|
| 3DGS | 2023 | 实时高质量新视角合成 ⭐ |
| 2DGS | 2024 | 2D 高斯盘，更好几何 |
| 4DGS | 2024 | 动态场景（时间维度）|
| Scaffold-GS | 2023 | 更紧凑的表示 |
| GaussianAvatars | 2024 | 人体/头像动画 |

### 代码入门
```bash
# 官方实现
git clone https://github.com/graphdeco-inria/gaussian-splatting
pip install plyfile tqdm

# 更易用的框架
pip install gsplat  # nerfstudio 团队出品

# 可视化
# 使用 SuperSplat 或 3DGS Viewer 在线查看 .ply 文件
```

### 关键论文
- [3D Gaussian Splatting](https://arxiv.org/abs/2308.04079) ⭐ 必读
- [2DGS](https://arxiv.org/abs/2403.17888)
- [GaussianAvatars](https://arxiv.org/abs/2312.02069)
- [4DGS](https://arxiv.org/abs/2310.08528)

### 游戏场景应用
- 实景扫描 → 3DGS → 实时渲染（替代传统三维重建）
- 角色/道具快速数字化：多视角拍照 → 3DGS → 游戏资产
- 3DGS 作为场景表示，接入 AI 编辑（换风格/补全）

---

## 学习顺序建议

```
Week 1-2  ViT
  → 阅读 ViT 原论文，手写 Patch Embedding + Self-Attention
  → 用 timm 加载模型，可视化 Attention Map
  → 阅读 DINO，理解自监督视觉表征

Week 3-4  Diffusion 基础
  → 阅读 DDPM，推导正/反向过程公式
  → 阅读 DDIM，理解 ODE 采样
  → 阅读 LDM，理解潜空间扩散

Week 5-6  Diffusion 实战
  → 用 diffusers 库跑通 SD 推理
  → 研读 ControlNet 代码，理解条件注入机制
  → 尝试 ComfyUI 基础工作流搭建

Week 7-8  NeRF
  → 阅读 NeRF 原论文，理解体渲染公式
  → 用 nerfstudio 跑通 nerfacto
  → 用 Instant-NGP 跑自己拍摄的照片集

Week 9-10  3DGS
  → 阅读 3DGS 论文，对比 NeRF 的差异
  → 跑官方代码，重建一个小场景
  → 用 SuperSplat 可视化并编辑高斯点云
```

---

## 检验标准（完成即打勾）

- [ ] 能用自己的话解释 ViT 的 Patch Embedding 和 Attention 机制
- [ ] 能推导 DDPM 正向加噪公式和 ELBO 训练目标
- [ ] 能解释 Classifier-Free Guidance 的作用和 guidance_scale 的意义
- [ ] 用 diffusers 成功生成图像并理解每个参数含义
- [ ] 能解释 NeRF 体渲染公式中每项的物理意义
- [ ] 用 nerfstudio 完成一次完整的场景重建
- [ ] 能说出 3DGS 与 NeRF 在表示、渲染、编辑上的核心差异
- [ ] 用 gaussian-splatting 重建一个自己的场景

---

## 补充：游戏行业参考资料

- [Epic: Using AI for World Building (GDC 2023)](https://gdcvault.com/)
- [Unity NeRF Integration Blog](https://blog.unity.com/)
- Activision 扫描工作室技术博客（光场/NeRF 在角色扫描中的应用）
- [Luma AI](https://lumalabs.ai/) — 商业化 NeRF/3DGS 服务，值得体验
