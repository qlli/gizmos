# 09 · 资料清单：GDC 演讲、论文、书籍、开源项目

> 汇总 00–08 引用的全部资料，按专题分组。★ 为推荐优先阅读。
> 说明：GDC Vault 部分视频需订阅，标注"免费"的可直接观看；中文笔记链接便于快速了解。

---

## 0. 推荐阅读路径

```mermaid
flowchart LR
    A[入门：理解"增效"<br/>★ BotW Change and Constant<br/>★ L4D Booth GDC 2009] --> B[镜头主线<br/>★ 50 Camera Mistakes<br/>★ 战神 GDC 2019<br/>★ Real-Time Cameras]
    B --> C[学术前沿<br/>Toric Space → Example-driven<br/>→ LensCraft → DirCast]
    A --> D[世界与角色<br/>秦都 PCG · 蜘蛛侠<br/>Nemesis · Generative Agents]
    D --> E[行业现状<br/>GDC 2026 AI-Native Games<br/>和平精英 AI 队友]
```

---

## 1. 镜头与电影化（→ 01）

| 类型 | 资料 | 要点 | 链接 |
|------|------|------|------|
| GDC 2014 ★ | John Nesky, *50 Camera Mistakes* | 第三人称镜头设计的"避坑指南" | https://gdcvault.com/play/1021262/50-Camera |
| GDC 2019 ★ | Dori Arazi / Erica Pinto（Santa Monica Studio），战神 no-cut 镜头 | 一镜到底的情感目标与过场管线 | https://sms.playstation.com/stories/our-gdc-2019-presentations-engagement/media/1 |
| GDC 2021 | Park Hamilton, *Exploration in Ghost of Tsushima: Letting the Island Guide You* | 风之引导、weenie 地标 | 中文笔记：https://www.gcores.com/articles/168695 |
| 书 ★ | Mark Haigh-Hutchinson, *Real-Time Cameras* | 游戏镜头唯一专著 | — |
| 书 | Joseph Mascelli, *The Five C's of Cinematography* | 电影摄影基础语法 | — |
| 论文 | Lino & Christie, *Intuitive and Efficient Camera Control with the Toric Space*（SIGGRAPH 2015） | 以构图为中心的镜头参数化 | https://inria.hal.science/hal-01142876v3 |
| 论文 ★ | Jiang et al., *Example-driven Virtual Cinematography by Learning Camera Behaviors*（SIGGRAPH 2020） | 从电影片段学习镜头行为 | https://inria.hal.science/hal-03141673 |
| 论文 | LensCraft（2025） | 规则 / 优化 / 学习三种范式综述 + 数据集 | https://arxiv.org/abs/2506.00988 |
| 论文 | CCD / CameraCtrl（2024）、E.T. 数据集（2025）、DirCast（2026） | 扩散模型生成镜头、流式 VLM 导播 | 见 arXiv |

## 2. 建筑学、城市规划与 PCG（→ 02）

| 类型 | 资料 | 要点 | 链接 |
|------|------|------|------|
| GDC 2025 ★ | 腾讯，秦朝古都 PCG | 闾里制、建筑语法、Roof Logic、云端 Houdini | https://news.qq.com/rain/a/20250519A09QXB00 |
| GDC | Insomniac, *Procedurally Crafting Manhattan for Marvel's Spider-Man* | 以玩法为核心的城市生成 | 中文翻译：https://blog.csdn.net/u013412391/article/details/115217431 |
| GDC | *Building Blocks: Artist Driven Procedural Buildings* | 美术驱动的程序化建筑 | https://www.gdcvault.com/play/1012655 |
| GDC 2021 | thatgamecompany（Nicolas Oueijan），认知地图 | Tolman → Lynch → 关卡设计 | 中文：https://igdshare.org/node/3017 |
| 文章 | *How Townscaper Works* | 不规则网格 + WFC | http://gamasutra.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making |
| 开源 ★ | Maxim Gumin, WaveFunctionCollapse | WFC 原始实现 | https://github.com/mxgmn/WaveFunctionCollapse |
| 文章 | Boris the Brave, *WFC Tips and Tricks* | WFC 工程技巧 | https://www.boristhebrave.com/2020/02/08/wave-function-collapse-tips-and-tricks/ |
| 论文 | Biggs et al., *Supporting Wayfinding through Patterns within Procedurally Generated Virtual Environments* | Alexander + Lynch 用于 PCG | http://dwig.lmc.gatech.edu/download/Biggs_SupportingWayfinding_08.pdf |
| 书 ★ | Christopher Totten, *An Architectural Approach to Level Design* | 建筑学视角的关卡设计 | — |
| 书 | Kevin Lynch, *The Image of the City* | 城市意象五要素 | — |
| 书 | Christopher Alexander, *A Pattern Language* | 253 个建筑模式 | — |
| GDC 2009 | Scott Rogers, *Everything I Learned About Level Design I Learned from Disneyland* | 主题公园手法 | — |
| GDC 2010 | Harvey Smith & Matthias Worch, *What Happened Here? Environmental Storytelling* | 环境叙事 | — |

## 3. 短视频、网络文化与世界模型（→ 03）

| 类型 | 资料 | 链接 |
|------|------|------|
| 案例 | 《8 号出口》销量与改编 | https://labs.invenglobal.com/articles/25663 |
| 案例 | Fortnite Renegade 表情署名争议 | https://screenrant.com/fortnite-renegade-tiktok-dance-emote-creator-credit-jalaiah/ |
| 报道 | 游戏"短剧化"（新华财经，2025-03） | https://m.cnfin.com/wx/share?url=//m.cnfin.com/gs-lb//zixun/20250319/4202593_1.html |
| 报道 | AI 互动影游行业综述（腾讯新闻，2026-04） | https://view.inews.qq.com/a/20260408A07UCH00 |
| 论文 | GameNGen（ICLR 2025）；Muse / WHAM（Nature 2025） | arXiv / Nature |
| 开源 ★ | Hunyuan-GameCraft | https://github.com/Tencent-Hunyuan/Hunyuan-GameCraft-1.0 |
| 开源 ★ | HY-World 1.5 / WorldPlay | https://github.com/Tencent-Hunyuan/HY-WorldPlay |
| 调研 | 世界模型调研 2024–2026 | https://huggingface.co/Oratis/world-model-research |

## 4. 活的角色（→ 04）

| 类型 | 资料 | 链接 |
|------|------|------|
| 论文 ★ | Park et al., *Generative Agents: Interactive Simulacra of Human Behavior*（UIST 2023） | arXiv 2304.03442 |
| 文章 ★ | *Designing Shadow of Mordor's Nemesis System* | https://www.gamedeveloper.com/design/designing-i-shadow-of-mordor-i-s-nemesis-system |
| 文章 | 体育式叙事框架（GameLook） | http://www.gamelook.com.cn?p=458424/ |
| GDC 2025 | Dead Meat：端侧 SLM + 导演笔记（NVIDIA ACE） | http://www.invisiblefriends.net/gdc-2025/ |
| GDC 2026 ★ | State of AI-Native Games 等回顾 | https://lanternworks.dev/lab-notes/gdc-2026-recap |
| GDC 2026 | 和平精英 AI 队友（中文报道） | https://view.inews.qq.com/a/20260314A07SPA00 |

## 5. AI 导演与节奏（→ 05）

| 类型 | 资料 | 链接 |
|------|------|------|
| GDC 2009 ★ | Michael Booth, *From Counter-Strike to Left 4 Dead: Creating Replayable Cooperative Experiences*（免费） | GDC Vault |
| AIIDE 2009 ★ | Michael Booth, *The AI Systems of Left 4 Dead* | https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf |
| 论文 | Hunicke, *The Case for Dynamic Difficulty Adjustment in Games*（2005） | — |
| 论文 | Mateas & Stern, *Façade*（2003/2005） | — |
| 论文 | Chen et al., *EOMM*（WWW 2017，伦理参考） | https://arxiv.org/abs/1702.06820 |
| 文章 | Tommy Thompson, Alien: Isolation AI 分析 | AI and Games |
| 资料 | RimWorld AI Storytellers | https://rimworldwiki.com/wiki/AI_Storytellers |

## 6. 系统化世界与 AI 动作（→ 06）

| 类型 | 资料 | 链接 |
|------|------|------|
| GDC 2017 ★ | *Change and Constant: Breaking Conventions with The Legend of Zelda: Breath of the Wild* | https://gdcvault.com/play/1024562/ ｜ https://www.youtube.com/watch?v=QyMsF31NdNc |
| GDC 2016 ★ | Simon Clavet, *Motion Matching and The Road to Next-Gen Animation* | GDC Vault |
| GDC 2016 | Kristjan Zadziuk, *Motion Matching: The Future of Games Animation… Today* | GDC Vault |
| 论文 ★ | Holden et al., *Learned Motion Matching*（SIGGRAPH 2020） | https://www.theorangeduck.com/page/learned-motion-matching |
| 论文 | DeepMimic（2018）、AMP（2021）、MaskedMimic（2024） | arXiv |
| 示例 | Epic, Game Animation Sample Project（UE 5.4+） | Fab / Epic Launcher |
| 作品 | Infinite Craft（LLM 作为合成规则引擎） | https://neal.fun/infinite-craft/ |

## 7. 声音、触觉与心理（→ 07）

| 类型 | 资料 | 链接 |
|------|------|------|
| GDC 2011 ★ | Mike Ambinder, *Biofeedback in Gameplay*（免费） | GDC Vault |
| GDC 2017 | Mick Gordon, *DOOM: Behind the Music* | GDC Vault |
| GDC 2025 | Team Asobi（Masayuki Yamada），Astro Bot 触觉设计 | GDC Vault |
| 纪录片 ★ | Ninja Theory, *Hellblade: Senua's Psychosis* | 官方 YouTube |
| 书 | Karen Collins, *Game Sound*（MIT Press） | — |
| 书 | Winifred Phillips, *A Composer's Guide to Game Music*（MIT Press） | — |

## 8. 方法论与综合（→ 00、08、10）

| 类型 | 资料 | 要点 |
|------|------|------|
| 书 ★ | Jesse Schell, *The Art of Game Design: A Book of Lenses* | 100+ 个设计"透镜"，跨领域思考的工具箱 |
| 书 | Tynan Sylvester, *Designing Games* | 体验引擎、涌现（RimWorld 作者） |
| 书 | Mihaly Csikszentmihalyi, *Flow* | 心流理论 |
| 书 | Steve Swink, *Game Feel* | 手感 / 打击感的系统化分析 |
| 书 | Keith Johnstone, *Impro* | 即兴戏剧、地位理论 |
| 报告 | GDC 2026 AI 议题（100+ 场，腾讯 21 场）回顾 | GameLook / 腾讯新闻 |

---

## 9. 持续跟踪渠道

| 渠道 | 内容 |
|------|------|
| GDC Vault（含免费区） | 每年 3 月 GDC 演讲 |
| SIGGRAPH / SIGGRAPH Asia、Eurographics | 动作、镜头、渲染论文 |
| AIIDE、IEEE CoG、FDG | 游戏 AI、PCG、交互叙事学术会议 |
| arXiv cs.GR / cs.CV / cs.AI | 世界模型、镜头生成、Agent |
| AI and Games（Tommy Thompson） | 游戏 AI 案例深度分析 |
| GameLook、机核、游戏葡萄、IGDShare | 中文 GDC 笔记与行业报道 |
| 腾讯游戏学堂 / GWB | 腾讯内部与公开技术分享 |
