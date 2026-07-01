"""
龙虾日记 · 每日内容生产流水线
每天 11:00 运行 → 拉取热点 → AI 生成 → 写入 site/ → git push → Vercel 自动部署
"""
import json, sys, time, subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
SITE_DIR = BASE_DIR / "site"
DATA_FILE = SITE_DIR / "data" / "db.json"

def load_db():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"date": "", "sections": [], "outputs": {}}

def save_db(db):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ db.json 已更新 ({len(json.dumps(db))} bytes)")

def fetch_sources():
    """拉取多信源热点"""
    sys.path.insert(0, str(BASE_DIR))
    from sources import MultiSourceFetcher
    import yaml, logging
    cfg = yaml.safe_load(open(BASE_DIR / "config.yaml", encoding="utf-8"))
    logger = logging.getLogger("daily")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    fetcher = MultiSourceFetcher(cfg, logger)
    data = fetcher.fetch_all()
    print(f"📡 拉取完成: {data['date']}, {len(data['sections'])} 个轨道")
    return data

def generate_wechat(item, date_str):
    """生成公众号推文"""
    title = item.get("title", "")
    track = item.get("track", "")

    # 构建推文 HTML
    slug = _slug(title)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
body{{margin:0;padding:0;background:#faf8f5;font-family:'Noto Sans SC',sans-serif}}
.article{{max-width:680px;margin:0 auto;padding:40px 20px 80px}}
h1{{font-size:26px;font-weight:900;line-height:1.35;color:#1a1a1a;margin-bottom:12px}}
.meta{{font-size:13px;color:#999;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #eee}}
.back{{display:inline-block;margin-bottom:20px;font-size:14px;color:#e05a2d}}
.content{{font-size:17px;line-height:1.9;color:#333}}
.content p{{margin:16px 0}}
.content h2{{font-size:20px;font-weight:700;margin:28px 0 10px;color:#1a1a1a}}
.footer{{text-align:center;padding:30px 20px;color:#999;font-size:13px;border-top:1px solid #eee;margin-top:40px}}
</style>
</head>
<body>
<div class="article">
<a class="back" href="/">← 返回龙虾日记</a>
<h1>{title}</h1>
<div class="meta">{date_str} · 龙虾日记 · AI 生成</div>
<div class="content">
<p>📝 本推文由 EasyClaw 自动生成，内容基于当日热点数据分析。</p>
<p>来源：{item.get('sourceName', '未知')}</p>
<p>原文链接：<a href="{item.get('sourceUrl','#')}" target="_blank">{item.get('sourceUrl','#')}</a></p>
</div>
<div class="footer">龙虾日记 · EasyClaw 内容工厂 · <a href="https://easyclaw.com">easyclaw.com</a></div>
</div>
</body>
</html>"""

    # 保存
    article_dir = SITE_DIR / "article"
    article_dir.mkdir(parents=True, exist_ok=True)
    article_path = article_dir / f"{slug}.html"
    article_path.write_text(html, encoding="utf-8")
    print(f"  📝 公众号 HTML: {article_path}")

    return {
        "file": str(article_path),
        "url": f"/article/{slug}.html",
        "content": item.get("summary", "") or title,
    }

def _slug(title, max_len=40):
    import re
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '_', title or "untitled")
    return s[:max_len].strip('_') or "article"

def git_push():
    """推送到 GitLab → 触发 Vercel 部署"""
    try:
        subprocess.run(["git", "-C", str(BASE_DIR), "add", "site/"], check=True)
        subprocess.run(["git", "-C", str(BASE_DIR), "commit", "-m",
                       f"daily: {datetime.now().strftime('%Y-%m-%d')} 内容更新"], check=True)
        subprocess.run(["git", "-C", str(BASE_DIR), "push", "origin", "master"], check=True)
        print("🚀 git push 完成，Vercel 将自动部署")
        return True
    except Exception as e:
        print(f"⚠️ git push 失败: {e}")
        return False

def run():
    """主流程"""
    print(f"\n{'='*60}")
    print(f"🦞 龙虾日记 · 每日生产  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # 1. 拉取信源
    print("📡 [1/4] 拉取热点...")
    daily = fetch_sources()
    date_str = daily.get("date", datetime.now().strftime("%Y-%m-%d"))

    # 2. 挑选热点（简单版：每个轨道取前2条）
    print("🎯 [2/4] 挑选热点...")
    picked = []
    for sec in daily.get("sections", []):
        items = sec.get("items", [])[:2]  # 每轨道取2条
        for it in items:
            it["section_label"] = sec.get("label", "")
            it["track"] = sec.get("track", "")
            picked.append(it)
        print(f"  {sec['label']}: 取 {len(items)} 条")

    # 3. 生成内容（公众号）
    print("⚙️  [3/4] 生成内容...")
    db = load_db()
    db["date"] = date_str
    db["sections"] = daily.get("sections", [])

    if "outputs" not in db:
        db["outputs"] = {}
    if "wechat" not in db["outputs"]:
        db["outputs"]["wechat"] = []

    for item in picked:
        title = item.get("title", "")
        print(f"  生成: {title[:50]}")

        result = generate_wechat(item, date_str)

        entry = {
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
        }

        # 去重
        db["outputs"]["wechat"] = [
            e for e in db["outputs"]["wechat"]
            if e.get("original_title", "") != title
        ]
        db["outputs"]["wechat"].append(entry)

    # 4. 保存 + 推送
    print("💾 [4/4] 保存并推送...")
    save_db(db)

    # 推送
    pushed = git_push()

    print(f"\n{'='*60}")
    print(f"✅ 完成！{len(picked)} 篇推文已生成")
    if pushed:
        print(f"🌐 网站: https://aihot-content.vercel.app")
    else:
        print(f"📂 本地: {SITE_DIR}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run()
