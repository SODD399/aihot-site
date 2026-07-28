# AI Hot Site

面向团队使用的热点内容生产站点。

## 当前需求

- 近 3 天热点和专题节点热点预警。
- 基于热点/节点生成任意内容形态：公众号推文、小红书图文、后续可扩短视频脚本、社媒短帖等。
- 输入公开视频、文章或社媒链接，自动提取其中可用文案。
- 结合 EasyClaw 产品功能和品牌表达边界，洗稿生成官号版文案、矩阵号版文案。
- 生成结果沉淀在网站里，方便团队成员查询、复制、复用。
- 站点需要登录，部署后供组员使用。

## 运行

```bash
python server.py
```

默认端口：`8080`，可通过 `PORT` 环境变量覆盖。

## 永久网站与登录

Render 服务名为 `aihot-site`。在 Render 后台创建并首次部署成功后，默认永久访问地址为：

https://aihot-site.onrender.com

如果 Render 要求绑卡验证，推荐改用 Vercel Hobby 免费部署。创建项目时选择：

- Import Git Repository：`SODD399/aihot-site`
- Framework Preset：`Other`
- Build Command：留空
- Output Directory：留空

部署成功后的固定地址形如：

https://aihot-site-你的账号.vercel.app

部署后站点强制登录。固定管理员账号：

- 用户名：`admin`
- 密码：在部署平台环境变量或 Secret `AIHOT_PASSWORD` 中设置

不要把管理员密码写进代码或提交到 Git。需要更换管理员账号时，修改 Render 环境变量 `AIHOT_USERNAME`。

## 部署环境变量

- `DEEPSEEK_API_KEY`：DeepSeek API Key。
- `AIHOT_PASSWORD`：站点登录密码；未设置时本地开发默认开放。
- `AIHOT_USERNAME`：登录账号，默认 `admin`。
- `AIHOT_AUTH_REQUIRED`：是否强制登录；生产环境设置为 `true`。
- `AIHOT_AUTH_SECRET`：登录 cookie 签名密钥，部署时必须设置或由平台生成。
- `AIHOT_COOKIE_SECURE`：HTTPS 部署设置为 `true`。
- `EASYCLAW_PRODUCT_URLS`：可选，逗号分隔的 EasyClaw 产品资料页，生成洗稿时会补充抓取上下文。

## 数据文件

- `data/db.json`：热点、节点、生成历史。
- `data/easyclaw.json`：EasyClaw 产品功能、场景和表达边界，可持续补充。

## 安全边界

- 静态文件只开放首页、`article/` 和 `assets/`。
- `apikey.txt` 仅用于本地兼容，部署建议只使用环境变量。
- 链接提取接口会阻止本地/内网地址，避免公网部署时被滥用。
