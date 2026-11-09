# PicVote

个人自用的图片抓取 / 浏览服务：抓取网页图片 → 本地文件存储 → 网页按抓取时间分页浏览 → `oo` / `xx` 点赞反对 → 每日凌晨清理汰换。

**独立工程**：与 `HelpApp` 无依赖、无引用。Python 3.6+ 标准库（兼容 CentOS 7 自带的 3.6.8），**零第三方依赖**，单进程，无数据库、无缩略图、无缓存服务，适配内存与硬盘有限的小服务器。

设计依据：`d:/UGit/gizmos/HelpApp/doc/design/20261108-图片抓取标注展示独立服务-结论.md`（状态「已确认」）。

> **已部署**：`root@101.200.200.199`，目录 `/opt/picvote`，systemd 服务 `picvote`，端口 `18080`，公网地址 `http://101.200.200.199:18080/`。该机器上另有 HelpApp 现网（80 / 8080 端口），本服务使用独立端口与独立目录，不与其共用配置。

---

## 1. 快速开始（本地）

```bash
cd d:/UGit/gizmos/PicVote
cp sources.example.txt sources.txt      # 按下面的格式填写来源
python app.py --job-now                 # 立即跑一次「清理 → 抓取 → 汰换」
python app.py                          # 启动网页 + 凌晨定时任务
# 浏览器打开 http://127.0.0.1:18080/
python app.py --status                 # 查看配额与索引状态
python -m unittest discover -s tests -v  # 自检（19 项）
```

Windows 上把 `cp` 换成 `copy`。首次不配 `sources.txt` 也能启动，只是不会抓新图。

---

## 2. 来源清单 `sources.txt`

每行一条：`<分类>|<类型>|<值>`，`#` 开头为注释。

| 分类 | 含义 |
|---|---|
| `beauty` | 美女 |
| `handsome` | 帅哥 |

| 类型 | 说明 |
|---|---|
| `page` | 普通 HTML 页面，抽取页面里的 `<img>`（遵守 robots.txt、限速） |
| `image` | 单张图片直链 |
| `dir` | 本地目录，导入你自己的图片，完全离线 |
| `jandan` | 煎蛋栏目专用适配器，解析公开列表接口、过滤装饰图 |

```
beauty|page|https://example.com/some/gallery
handsome|image|https://example.com/photo.jpg
beauty|dir|./my-images
beauty|jandan|https://jandan.net/beauty
```

分类由清单显式标注，程序**不做图像识别分类**（内存有限、按简单设计）。

### 抓取适配层的边界

`fetcher` 是通用、守规矩的实现：遵守 `robots.txt`、可识别 UA、单线程限速、校验图片文件头与 `Content-Type`、限制单张大小、跳过已抓过的 URL。来源接口 `Source.iter_images()` 可插拔。

`JandanSource` 是站点专用适配器：从公开 HTML 读栏目 `PAGE.id`、GET 该站公开列表接口、递归提取返回数据里的图片地址、过滤 `/static/tg/` 等装饰图。实测该站内容接口要求登录态（`code=1000`），因此支持读取用户本人配置的 Cookie，见第 2.1 节。

**仍未实现**：提交用户名密码自动登录、换取 / 刷新 token、接口签名伪造、风控 / 验证码绕过、JS 渲染反检测、UA / 代理轮换；除 `jandan` 外，不包含知乎 / 小红书 / 抖音 / 微博的站点专用爬虫。实测这些平台多数内容在登录墙后且 robots 禁止抓取。绕过反爬属于手段层面的红线，与用途无关。

### 2.1 登录态凭证（可选，用户本人配置）

内容接口需要登录态。凭证由**你本人**在服务器上写入，程序只读取、只按域附加请求头：

**最省事的做法**：在服务器上运行一次导入工具，粘贴浏览器里复制的内容即可，不用手工拼字符串：

```bash
cd /opt/picvote && python3 import_cookie.py
```

它支持 4 种粘贴格式，任选其一，粘贴后回车、再按一次空回车结束：

1. DevTools → Network → 选 `jandan.net` 的请求 → Headers → Request Headers 里的 `cookie:` 整行
2. 右键该请求 → Copy → Copy as cURL 的整条命令
3. Cookie-Editor → Export → JSON（底部工具栏最右侧图标，无文字标签，悬停显示 tooltip）
4. 纯 `name=value; name2=value2` 串

工具只在本机写入 `secrets/credentials.json`（600），**内容不打印、不回传、不落日志**，并顺带校验 `state` 与 `is_template`。

也可以手工编辑（目录 700 / 文件 600）：

```bash
mkdir -p /opt/picvote/secrets && chmod 700 /opt/picvote/secrets
cp /opt/picvote/secrets.example.json /opt/picvote/secrets/credentials.json
chmod 600 /opt/picvote/secrets/credentials.json
vi /opt/picvote/secrets/credentials.json
```

格式（键为域名，值为原样附加的请求头）：

```json
{
  "jandan.net": {
    "Cookie": "<你本人浏览器里该站的 Cookie 串>"
  }
}
```

- 凭证**只发给声明域名**，不会发给图床或其他站点。
- 不进仓库（`secrets/` 已忽略）、不落日志、不出现在索引 / API / 异常信息里；程序只记录「未配置 / 已加载 / 已失效」三态。
- 权限非 600（POSIX）或 JSON 非法时，凭证会被忽略并告警。
- **不需要每天手工提供**：凭证带 `expireTime`，配一次可连续用多天。到期、改密码、异地登录、风控重登后需重新提供一次。
- **失效会显式告警**：`/api/status` 的 `credentials.state` 变为 `expired`、`auth_error` 有值，网页顶部显示红色提示，凌晨任务不再静默空跑。
- 该站前端未发现自动续期逻辑，所以没有实现 token 刷新。

---

## 3. 行为规则

| 项 | 规则 |
|---|---|
| 存储 | `data/images/00000001.png` 原始字节；`data/index.json` 单文件索引（原子写回）；`data/picvote.log` 日志 |
| 配额 | 10 GiB（`10*1024^3`），只统计图片字节。落盘前预判 `已用 + 本张 > 上限` 即丢弃并停止本轮，保证不超过 10G |
| 排序 | 按 `id` 升序，即抓取时间顺序；`id` 同时是文件名与「最旧」判据 |
| 展示 | 美女 / 帅哥两个标签页；每页 20 张；纵向单列自然上下排列 |
| 投票 | `oo` / `xx`；无账号、无防刷。点已选按钮取消为无票，点另一按钮改票。`xx` 只是标记，**不代表删除** |
| 清理 | 每天凌晨（默认 03:00）删除 `ceil(当前张数 * 10%)` 张最旧图片，**`oo` 图片永不删除**；非 oo 不足 10% 时删到无可删 |
| 汰换 | 清理后立即抓取补足，直到再次达到 10 GiB 或来源耗尽 |
| 当天停止 | `last_job_date` 保证同一天只跑一次；达到 10G 当天停止，次日凌晨恢复清理 / 抓取 / 汰换 |
| 终态 | 剩余图片全部为 `oo` 且配额已满 → `frozen = true`，此后**不再抓取、清理、汰换**，任何任务直接返回 |
| 并发 | 按简单设计不处理；凌晨任务与白天浏览天然错开，分页用简单 offset |

> 终态那条有个关键取舍：若「全是 oo」时仍继续抓新图，新图默认无票，会永远无法达到「最后 10G 全是点赞图片」。因此全 oo 时不再补抓新图。

---

## 4. 配置项

全部通过环境变量覆盖（或直接改 `config.py` 默认值）。

| 变量 | 默认 | 说明 |
|---|---|---|
| `PICVOTE_ROOT` | 工程目录 | 数据与索引根目录 |
| `PICVOTE_QUOTA_BYTES` | `10737418240` | 配额字节数 |
| `PICVOTE_PAGE_SIZE` | `20` | 每页张数 |
| `PICVOTE_CLEANUP_RATIO` | `0.10` | 每日清理比例 |
| `PICVOTE_JOB_HOUR` | `3` | 凌晨任务小时 |
| `PICVOTE_HOST` | `0.0.0.0` | 监听地址 |
| `PICVOTE_PORT` | `18080` | 端口（避开现网 80 / 8080） |
| `PICVOTE_ACCESS_TOKEN` | 空 | 非空时所有页面与接口需带 `?token=` 或 `Authorization: Bearer` |
| `PICVOTE_REQUEST_INTERVAL` | `1.0` | 每次请求最小间隔秒数 |
| `PICVOTE_TIMEOUT` | `10.0` | 单次请求超时秒数 |
| `PICVOTE_MAX_IMAGE_BYTES` | `8388608` | 单张图片大小上限 |
| `PICVOTE_JANDAN_MAX_PAGES` | `20` | 每条 `jandan` 来源最多翻几页 |

### 访问范围（建议收紧）

默认按你的要求为**公网匿名访问**（`0.0.0.0` + 无口令）。但匿名公网端口并不等于「只有我自己访问」：扫描器、搜索引擎、同网段其他人都可能访问。两个一行式收紧方式：

```bash
# 方案 A：只监听本机，用 SSH 隧道访问（个人自用最稳）
PICVOTE_HOST=127.0.0.1 python app.py
ssh -L 18080:127.0.0.1:18080 root@101.200.200.199

# 方案 B：加简单口令
PICVOTE_ACCESS_TOKEN=自定口令 python app.py
# 浏览器访问 http://101.200.200.199:18080/?token=自定口令
```

---

## 5. 部署到云服务器

已于 2026-11-08 部署到 `root@101.200.200.199`（CentOS 7）。要点：

- 服务器原本只有 Python 2.7；通过 `yum install -y python3` 安装 3.6.8，工程代码已做到 3.6 兼容（不使用 `dataclasses` / f-string / `ThreadingHTTPServer`）。
- `8080` 被现网 `helpapp-api` 占用、`80` 被 nginx 占用，因此本服务使用 **`18080`**，安全组已放行。
- 复用服务器已有的免密 SSH 通道；未使用、也未存储任何明文口令。
- 独立 systemd 服务 `picvote`，开机自启；未修改 nginx / HelpApp 任何配置，现网 `/healthz` 仍为 200。

重新部署（代码改动后）：

```bash
# 本机（PowerShell）
cd d:/UGit/gizmos/PicVote
tar -czf picvote-deploy.tar.gz --exclude='__pycache__' \
    app.py config.py storage.py sources.py job.py web.py \
    README.md requirements.txt sources.example.txt deploy tests
scp picvote-deploy.tar.gz root@101.200.200.199:/tmp/

# 服务器
ssh root@101.200.200.199
cd /opt/picvote && tar -xzf /tmp/picvote-deploy.tar.gz && rm -f /tmp/picvote-deploy.tar.gz
python3 -m unittest discover -s tests        # 服务器自检
PORT=18080 HOST=0.0.0.0 bash deploy/install.sh
```

`install.sh` 会保留已有 `data/` 与 `sources.txt`，只更新代码与 unit，然后重启服务并做本机健康检查。常用运维：

```bash
systemctl status picvote
systemctl restart picvote
journalctl -u picvote -f
tail -f /opt/picvote/data/picvote.log
python3 /opt/picvote/app.py --job-now   # 手动跑一次任务
python3 /opt/picvote/app.py --status
```

若改端口，需在云厂商安全组同步放行；用域名则还需 ICP 备案。

---

## 6. 合规提醒（一次性）

你已明确「先不考虑授权」，工程按此执行。仍需如实记录两点事实：

- 「公网匿名访问」= 向不特定公众提供，个人 / 家庭事务豁免与「必要范围内个人使用已公开肖像 / 作品」的合理使用空间，通常以不公开传播为前提；公开站点还可能触发备案与内容审核义务。
- 抓取真人肖像并公开展示、点赞反对，涉及肖像权、个人信息与作品著作权；平台用户协议与 robots 普遍限制批量抓取。

这些由你自行判断，工程侧不代作决定，也不实现任何绕过手段。

---

## 7. 文件结构

```
app.py          入口（网页服务 + 凌晨定时线程 + CLI）
config.py       全部配置
storage.py      单文件 JSON 索引、图片落盘、配额、投票、分页
sources.py      可插拔抓取适配层（robots / 限速 / 图片头校验）
job.py          每日任务状态机
web.py          HTTP 接口 + 单页前端
tests/          单元与 HTTP 自检
deploy/         systemd unit + 安装脚本
sources.example.txt  来源清单模板
```
