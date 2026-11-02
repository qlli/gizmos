# AI 辅助游戏开发 — 学习与工程实验工程

> 深耕方向：AI 提效 · AIGC 资产 · PCG+AI 场景 · AI 自动测试 · AI Coding · AI 渲染参数
> 新增路线：**AI 增效**——借助 AI 把电影、建筑、转播、心理学等专业知识变成实时交互体验（见 `11_experience_innovation/`）

---

## 目录结构

```
AIGC/
├── 00_overview/            # 整体规划、路线图、方法论沉淀
├── 01_aigc_assets/         # AIGC 游戏资产工程化
│   ├── 01_concept_art/     # AI 生成原画
│   ├── 02_3d_model/        # AI 生成/重建三维模型
│   ├── 03_character_animation/ # AI 角色动画生成
│   ├── 04_rigging/         # AI 自动绑定
│   ├── 05_texture_enhancement/ # 贴图细节增强
│   └── 06_cinematic_animation/ # AI 剧情动画
├── 02_ai_coding/           # AI Coding 工程化
│   ├── 01_code_generation/
│   ├── 02_test_assistance/
│   ├── 03_code_review/
│   └── 04_dev_collaboration/
├── 03_pcg_scene_generation/ # PCG + AI 场景生成
├── 04_ai_auto_testing/     # AI 自动测试
│   ├── 01_gameplay_testing/
│   ├── 02_visual_testing/
│   └── 03_bug_detection/
├── 05_ai_auto_camera/      # AI 自动镜头
├── 06_asset_pipeline_adaptation/ # AIGC 资产自动适配游戏管线
├── 07_ai_rendering_params/ # AI 自动生成渲染/布料/灯光参数
│   ├── 01_render_params/
│   ├── 02_cloth_params/
│   └── 03_auto_lighting/
├── 08_ai_agent_workflow/   # AI Agent / 自动化工作流
├── 09_experiments/         # 工程实验记录
├── 10_resources/           # 通用学习资料、论文、工具链
└── 11_experience_innovation/ # AI 驱动的游戏效果与体验创新（增效路线）
    ├── 00_methodology.md         # 专业知识 → 可计算规则 → 交互体验 五步框架
    ├── 01_cinematic_camera.md    # 电影运镜迁移
    ├── 02_architecture_urban_pcg.md # 建筑学/城市规划 → PCG
    ├── 03_short_video_world_model.md # 短视频游戏化 / 世界模型
    ├── 04_living_characters.md   # 活的角色 / AI 队友
    ├── 05_ai_director_pacing.md  # AI 体验导演 / 节奏
    ├── 06_systemic_world_motion.md # 系统化世界 / AI 动作
    ├── 07_senses_audio_haptics.md # 声音、触觉、心理
    ├── 08_cross_domain_catalog.md # 28 个可迁移的专业领域
    ├── 09_gdc_reading_list.md    # GDC / 论文 / 书籍清单
    └── 10_opportunity_matrix.md  # 机会矩阵与落地建议
```

---

## 快速导航

| 方向 | 核心文档 |
|------|---------|
| 整体路线图 | [00_overview/roadmap.md](00_overview/roadmap.md) |
| AIGC 资产 | [01_aigc_assets/README.md](01_aigc_assets/README.md) |
| AI Coding | [02_ai_coding/README.md](02_ai_coding/README.md) |
| PCG+AI 场景 | [03_pcg_scene_generation/README.md](03_pcg_scene_generation/README.md) |
| AI 自动测试 | [04_ai_auto_testing/README.md](04_ai_auto_testing/README.md) |
| AI 镜头 | [05_ai_auto_camera/README.md](05_ai_auto_camera/README.md) |
| 资产管线适配 | [06_asset_pipeline_adaptation/README.md](06_asset_pipeline_adaptation/README.md) |
| AI 渲染参数 | [07_ai_rendering_params/README.md](07_ai_rendering_params/README.md) |
| Agent 工作流 | [08_ai_agent_workflow/README.md](08_ai_agent_workflow/README.md) |
| **体验创新（增效）** | [11_experience_innovation/README.md](11_experience_innovation/README.md) |

---

## 使用方式

- 每个方向下有独立 `README.md`（学习路径 + 关键论文 + 工具链）
- `notes/` 子目录记录阶段性学习笔记
- `experiments/` 子目录放工程实验代码和结果
- 遇到重要判断或技术选型时，更新 `00_overview/decisions.md`
