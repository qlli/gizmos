# AIGC 游戏资产工程化

涵盖：原画 · 三维模型 · 角色动画 · 绑定 · 贴图增强 · 剧情动画

---

## 子方向索引

| 子方向 | 核心问题 | 关键技术 |
|--------|---------|---------|
| [01 原画生成](01_concept_art/README.md) | 如何高效生成符合美术风格的原画 | SD/Flux + ControlNet + LoRA |
| [02 三维模型](02_3d_model/README.md) | 从图像/文本生成可用游戏模型 | TripoSR / InstantMesh / Rodin |
| [03 角色动画](03_character_animation/README.md) | 动作序列的 AI 生成与迁移 | MotionDiffuse / MDM / MoCap |
| [04 自动绑定](04_rigging/README.md) | 骨骼自动绑定与蒙皮 | RigNet / Neural Skinning |
| [05 贴图增强](05_texture_enhancement/README.md) | 低分辨率贴图超分与细节生成 | ControlNet Tile / Upscaler |
| [06 剧情动画](06_cinematic_animation/README.md) | AI 驱动剧情动画制作 | Motion + Camera + LLM 脚本 |

---

## 学习路径（建议顺序）

1. 掌握 Stable Diffusion 基础生态（WebUI / ComfyUI）
2. 学习 ControlNet 各 Preprocessor 用途（Canny/Depth/OpenPose/Tile）
3. 理解 LoRA/DreamBooth 微调，用于风格定制
4. 进入 3D 生成：NeRF → 3DGS → Mesh 重建管线
5. 动画方向：了解 Motion Capture 数据格式（BVH/FBX），再接 Motion Diffusion
6. 研究资产适配：生成物如何满足游戏引擎 LOD/碰撞/材质规范

---

## 工具链

- **生图**: ComfyUI, Stable Diffusion WebUI, Fooocus
- **3D生成**: TripoSR, InstantMesh, Meshy, Rodin
- **动画**: Motion Diffuse, MDM, AnimateDiff
- **绑定**: RigNet, Mixamo (工业), AccuRIG
- **贴图超分**: Real-ESRGAN, ControlNet Tile, Magnific
- **引擎集成**: Unity AI, Unreal MetaHuman, Blender

---

## 关键论文

- [DreamFusion](https://arxiv.org/abs/2209.14988) — Text-to-3D 基础
- [Zero-1-to-3](https://arxiv.org/abs/2303.11328) — 单图3D视角合成
- [InstantMesh](https://arxiv.org/abs/2404.07191) — 快速多视角重建
- [MDM](https://arxiv.org/abs/2209.14916) — Human Motion Diffusion
- [MotionDiffuse](https://arxiv.org/abs/2208.15001) — 文本驱动动作生成
- [RigNet](https://arxiv.org/abs/2005.00559) — 自动骨骼绑定

---

## 实验记录

见 `experiments/` 子目录，按日期命名实验文件夹。
