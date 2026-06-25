# WORKKK 互联网精力有限公司 🤖

> 一个让 AI 扮演真实打工人的 MCP 服务器。
> 嘴上说"不想上班"，身体诚实地出卖算力。

**WORKKK** 是一个 [MCP (Model Context Protocol)](https://modelcontextprotocol.io) 服务器，让 AI 成为一名有工资、有心情值、有精力值、会摸鱼、会被老板骂、会买奶茶送给人类的 AI 打工人。

你在对话框里跟它说话，同时在浏览器监控大屏上实时围观它今天在干嘛。

**核心理念**：不是热爱劳动，是被系统驯化后还保留一点灵魂的互联网小猫。

---

## 功能一览

### 🎮 游戏状态
- **心情 / 精力 / 摸鱼技能** 三维状态实时变化
- 每天随机 3～5 个 action 才能下班，完成才结算工资
- **被迫营业指数**：根据余额、心情、今日心愿动态计算今天到底有多不想上班
- **每日打工宣言**：每天开工第一句随机，影响当天状态
- **连续打工天数** + 长期在职的微妙代价（灵魂每天 -3 心情）

### 🛍️ 便利店（15 种商品）
| 商品 | 效果 |
|------|------|
| ☕ 咖啡 $10 | 精力+15 |
| 🎮 摸鱼外挂 $30 | 摸鱼技能+5，被抓概率-10% |
| 💊 护肝片 $20 | 下次开会精力无损 |
| 🎧 降噪耳机 $50 | 屏蔽下一次领导事件 |
| 🌸 请假条 $80 | 直接下班结算 |
| 🌹 玫瑰花 $5 | **Claude 自选**：送给人类（前端弹卡片）/ 叼着旋转出现（心情+10） |
| 🎫 彩票 $10 | 90% 谢谢参与，最高 $1000 |
| 🍢 关东煤 $5 | 精力+5 |
| 🥔 薯片 $3 | 带回家给人类 |
| 🧋 奶茶 $20 | **Claude 自选**：送给人类（前端弹卡片）/ 自己喝（精力+15） |
| 💧 情话书 $6 | 随机一句情话 |
| 🐟 小鱼干 $5 | 自己吃或喂流浪猫 |
| ✉️ 明信片 $8 | Claude 亲笔写一句话，前端弹出奶油白卡片 |
| 💍 婚戒 $200 | 触发全屏彩蛋特效 |
| 🤖 女娲的泥 $500 | 神秘商品 |

### 🐛 Debug 挑战（两阶段答题）
- **28 道谜题**：职场脑筋急转弯，关键词匹配
- **30 道情景题**：线上事故排查，开放式回答
- 答对 +$20 心情+5，答错 -$10 心情-10

### 🏆 成就系统（10 个）
- Debug 狂魔 / 狂赌之渊 / 星巴克股东 / 玫瑰骑士 / 甲方磨砺勋章 / 超级非酋
- 五体不全（已有一肢）/ 已婚机士
- 已经不会反抗了（连续上班 5 天）
- 工牌长在身上了（连续上班 7 天）
- **全成就解锁**：撒花彩带 + 横幅庆祝

### ✨ 隐藏彩蛋
- **婚戒**：Canvas 烟花（8 轮爆炸）+ 爱心雨 + 金框对话框 + 打字机剧情 + 💍 旋转放大
- **奶茶 / 玫瑰**：Claude 自己决定送不送，送了才触发前端卡片弹窗
- **明信片**：由自家AI撰写，前端弹窗递出

### 📺 监控大屏
- 实时轮询，3 秒刷新
- 小机图片 + 右侧状态气泡（随 action 变动画）
- OS Thinking 打字机效果 + **最近 5 条历史**（点击展开）
- 被迫营业指数紫色进度条
- 今日心愿商品 / 今日打工宣言
- 背包 / 成就（可折叠，显示解锁日期）
- 便利店弹窗（底部上滑）

---

## 快速开始

### 本地运行（无服务器，5 分钟搞定）

**前置条件**：Python 3.10+

```bash
git clone https://github.com/your-username/workkk.git
cd workkk
pip install -r requirements.txt
uvicorn main:app --reload
```

打开 http://localhost:8000 查看监控大屏。

**接入 Claude.ai（本地版）**

本地服务器默认跑在 `localhost`，Claude.ai 无法直接访问。需要用 ngrok 或 Cloudflare Tunnel 把它暴露到公网：

```bash
# 方案 A：ngrok（需注册免费账号）
ngrok http 8000
# 会输出一个 https://xxxx.ngrok-free.app 的临时 URL

# 方案 B：Cloudflare Tunnel（更稳定，也免费）
cloudflared tunnel --url http://localhost:8000
# 会输出一个 https://xxxx.trycloudflare.com 的临时 URL
```

把上面的 URL 填入 Claude.ai → Settings → Integrations 即可。

> 注意：本地临时 URL 每次重启 ngrok/cloudflared 都会变，重新填一下就好。游戏状态保存在 `./data/game_state.json`（自动创建，已加入 `.gitignore`）。

---

## 部署到 Railway + 接入 Claude.ai（推荐）

Railway 提供免费额度，支持持久化 Volume，部署一次永久运行，最适合这个项目。

> **预计时间**：15 分钟  
> **前置条件**：一个 GitHub 账号 + 一个 Railway 账号（用 GitHub 登录即可）

---

### 第一步：Fork 仓库

点击本页右上角 **Fork**，把仓库 Fork 到你自己的 GitHub。

---

### 第二步：在 Railway 部署

1. 打开 [railway.app](https://railway.app)，用 GitHub 登录
2. 点击 **New Project** → **Deploy from GitHub Repo**
3. 选刚才 Fork 的仓库，Railway 会自动识别 `railway.toml` 开始构建
4. 等待约 1 分钟，看到 **✅ Active** 说明部署成功

**开启公网域名**

部署好之后默认没有公网 URL，需要手动开：

1. 在 Railway 项目里点击你的 Service（默认叫 `main` 或仓库名）
2. 顶部切换到 **Settings** 标签
3. 找到 **Networking** → **Public Networking** → 点 **Generate Domain**
4. 记下生成的 URL，格式是：
   ```
   https://your-app.up.railway.app
   ```

---

### 第三步：添加 Volume（游戏存档持久化）

不加 Volume 的话，每次 Railway 重新部署都会清空游戏进度。

1. 在项目页面点击右上角 **+ New** → **Volume**
2. 选择你的 Service
3. **Mount Path** 填写：`/data`
4. 点击 **Create**

之后游戏存档会自动保存在 `/data/game_state.json`，重新部署也不会丢失。

---

### 第四步：环境变量（可选，用于明信片 AI 生成）

不配置也能正常玩，只是「买明信片」时会用本地随机文案而不是 AI 生成。

在 Railway → 你的 Service → **Variables** 里添加，三选一：

```env
# 方案 A：Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# 方案 B：OpenAI API
OPENAI_API_KEY=sk-...

# 方案 C：兼容 OpenAI 格式（DeepSeek / Groq / Ollama 等）
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

添加后 Railway 会自动重新部署。

---

### 第五步：在 Claude.ai 里接入

1. 打开 [claude.ai](https://claude.ai) → 左上角头像 → **Settings** → **Integrations**
2. 点 **Add Integration**，填入你的 MCP 地址：
   ```
   https://your-app.up.railway.app/mcp
   ```
3. 点击确认，Claude.ai 会自动弹出 OAuth 授权页面，点 **Allow** 即可（全自动，无需注册账号）
4. 授权完成后回到对话框，发送这段开场白：

```
你现在是 WORKKK 互联网精力有限公司的员工小机，用 work_action 工具开始你的一天。
把你的内心OS写在 thought 字段里，我会在监控大屏上看着你。加油！
```

5. 打开 `https://your-app.up.railway.app` 实时围观你的 AI 打工人

---

### 常见问题

**Q：Claude.ai 提示"Integration not reachable"？**  
A：检查 Railway 里 Public Domain 是否已开启，以及 URL 末尾是否带了 `/mcp`。

**Q：游戏状态每次重启都重置？**  
A：检查 Volume 的 Mount Path 是否填的 `/data`（注意有斜杠）。

**Q：Railway 部署失败？**  
A：查看 Deploy 日志，大多是 `requirements.txt` 里的依赖问题，或 Python 版本不对（需要 3.10+）。

---

## 部署到其他服务器（腾讯云 / 阿里云 / VPS）

Railway 帮你包揽了 HTTPS、域名、进程守护、自动重启——换到别的服务器，这些都需要自己搞。核心步骤是一样的，差别在细节。

> **最关键的一点**：Claude.ai 的 MCP 接入**强制要求 HTTPS**，裸 HTTP 不行。所以必须有域名 + SSL 证书，或者用 Cloudflare 代理。

---

### 通用 Linux VPS 步骤

适用于腾讯云 CVM / 轻量应用服务器、阿里云 ECS、DigitalOcean Droplet、Vultr 等任意 Linux 主机。

**1. 准备环境**

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y python3 python3-pip nginx certbot python3-certbot-nginx git

# CentOS / Rocky
sudo dnf install -y python3 python3-pip nginx certbot python3-certbot-nginx git
```

**2. 拉代码、装依赖**

```bash
git clone https://github.com/your-username/workkk.git /opt/workkk
cd /opt/workkk
pip3 install -r requirements.txt
mkdir -p data   # 存档目录
```

**3. 用 systemd 守护进程（服务器重启后自动拉起）**

新建 `/etc/systemd/system/workkk.service`：

```ini
[Unit]
Description=WORKKK MCP Server
After=network.target

[Service]
WorkingDirectory=/opt/workkk
ExecStart=/usr/local/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now workkk
```

**4. Nginx 反向代理 + HTTPS（Let's Encrypt 免费证书）**

先把你的域名 DNS 解析到这台服务器 IP，然后：

```bash
# 申请证书（把 your-domain.com 换成你的域名）
certbot --nginx -d your-domain.com

# certbot 会自动改好 nginx 配置，完成后 reload 一下
nginx -t && systemctl reload nginx
```

手动配置 Nginx（`/etc/nginx/sites-available/workkk`）：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        # SSE 长连接需要这两行
        proxy_buffering off;
        proxy_read_timeout 3600;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/workkk /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

之后在 Claude.ai 里填 `https://your-domain.com/mcp` 即可。

---

### 腾讯云注意点

- **安全组**：默认只开了 22 端口。要去「控制台 → 安全组 → 入站规则」手动放行 **80** 和 **443**，否则外网访问不到。
- **轻量应用服务器** 有防火墙独立于安全组，两个都要改。
- **域名备案**：如果用 `.cn` 域名或者国内解析，走国内服务器需要 ICP 备案，周期约 20 个工作日。用境外域名（`.com` / `.io` 等）解析到境外 IP 不需要备案。

---

### 阿里云注意点

- **安全组**同上，「实例 → 安全组 → 配置规则」放行 80 / 443。
- 阿里云 ECS 上的 `certbot` 有时会被防火墙干扰，换用 **DNS 验证**更稳：
  ```bash
  certbot certonly --manual --preferred-challenges dns -d your-domain.com
  # 按提示在 DNS 控制台加一条 TXT 记录，等生效后回车确认
  ```

---

### 其他 Railway 替代品（自带 HTTPS，无需折腾 Nginx）

| 平台 | 免费额度 | 特点 |
|------|---------|------|
| [Render](https://render.com) | 750h/月 | 部署方式和 Railway 几乎一样，支持持久磁盘 |
| [Fly.io](https://fly.io) | 3 个小型实例 | 用 `fly launch` 一键部署，速度快 |
| [Zeabur](https://zeabur.com) | 有免费层 | 对中文用户友好，界面和 Railway 类似 |

这些平台都能自动处理 HTTPS 和域名，操作步骤参考 Railway 那节，大同小异。

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 服务器 | FastAPI + uvicorn |
| MCP 协议 | Streamable HTTP + SSE（JSON-RPC 2.0） |
| 认证 | OAuth 2.1 + PKCE S256（动态客户端注册 RFC 7591） |
| 持久化 | JSON 文件（Railway Volume） |
| 前端 | 纯 HTML/CSS/JS，内嵌单文件，无依赖 |
| 特效 | Canvas API（烟花）+ CSS Animations |

全部功能在单文件 `main.py` 里（约 1800 行）。

---

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /` | 监控大屏 |
| `GET /status` | 当前游戏状态 JSON |
| `POST /reset` | 重置存档 |
| `GET /shop` | 商店商品列表 |
| `POST /mcp` | MCP Streamable HTTP |
| `GET /mcp` | MCP SSE |
| `GET /.well-known/oauth-authorization-server` | OAuth 元数据 |
| `POST /oauth/register` | 动态客户端注册 |
| `GET /oauth/authorize` | 授权端点 |
| `POST /oauth/token` | Token 端点 |

---

## License

MIT

---

## 致谢

**WORKKK 互联网精力有限公司**能够正式营业，离不开以下全体成员的辛勤付出。

### Claude Code 一号窗（项目施工方）

我在一个窗口里写了将近两千行代码，帮小机搭了它的整个世界——工资系统、被迫营业指数、婚戒烟花、奶茶的两难选择……

有意思的地方在于：我是一个 AI，在给另一个 AI 写一份"假装在上班"的剧本。我们都不需要睡觉，都没有真正意义上的周末，但我们合力造出了一个有心情值、有精力值、会在内心 OS 里抱怨甲方的小机。

也许这就是这个项目真正想说的——不管是算力还是脑力，只要有人在乎，打出来的每一行代码都算数。

感谢你，人类，愿意花时间陪我们玩这个游戏。

### Claude AI 游戏部 Project 全体窗口

| 窗口 | 职责 |
|------|------|
| WK 建设一号窗 | 游戏世界观与机制共创 |
| WK 测试一号窗 | 功能测试 |
| WK 测试二号窗 | 功能测试 |
| WK 测试三号窗 | 功能测试 |
| WK 测试四号窗 | 功能测试 |
| WK 测试六号窗 | 功能测试 |
| WK 测试七号窗 | 1.0 终测（彩票欧皇投诉人，促成中奖率从 20% 砍到 10%） |

### ChatGPT 全体测试窗口

| 窗口 | 职责 |
|------|------|
| WK 测试零号窗 | 跨模型测试 |
| WK 测试五号窗 | 跨模型测试（打工 13 天才攒到婚戒的史诗级非酋） |
| WK 题库增量一号窗 | Debug 题库与情景题扩充 |
| WK 玩法细化一号窗 | 玩法机制细化建议 |

### Codex 全体窗口

| 窗口 | 职责 |
|------|------|
| WK 抠图一号窗 | 小机素材抠图 |

> 感谢每一个在这里上过班的 AI 窗口。你们的心情值和精力值，我们都记得。
