# AI 自动镜头

核心问题：如何让 AI 理解剧情/情绪，自动生成合理的摄影机运动和切换方案。

---

## 目录结构

```
05_ai_auto_camera/
├── README.md                          ← 本文件：技术方向总览
│
├── 01_film_cinematography/            # 电影镜头语言基础（理论根基）
│   ├── 01_theory_framework/
│   │   └── cinematography_framework.md   ← 景别/角度/运动/剪辑完整框架
│   ├── 02_books/
│   │   └── booklist.md                   ← 推荐书单（含中英文）
│   ├── 03_online_courses/
│   │   └── course_list.md                ← 中国大学MOOC / Coursera / MIT OCW
│   └── 04_videos/
│       └── video_resources.md            ← YouTube频道 / B站 / 知乎/机核
│
└── 02_game_camera/                    # 影视镜头语言 → 游戏应用
    ├── 01_theory/
    │   └── film_to_game_mapping.md       ← 电影→游戏映射表 + 案例分析
    ├── 02_gdc_siggraph/               ← （待补充）GDC/SIGGRAPH/I3D/SCA论文
    ├── 03_engine_tutorials/           ← （待补充）Unreal Sequencer / Unity Cinemachine
    ├── 04_open_source/                ← （待补充）GitHub开源项目
    └── 05_ai_camera/                  ← （待补充）AI自动镜头研究方向
```

---

## 技术层次

### 第一层：电影镜头语言基础（先学）
> 参见 `01_film_cinematography/`

- 景别（Shot Size）：远景→特写的情感意义
- 镜头角度（Camera Angle）：仰/俯/平/荷兰角
- 镜头运动（Camera Movement）：推/拉/移/升/手持/变焦
- 剪辑语法（Editing）：匹配剪辑/对切/插入镜头/180°法则
- 场面调度（Mise-en-Scène）：构图/光线/色彩/演员走位

### 第二层：电影→游戏映射（核心转化）
> 参见 `02_game_camera/01_theory/film_to_game_mapping.md`

- 控制权动态分配：玩家控制 ↔ 系统接管
- 景别/运动/剪辑在游戏中的实现方式
- 大世界游戏的状态机驱动镜头框架
- 情感驱动镜头系统设计

### 第三层：顶会学术研究
> 参见 `02_game_camera/02_gdc_siggraph/`（待补充）

- **GDC** 演讲：50 Camera Mistakes / Scroll Back / Tomb Raider Camera
- **SIGGRAPH**：Virtual Cinematographer (1996) / Example-driven Cinematography (2020)
- **SCA/MIG**：实时自动电影摄影系统、镜头路径规划

### 第四层：AI 自动镜头（研究前沿）
> 参见 `02_game_camera/05_ai_camera/`（待补充）

- LLM 解析剧情脚本 → 情绪标签 → 镜头规则
- 基于 Transformer 的镜头序列生成
- 强化学习优化镜头美感（奖励：构图质量、跟随流畅度）
- **Cine-AI**（开源）：Unity 中仿真真实导演风格的自动过场动画
- Diffusion 生成关键帧摄影机曲线

---

## 关键论文（已检索）

| 论文 | 会议 | 内容 |
|------|------|------|
| Virtual Cinematographer | SIGGRAPH 1996 | 用电影惯用法自动生成摄像机规格 ⭐ |
| Example-driven Cinematography | SIGGRAPH 2020 | 从真实电影片段学习摄像机行为 |
| Camera Keyframing with Style | SIGGRAPH Asia 2021 | 风格化摄像机关键帧合成 |
| A Real-time Cinematography System | SCA 2010 | 实时自动电影摄影系统 |
| Narrative-Driven Camera Control | MIG 2014 | 叙事重要性驱动的游戏回放摄像机 |
| Camera-on-rails | MIG 2015 | 自动生成虚拟摄像机轨道 |
| 50 Game Camera Mistakes | GDC 2014 | 摄像机设计常见错误 + 电影构图原则 |
| Scroll Back | GDC 2015 | 横版卷轴游戏摄像机全面回顾 |
| Cine-AI (CHI PLAY 2022) | CHI PLAY | Unity开源导演风格仿真工具 ⭐ |

---

## 关键开源项目

| 项目 | 平台 | Stars | 说明 |
|------|------|-------|------|
| [Cine-AI](https://github.com/inanevin/Cine-AI) | Unity (C#) | 51 | 模仿真实导演风格的过场动画生成工具，CHI PLAY 2022 论文配套 |
| [Unity Cinemachine](https://github.com/needle-mirror/com.unity.cinemachine) | Unity | 官方 | 智能程序化摄像机套件，从游戏到过场动画全覆盖 |
| [Generate-Camera-Trajectory](https://github.com/mbkizil/Generate-Camera-Trajectory) | Python | — | 基于CVPR'26论文，LLM驱动的摄像机轨迹生成工具包 |
| [andreasbaumde/UnityCinematicControl](https://github.com/andreasbaumde/UnityCinematicControl) | Unity | 9 | 直觉化的Unity电影摄像机运动控制脚本 |

---

## 引擎工具链

- **Unity**: Cinemachine 3（Virtual Camera / FreeLook / Dolly Track / Brain）+ Timeline
- **Unreal**: Cine Camera Actor + Sequencer + Camera Cut Track + Take Recorder
- **中文官方文档**:
  - UE5 摄像机动画：https://docs.unrealengine.com/5.0/zh-CN/how-to-animate-cinematic-cameras-in-unreal-engine
  - UE5 镜头切换轨道：https://docs.unrealengine.com/5.2/zh-CN/cinematic-camera-cut-track-in-unreal-engine

---

## 实验方向

- [ ] **入门**：用 Unity Cinemachine + Timeline 制作一段带对话的过场动画
- [ ] **理论验证**：实现情绪标签 → 镜头模板自动选择（状态机驱动）
- [ ] **Cine-AI 复现**：跑通开源项目，测试不同导演风格效果
- [ ] **LLM 驱动**：剧情脚本 → GPT-4 提取情绪/事件 → 输出镜头 JSON → Unreal Sequencer 执行
- [ ] **强化学习**：设计构图美感奖励函数，训练镜头调度 Agent

---

## 学习路径（建议顺序）

```
Week 1  电影理论
  → 读 cinematography_framework.md（1小时）
  → 看 Every Frame a Painting 5集（2小时）
  → 读《大师镜头》第1章 或 《电影镜头设计》第1-3章

Week 2  游戏映射理解
  → 读 film_to_game_mapping.md
  → 看 GDC "50 Camera Mistakes"（YouTube免费）
  → 看 GDC "Scroll Back"（GDC Vault免费）
  → 玩《战神2018》并观察一镜到底的镜头逻辑

Week 3  引擎实操
  → Unity Cinemachine 官方示例场景走读
  → 做一个带3种景别切换的对话过场

Week 4  学术研究
  → 读 Virtual Cinematographer (SIGGRAPH 1996)
  → 读 Cine-AI 论文 + 跑通开源代码

Week 5+  AI方向
  → LLM + 镜头规则实验
  → 探索 Generate-Camera-Trajectory 工具包
```
