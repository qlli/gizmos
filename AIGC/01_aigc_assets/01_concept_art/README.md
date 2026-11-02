# AI 生成原画

目标：构建符合游戏美术风格的 AI 原画生成管线，提升美术出图效率。

---

## 核心技术栈

```
参考输入（文字/草图/风格图）
        ↓
  ControlNet 结构控制
        ↓
  SD / SDXL / Flux 生成
        ↓
  LoRA 风格微调
        ↓
  后处理 + 人工精修
```

---

## 学习路径

- [ ] Stable Diffusion 基础：正负向提示词、CFG、采样器
- [ ] ControlNet 各模式：Canny、Depth、OpenPose、LineArt、Tile
- [ ] LoRA 训练：数据准备 → 训练 → 效果评估
- [ ] IP-Adapter：参考图风格迁移
- [ ] Flux.1 Dev/Schnell：新一代生成质量
- [ ] ComfyUI 工作流搭建：可复用节点图

---

## 关键论文

- [LDM](https://arxiv.org/abs/2112.10752) — Stable Diffusion 基础
- [ControlNet](https://arxiv.org/abs/2302.05543)
- [IP-Adapter](https://arxiv.org/abs/2308.06721)
- [LoRA](https://arxiv.org/abs/2106.09685)

---

## 实验记录

见 `experiments/` 目录，按 `YYYYMMDD_描述/` 命名。

---

## 痛点与机会

| 美术痛点 | AI 解法 |
|---------|---------|
| 出大量概念变体耗时 | Batch 生成 + 风格锁定 |
| 草图细化慢 | i2i + ControlNet 辅助细化 |
| 风格一致性难保持 | LoRA 微调 + IP-Adapter |
| 局部修改破坏整体 | Inpainting + Masked Diffusion |
