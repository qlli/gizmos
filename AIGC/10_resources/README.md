# 通用资源

## 必读论文集合（持续更新）

### 基础模型
- Attention Is All You Need (Transformer)
- DDPM / DDIM (扩散模型基础)
- ViT (Vision Transformer)
- CLIP (多模态对齐)
- LLaMA / Qwen / DeepSeek 技术报告

### 图像生成
- Stable Diffusion (LDM)
- ControlNet
- IP-Adapter
- Flux.1 技术报告

### 3D 生成
- NeRF
- 3D Gaussian Splatting
- Zero-1-to-3
- InstantMesh

### 视频/动画
- AnimateDiff
- CogVideoX
- MDM (Motion Diffusion)

---

## 学习资源导航

| 资源 | 链接类型 |
|------|---------|
| Hugging Face Papers | 每日论文速览 |
| Arxiv Sanity | 论文检索 |
| Papers With Code | 代码复现 |
| Siggraph 论文集 | 图形学顶会 |
| GDC Vault | 游戏开发者大会 |
| Two Minute Papers | 论文速读视频 |

---

## 工具环境配置

### Python 环境建议
```bash
# 推荐使用 conda 管理
conda create -n aigc python=3.10
conda activate aigc

# 深度学习基础
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 常用库
pip install diffusers transformers accelerate
pip install langchain langgraph
pip install open3d trimesh
```

### 常用模型下载
- Hugging Face Hub: `huggingface-cli download`
- 模型缓存路径配置: `HF_HOME` 环境变量

---

## 硬件资源参考

| 任务 | 最低显存 | 推荐显存 |
|------|---------|---------|
| SD 图像生成 | 6GB | 12GB+ |
| SDXL | 8GB | 16GB+ |
| 3D 生成（TripoSR）| 6GB | 16GB+ |
| LLM 推理（7B）| 8GB | 16GB+ |
| 模型微调（LoRA）| 8GB | 24GB+ |

---

## 重要社区与博客

- Hugging Face Blog
- Stability AI Blog
- Meta AI Research
- Google DeepMind Blog
- 游戏方向: Activision Research, Electronic Arts Tech Blog, Epic Games Dev Community
