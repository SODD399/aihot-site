# -*- coding: utf-8 -*-
"""
龙虾日记 · 每日内容生产流水线
每天 11:00 运行 → 拉取热点 → AI 生成 → 写入 site/ → git push → Vercel 自动部署
兼容新版页面结构：今日热点（主线+副线）→ 龙虾出品 → 龙虾帮你
"""
import json, sys, time, subprocess, os, re
from pathlib import Path
from datetime import datetime

SITE_DIR = Path(__file__).parent  # daily.py 所在目录即站点根目录
DATA_FILE = SITE_DIR / "data" / "db.json"

# 内容平台路径：查找同级目录下的内容平台
CONTENT_PLATFORM = SITE_DIR.parent / "aihot-content-platform"


def load_db():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"date": "", "sections": [], "outputs": {}}


def save_db(db):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ db.json 已更新 ({len(json.dumps(db))} bytes)")


def fetch_sources():
    """拉取多信源热点 - 优先使用内容平台，否则用演示数据"""
    if CONTENT_PLATFORM.exists():
        try:
            sys.path.insert(0, str(CONTENT_PLATFORM))
            from sources import MultiSourceFetcher
            import yaml, logging
            cfg_path = CONTENT_PLATFORM / "config.yaml"
            cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
            logger = logging.getLogger("daily")
            logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
            fetcher = MultiSourceFetcher(cfg, logger)
            data = fetcher.fetch_all()
            print(f"📡 [内容平台] 拉取完成: {data['date']}, {len(data['sections'])} 个轨道")
            return data
        except Exception as e:
            print(f"⚠️ 内容平台加载失败: {e}")

    print("📡 [演示模式] 生成示例热点数据...")
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today,
        "sections": [
            {
                "label": "AI 热点",
                "track": "ai",
                "items": [
                    {"title": "DeepSeek V4 发布，推理能力全面超越 GPT-5，开源社区沸腾", "sourceName": "36氪", "sourceUrl": "https://36kr.com", "publishedAt": today + "T08:00:00"},
                    {"title": "Anthropic 发布 Claude Opus 4.5，企业级 AI 助手新标杆", "sourceName": "TechCrunch", "sourceUrl": "https://techcrunch.com", "publishedAt": today + "T07:30:00"},
                    {"title": "AI 编程助手 Cursor 估值突破 100 亿美元", "sourceName": "The Information", "sourceUrl": "https://theinformation.com", "publishedAt": today + "T09:00:00"},
                ]
            },
            {
                "label": "金融理财",
                "track": "finance",
                "items": [
                    {"title": "美联储暗示9月降息，全球股市集体上涨，科技股领涨", "sourceName": "Reuters", "sourceUrl": "https://reuters.com", "publishedAt": today + "T09:00:00"},
                    {"title": "A股成交额突破2万亿，AI概念股领涨，北向资金大幅流入", "sourceName": "华尔街见闻", "sourceUrl": "https://wallstreetcn.com", "publishedAt": today + "T10:00:00"},
                    {"title": "比特币突破15万美元，机构投资者加速入场", "sourceName": "Bloomberg", "sourceUrl": "https://bloomberg.com", "publishedAt": today + "T08:30:00"},
                ]
            },
            {
                "label": "电商消费",
                "track": "ecommerce",
                "items": [
                    {"title": "TikTok Shop 东南亚单日GMV破10亿美元，直播电商爆发", "sourceName": "虎嗅", "sourceUrl": "https://huxiu.com", "publishedAt": today + "T08:30:00"},
                    {"title": "拼多多TEMU加速欧洲扩张，已在12国上线，挑战亚马逊", "sourceName": "36氪", "sourceUrl": "https://36kr.com", "publishedAt": today + "T07:00:00"},
                    {"title": "SHEIN 秘密提交伦敦IPO申请，估值超800亿美元", "sourceName": "Financial Times", "sourceUrl": "https://ft.com", "publishedAt": today + "T11:00:00"},
                ]
            },
        ]
    }


def generate_wechat(item, date_str):
    """生成公众号推文 HTML"""
    title = item.get("title", "")
    track = item.get("track", "")
    source_name = item.get("sourceName", "未知来源")
    source_url = item.get("sourceUrl", "#")

    slug = _slug(title)
    html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
    html += '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    html += '<title>' + title + '</title>\n'
    html += '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">\n'
    html += '<style>\n'
    html += 'body{margin:0;padding:0;background:#faf8f5;font-family:"Noto Sans SC",sans-serif}\n'
    html += '.article{max-width:680px;margin:0 auto;padding:40px 20px 80px}\n'
    html += 'h1{font-size:26px;font-weight:900;line-height:1.35;color:#1a1a1a;margin-bottom:12px}\n'
    html += '.meta{font-size:13px;color:#999;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #eee}\n'
    html += '.back{display:inline-block;margin-bottom:20px;font-size:14px;color:#e05a2d}\n'
    html += '.content{font-size:17px;line-height:1.9;color:#333}\n'
    html += '.content p{margin:16px 0}\n'
    html += '.content h2{font-size:20px;font-weight:700;margin:28px 0 10px;color:#1a1a1a}\n'
    html += 'blockquote{border-left:4px solid #e05a2d;padding:12px 16px;margin:16px 0;background:#fdf5f1;color:#555;font-size:15px}\n'
    html += '.footer{text-align:center;padding:30px 20px;color:#999;font-size:13px;border-top:1px solid #eee;margin-top:40px}\n'
    html += '</style>\n</head>\n<body>\n'
    html += '<div class="article">\n'
    html += '<a class="back" href="/">&larr; 返回龙虾日记</a>\n'
    html += '<h1>' + title + '</h1>\n'
    html += '<div class="meta">' + date_str + ' · 龙虾日记 · AI 生成</div>\n'
    html += '<div class="content">\n'
    html += '<blockquote>📌 本文由 EasyClaw AI 自动分析生成，基于当日热点数据。</blockquote>\n'
    html += '<h2>📰 热点速览</h2>\n'
    html += '<p>' + title + '——这是今天最值得关注的' + _track_cn(track) + '领域动态。</p>\n'
    html += '<p>来源：<a href="' + source_url + '" target="_blank">' + source_name + '</a></p>\n'
    html += '<h2>🦞 龙虾点评</h2>\n'
    html += '<p>该热点反映出当前' + _track_cn(track) + '赛道的核心趋势。EasyClaw 数字员工已为你准备好深度解读和二次创作素材。</p>\n'
    html += '</div>\n'
    html += '<div class="footer">🦞 龙虾日记 · EasyClaw 内容工厂 · <a href="https://easyclaw.com">easyclaw.com</a><br><span style="font-size:12px;color:#aaa">AI 生成内容，仅供参考</span></div>\n'
    html += '</div>\n</body>\n</html>'

    article_dir = SITE_DIR / "article"
    article_dir.mkdir(parents=True, exist_ok=True)
    article_path = article_dir / (slug + ".html")
    article_path.write_text(html, encoding="utf-8")
    print(f"  📝 公众号 HTML: {article_path}")

    return {
        "file": str(article_path),
        "url": "/article/" + slug + ".html",
        "content": "【" + _track_cn(track) + "热点】" + title + "——来源：" + source_name + "。该热点反映了当前" + _track_cn(track) + "赛道的核心趋势。",
    }


def generate_x_tweet(item, date_str):
    """生成 X/Twitter 推文草稿"""
    title = item.get("title", "")
    track = item.get("track", "")
    source_name = item.get("sourceName", "")

    long_tweet = "🔥 " + title + "\n\nvia " + source_name + "\n\n" + _generate_tweet_insight(track, title) + "\n\n#AI #HotTopic"
    short_tweet = "🚀 " + title[:80] + "... #breaking"

    return {
        "content": long_tweet[:400],
        "content_cn": title,
        "short1": short_tweet[:240],
        "short1_cn": title[:80],
    }


def generate_xiaohongshu(item, date_str):
    """生成小红书笔记草稿"""
    title = item.get("title", "")
    track = item.get("track", "")

    hashtag = "AI" if track == "ai" else ("搞钱" if track == "finance" else "电商")
    content = (
        "姐妹们！今天的重磅消息来了 💥\n\n"
        + "📌 " + title + "\n\n"
        + _generate_xhs_insight(track, title) + "\n\n"
        + "💡 小龙虾已经帮大家整理好了关键信息，这篇值得收藏！\n\n"
        + "#龙虾日记 #每日热点 #" + hashtag + " #干货分享"
    )
    return {
        "content": content[:600],
        "display_title": "🔥 " + ("AI圈" if track == "ai" else ("财经圈" if track == "finance" else "电商圈")) + "炸了！" + title[:30] + "...",
    }


def generate_worldcup_data(date_str):
    """生成世界杯预测/分析内容"""
    return [
        {
            "title": "龙虾三场全中！今日世界杯淘汰赛预测",
            "display_title": "🦞 龙虾预测 " + date_str + " 世界杯淘汰赛",
            "content": "🏆 龙虾今日世界杯淘汰赛预测：基于AI模型分析各队实力、伤病、历史交锋数据。更多详情请查看龙虾日记世界杯专题。",
            "track": "worldcup",
            "source_label": "世界杯",
            "source_name": "龙虾日记",
            "date": date_str,
        },
    ]


def _track_cn(track):
    return {"ai": "AI", "finance": "金融理财", "ecommerce": "电商消费"}.get(track, "综合")


def _generate_tweet_insight(track, title):
    insights = {
        "ai": "AI赛道持续升温，技术迭代速度前所未有。企业必须拥抱变化。",
        "finance": "市场信号明确，投资者需要及时调整策略。机会总是留给有准备的人。",
        "ecommerce": "电商格局正在重塑，出海和直播是两大不可忽视的趋势。",
    }
    return insights.get(track, "热点事件值得关注，持续跟进中。")


def _generate_xhs_insight(track, title):
    insights = {
        "ai": "AI圈最近真的太卷了！每天都有新技术出来，不学真的会被淘汰啊姐妹们 😱 赶紧关注起来！",
        "finance": "搞钱人必看！今天的市场风向很关键，聪明的钱已经开始布局了 💰",
        "ecommerce": "做电商的姐妹注意了！这个信号很重要，跟对了方向真的能赚到 🛒✨",
    }
    return insights.get(track, "今天的重磅消息！值得每个关注行业动态的人看看 👀")


def _slug(title, max_len=40):
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '_', title or "untitled")
    return s[:max_len].strip('_') or "article"


def git_push():
    """推送到 Git → 触发 Vercel 部署"""
    try:
        subprocess.run(["git", "-C", str(SITE_DIR), "add", "."], check=True)
        subprocess.run(["git", "-C", str(SITE_DIR), "commit", "-m",
                       "daily: " + datetime.now().strftime('%Y-%m-%d') + " 内容更新"], check=True)
        subprocess.run(["git", "-C", str(SITE_DIR), "push", "origin", "master"], check=True)
        print("🚀 git push 完成，Vercel 将自动部署")
        return True
    except Exception as e:
        print(f"⚠️ git push 失败: {e}")
        return False


def run():
    """主流程：拉取热点 → 多平台生成 → 写入 db.json → 推送"""
    print(f"\n{'='*60}")
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    print("🦞 龙虾日记 · 每日生产  " + now_str)
    print(f"{'='*60}\n")

    # 1. 拉取信源
    print("📡 [1/5] 拉取热点...")
    daily = fetch_sources()
    date_str = daily.get("date", datetime.now().strftime("%Y-%m-%d"))

    # 2. 挑选热点（每轨道取前2条）
    print("🎯 [2/5] 挑选热点...")
    picked = []
    for sec in daily.get("sections", []):
        items = sec.get("items", [])[:2]
        for it in items:
            it["section_label"] = sec.get("label", "")
            it["track"] = sec.get("track", "")
            picked.append(it)
        print("  " + sec['label'] + ": 取 " + str(len(items)) + " 条")

    # 3. 生成内容（多平台）
    print("⚙️  [3/5] 生成多平台内容...")
    db = load_db()
    db["date"] = date_str
    db["sections"] = daily.get("sections", [])

    if "outputs" not in db:
        db["outputs"] = {}
    for plat in ["wechat", "x_tweet", "xiaohongshu"]:
        if plat not in db["outputs"]:
            db["outputs"][plat] = []

    # 公众号推文
    for item in picked:
        title = item.get("title", "")
        print("  🟢 公众号: " + title[:45] + "...")
        result = generate_wechat(item, date_str)
        db["outputs"]["wechat"].append({
            "title": title,
            "display_title": title,
            "original_title": title,
            "date": date_str,
            "content": result["content"],
            "image_path": "",
            "image_url": "",
            "source_name": item.get("sourceName", ""),
            "source_url": item.get("sourceUrl", ""),
            "source_label": item.get("section_label", ""),
            "track": item.get("track", ""),
            "source_title": title,
            "html_file": result["file"],
            "html_url": result["url"],
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        })

    # X 推文
    for item in picked[:2]:
        title = item.get("title", "")
        print("  🐦 X推文: " + title[:45] + "...")
        result = generate_x_tweet(item, date_str)
        db["outputs"]["x_tweet"].append({
            "title": title,
            "display_title": title,
            "original_title": title,
            "date": date_str,
            "content": result["content"],
            "content_cn": result["content_cn"],
            "short1": result["short1"],
            "short1_cn": result["short1_cn"],
            "source_name": item.get("sourceName", ""),
            "source_label": item.get("section_label", ""),
            "track": item.get("track", ""),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        })

    # 小红书
    for item in picked[:3]:
        title = item.get("title", "")
        print("  📕 小红书: " + title[:45] + "...")
        result = generate_xiaohongshu(item, date_str)
        db["outputs"]["xiaohongshu"].append({
            "title": title,
            "display_title": result.get("display_title", title),
            "original_title": title,
            "date": date_str,
            "content": result["content"],
            "source_name": item.get("sourceName", ""),
            "source_label": item.get("section_label", ""),
            "track": item.get("track", ""),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        })

    # 4. 世界杯专题
    print("⚽ [4/5] 世界杯预测...")
    if "worldcup" not in db["outputs"]:
        db["outputs"]["worldcup"] = []
    wc_items = generate_worldcup_data(date_str)
    for wc in wc_items:
        db["outputs"]["worldcup"].append({
            "title": wc["title"],
            "display_title": wc["display_title"],
            "original_title": wc["title"],
            "date": date_str,
            "content": wc["content"],
            "image_path": "",
            "image_url": "",
            "source_name": wc.get("source_name", "龙虾日记"),
            "source_label": wc.get("source_label", "世界杯"),
            "track": "worldcup",
            "html_url": "/article/lobster_july2_prediction.html",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        })

    # 5. 保存 + 推送
    print("💾 [5/5] 保存并推送...")

    # 去重
    for plat in db["outputs"]:
        seen = set()
        unique = []
        for entry in db["outputs"][plat]:
            key = entry.get("original_title", "")
            if key not in seen:
                seen.add(key)
                unique.append(entry)
        db["outputs"][plat] = unique

    save_db(db)

    pushed = git_push()

    total = sum(len(v) for v in db["outputs"].values())
    other_count = sum(1 for k in db["outputs"] if k != "wechat" for _ in db["outputs"][k])
    print(f"\n{'='*60}")
    print("✅ 完成！共生成 " + str(total) + " 篇内容（" + str(len(picked)) + " 篇公众号 + " + str(other_count) + " 篇其他平台）")
    if pushed:
        print("🌐 网站: https://aihot-content.vercel.app")
    else:
        print("📂 本地: " + str(SITE_DIR))
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
