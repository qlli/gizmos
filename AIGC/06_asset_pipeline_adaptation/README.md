# AIGC 资产自动适配游戏管线

核心问题：AI 生成的资产（模型/贴图/动画）如何自动化处理，使其符合游戏引擎规范。

---

## 主要挑战

| 挑战 | 说明 |
|------|------|
| 几何质量 | 生成模型面数过高/拓扑不规范，需重拓扑 |
| LOD 生成 | 自动生成多级 LOD，保持视觉一致性 |
| 碰撞体 | 自动生成简化碰撞几何体 |
| 材质标准化 | 将生成贴图转为 PBR 标准（BaseColor/Normal/Roughness/Metallic）|
| 命名规范 | 自动重命名骨骼/材质/贴图，符合项目规范 |
| 动画重定向 | 不同骨架之间的动画迁移 |

---

## 学习路径

1. 掌握游戏资产规范（三角形预算、UV 展开、PBR 材质标准）
2. 学习自动重拓扑工具（Instant Meshes, QuadriFlow, ZRemesher API）
3. 研究法线贴图烘焙自动化（xNormal, Marmoset Toolbag API, Blender Python）
4. 了解骨骼动画重定向原理（Unreal IK Retargeter, Unity Avatar）
5. 设计资产验证 Pipeline（几何检查 + 材质检查 + 命名检查）

---

## 关键工具

- **重拓扑**: Instant Meshes, ZRemesher, QuadriFlow
- **LOD**: Unreal AutoLOD, Unity LOD Group, Simplygon
- **材质转换**: Substance Automation Toolkit, xNormal
- **流水线**: Python + Blender API, Houdini PDG, USD Pipeline
- **验证**: 自定义资产检查器（Linter）

---

## 关键论文

- [Neural Mesh Simplification](https://arxiv.org/abs/2107.01325)
- [Instant3D + Mesh Post-processing]
- [DiffusionRig](https://arxiv.org/abs/2304.06711) — 扩散模型辅助骨骼绑定

---

## 实验方向

- [ ] Blender Python 脚本：TripoSR 输出 → 自动重拓扑 → LOD → 导出 FBX
- [ ] PBR 贴图生成管线：Diffuse → Normal/Roughness/AO 自动推断
- [ ] 命名规范检查工具（资产 Linter）
