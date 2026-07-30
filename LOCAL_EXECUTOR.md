# 抖音个人号本地执行器

这个执行器用于个人号半自动运营：网站生成任务和话术，本机 Chrome 辅助打开抖音创作者中心。它不需要抖音开放平台资质，也不保存账号密码。

## 第一次登录

在项目目录运行：

```bat
.\local_executor.bat login --account "矩阵号 A"
```

脚本会打开一个独立 Chrome 窗口。你在里面登录抖音账号，登录状态只保存在本机 `.local-douyin-profile/`，该目录不会提交到 Git。

## 发布任务

先在网站的 `自动化运营 -> 矩阵号 A -> 批量发布` 创建发布任务包，然后运行：

```bat
.\local_executor.bat publish --account "矩阵号 A"
```

执行器会打开抖音发布页，并在 `data/executor/` 生成一份发布包 txt，里面包含标题、视频路径、文案、tag、封面说明。第一版会停在发布前，由你人工确认。

## 评论采集

运行：

```bat
.\local_executor.bat comments --account "矩阵号 A"
```

打开创作者中心后，手动进入目标作品的评论页面并滚动加载评论。优先用鼠标选中评论区域文本，再回到命令行按 Enter；执行器会优先采集选中文本，没有选中文本时才保存当前页面可见文本到 `data/executor/`。把里面的评论行粘贴回网站 `评论监测`，系统会自动分拣并生成回复草稿。

如果你本机也启动了网站服务，可以让执行器自动回传到网站：

```bat
.\local_executor.bat comments --account "矩阵号 A" --site "http://127.0.0.1:8080"
```

线上 Vercel 站点因为有登录保护，执行器默认不直接回传；先用本机服务跑闭环最稳。

## 注意

- 不要把抖音账号密码、cookie 或扫码登录态发给别人。
- 评论回复、发布视频、粉丝群发送等关键动作建议保留人工确认。
- 抖音页面改版后，采集步骤可能需要调整。

## 外部执行器适配口

如果后续找到能提供 API/Webhook 的第三方执行服务，不需要重写网站，只要在部署环境配置：

```text
AIHOT_DOUYIN_EXECUTOR_WEBHOOK=https://example.com/webhook
AIHOT_DOUYIN_EXECUTOR_TOKEN=可选的服务商鉴权 token
```

配置后，发布任务和评论草稿上的 `推外部` 按钮会把任务 JSON 推送过去。
