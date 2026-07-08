#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国内社媒 x AI Native — 后端服务
功能：AI内容生成 + 抖音文案提取 + 热点/节点数据管理
接口：DeepSeek API (OpenAI 兼容) 或 easycode CLI
"""

import json, os, re, time, uuid, subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

SITE_DIR = Path(__file__).parent
DATA_FILE = SITE_DIR / "data" / "db.json"
ARTICLE_DIR = SITE_DIR / "article"
ARTICLE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════
# AI 配置
# ═══════════════════════════════════════════
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_MODEL = "deepseek-chat"

# easycode CLI 路径（macOS/Linux）
EASYCODE_CLI = os.environ.get("EASYCODE_PATH", "/usr/local/bin/easycode")
USE_EASYCODE = False  # 自动检测


def detect_ai_backend():
    """检测可用的 AI 后端"""
    global USE_EASYCODE
    if os.path.exists(EASYCODE_CLI):
        try:
            result = subprocess.run([EASYCODE_CLI, "--help"], capture_output=True, timeout=5)
            if result.returncode == 0:
                USE_EASYCODE = True
                print(f"✅ 使用 easycode CLI: {EASYCODE_CLI}")
                return
        except Exception:
            pass
    if DEEPSEEK_API_KEY:
        USE_EASYCODE = False
        print(f"✅ 使用 DeepSeek API: {DEFAULT_MODEL}")
    else:
        print("⚠️ 未配置 AI 后端！请设置 DEEPSEEK_API_KEY 或安装 easycode")


def llm_call(prompt, timeout=300):
    """统一的 LLM 调用入口"""
    if USE_EASYCODE:
        return _llm_via_easycode(prompt, timeout)
    elif DEEPSEEK_API_KEY:
        return _llm_via_deepseek(prompt, timeout)
    else:
        return _llm_fallback(prompt)


def _llm_via_easycode(prompt, timeout=300):
    """通过 easycode CLI 调用"""
    try:
        result = subprocess.run(
            [EASYCODE_CLI, "--output-format", "stream-json", "-m", DEFAULT_MODEL, "-p", prompt, "-y"],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ""
    parts = []
    for line in (result.stdout or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if msg.get("type") == "message" and msg.get("role") == "assistant":
            c = msg.get("content", "")
            if isinstance(c, str):
                parts.append(c)
    return "".join(parts).strip()


def _llm_via_deepseek(prompt, timeout=300):
    """通过 DeepSeek API (OpenAI 兼容) 调用"""
    import urllib.request
    data = json.dumps({
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 4000,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"DeepSeek API 错误: {e}")
        return _llm_fallback(prompt)


def _llm_fallback(prompt):
    """无 AI 时的兜底模板"""
    title_match = re.search(r'热点[：:]?\s*(.+)', prompt.split('\n')[0])
    title = title_match.group(1) if title_match else "热点内容"
    return f"""【AI 生成模板 · 请配置 API Key 以启用智能生成】

{title}

这里是 AI 生成的内容区域。请设置环境变量 DEEPSEEK_API_KEY 以启用 DeepSeek API，或安装 easycode CLI。

来源：AI Native 平台 · {datetime.now().strftime('%Y-%m-%d')}

⚠️ 当前为模板占位内容，实际使用时将被 AI 智能生成的内容替换。"""


# ═══════════════════════════════════════════
# 数据管理
# ═══════════════════════════════════════════
def load_db():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"hotspots": [], "events": [], "generated": [], "last_updated": ""}


def save_db(db):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    db["last_updated"] = datetime.now().isoformat(timespec="seconds")
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    return db


def init_demo_data():
    """初始化演示数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    hotspots = [
        {"id": "h1", "type": "ai", "date": today, "time": "08:30",
         "title": "DeepSeek V4 发布，推理能力全面超越 GPT-5，开源社区沸腾",
         "source": "36氪", "sourceUrl": "https://36kr.com",
         "summary": "DeepSeek 最新模型在多项基准测试中超越 GPT-5，且完全开源。这意味着中小企业也能用上顶级 AI。"},
        {"id": "h2", "type": "ai", "date": today, "time": "07:00",
         "title": "Anthropic 发布 Claude Opus 4.5，企业级 AI 助手新标杆",
         "source": "TechCrunch", "sourceUrl": "https://techcrunch.com",
         "summary": "Claude 新一代模型大幅提升推理和代码能力，API 价格同步下调 50%。"},
        {"id": "h3", "type": "finance", "date": today, "time": "09:00",
         "title": "A股成交额突破2万亿，AI概念股领涨",
         "source": "华尔街见闻", "sourceUrl": "https://wallstreetcn.com",
         "summary": "市场情绪高涨，北向资金大幅流入，科技板块成为最大赢家。"},
        {"id": "h4", "type": "finance", "date": today, "time": "10:30",
         "title": "比特币突破15万美元，机构投资者加速入场",
         "source": "Bloomberg", "sourceUrl": "https://bloomberg.com",
         "summary": "多家华尔街机构获批加密货币托管业务，比特币创历史新高。"},
        {"id": "h5", "type": "ecommerce", "date": today, "time": "08:00",
         "title": "TikTok Shop 东南亚单日GMV破10亿美元",
         "source": "虎嗅", "sourceUrl": "https://huxiu.com",
         "summary": "直播电商在东南亚爆发式增长，MCN机构和品牌加速入局。"},
        {"id": "h6", "type": "ecommerce", "date": yesterday, "time": "16:00",
         "title": "SHEIN 秘密提交伦敦IPO申请，估值超800亿美元",
         "source": "Financial Times", "sourceUrl": "https://ft.com",
         "summary": "快时尚巨头 SHEIN 加速全球化扩张，伦敦上市将成今年最大 IPO。"},
        {"id": "h7", "type": "ai", "date": yesterday, "time": "14:00",
         "title": "AI 编程助手 Cursor 估值突破 100 亿美元",
         "source": "The Information", "sourceUrl": "https://theinformation.com",
         "summary": "Cursor 在最新一轮融资中估值突破 100 亿美元，AI 编程工具赛道持续火热。"},
    ]

    events = [
        {"id": "e1", "type": "worldcup", "date": "2026-07-09", "title": "世界杯半决赛",
         "source": "FIFA官方", "summary": "四强对决。可提前准备半决赛球队分析、历史对战数据、龙虾预测。方向：赛前分析长文 + 小红书比分预测图 + 公众号复盘推文。",
         "isWarning": False},
        {"id": "e2", "type": "worldcup", "date": "2026-07-14", "title": "世界杯决赛",
         "source": "FIFA官方", "summary": "决赛之夜。方向：决赛前瞻 + 双方实力深度分析 + 赛后复盘 + 龙虾日记世界杯总结。这是整个世界杯期间流量最高的一天。",
         "isWarning": False},
        {"id": "e3", "type": "seasonal", "date": "2026-07-15", "title": "暑假黄金期 · 教辅机构招生冲刺",
         "source": "行业提醒", "summary": "7月中旬是K12暑假班最后一波招生窗口。方向：生成朋友圈招生海报文案、社群招生话术、试听课邀约文章。",
         "isWarning": False},
        {"id": "e4", "type": "seasonal", "date": "2026-07-20", "title": "暑期在线教育内容营销",
         "source": "行业提醒", "summary": "暑期过半，机构可发布暑假学习报告/成长记录，带动续费。方向：公众号学员故事推文 + 小红书学员成果展示。",
         "isWarning": False},
        {"id": "e5", "type": "industry", "date": "2026-07-25", "title": "Q2 财报季密集发布",
         "source": "财经日历", "summary": "各大科技公司 Q2 财报陆续发布，关注 AI 相关业务增长数据。方向：财报解读文章 + 财经数据可视化 + 投资展望。",
         "isWarning": False},
        {"id": "e6", "type": "industry", "date": "2026-08-01", "title": "Apple/Google 秋季发布会预热",
         "source": "行业提醒", "isWarning": True,
         "summary": "⚠️ 预警：苹果和谷歌秋季发布会临近，AI 功能成焦点。建议提前储备相关解读素材。"},
        {"id": "e7", "type": "seasonal", "date": "2026-08-05", "title": "七夕营销节点",
         "source": "营销日历", "summary": "七夕（8月7日）前需完成方案。方向：社交 App/电商/礼品行业的文案和活动策划。",
         "isWarning": False},
        {"id": "e8", "type": "industry", "date": "2026-08-15", "title": "开学季预热 · 学习工具推广",
         "source": "行业提醒", "isWarning": True,
         "summary": "⚠️ 预警：距离开学还有2周，学习类App/教辅机构应开始布局开学季营销。"},
    ]

    return {"hotspots": hotspots, "events": events, "generated": [], "last_updated": datetime.now().isoformat()}


# ═══════════════════════════════════════════
# AI 生成逻辑
# ═══════════════════════════════════════════

OFFICIAL_STYLE = """你是品牌官方账号的主编，写作风格要求：
1. 专业、克制、客观，不拉踩任何竞品
2. 语气正式但不僵硬，能有适度的温度
3. 数据引用需标注来源，不夸大
4. 避免情绪化的感叹号和网络用语
5. 文章结构清晰、逻辑严谨"""

MATRIX_STYLE = """你是矩阵号（个人IP号/素人号）运营者，写作风格要求：
1. 口语化、自然，像朋友发朋友圈
2. 可以有情绪、有态度，允许轻微的吐槽和幽默
3. 可以使用网络流行语和 emoji
4. 不用太正式，但也不要太低俗
5. 短句为主，节奏轻快"""


def generate_wechat_article(item, style, db):
    """生成公众号推文"""
    title = item.get("title", "")
    src = item.get("source", "")
    summary = item.get("summary", "")
    item_type = item.get("type", "")

    style_prompt = OFFICIAL_STYLE if style == "official" else MATRIX_STYLE
    style_label = "官方号" if style == "official" else "矩阵号"
    type_cn = {"ai": "AI", "finance": "金融", "ecommerce": "电商", "worldcup": "世界杯",
               "seasonal": "节假日", "industry": "行业"}.get(item_type, "综合")

    prompt = f"""{style_prompt}

请基于以下热点信息，写一篇公众号推文（{style_label}风格，{type_cn}赛道）。

热点标题：{title}
来源：{src}
背景摘要：{summary}

【写作要求】
1. 标题要有吸引力（悬念、反问、数字、对比 四选一），不要新闻通稿风
2. 开头用具体故事/场景勾起好奇，100-150字
3. 主体 2-3 个观点，每个用类比解释，600-900字
4. 结尾金句收尾 + 引导关注，100-150字
5. 全文 1000-1500 字
6. 不要出现"原文来源""原文链接""来源：xx""译自""出处"等外部引用
7. 不要用 Markdown 语法（不要 **粗体**、#标题、>引用）
8. 不要拉踩任何具体公司或产品（{ '官号底线：绝对不拉踩' if style == 'official' else '矩阵号可以轻度调侃但不要恶意攻击' }）
9. {'语气专业克制，数据可查证' if style == 'official' else '语气随意自然，像跟朋友聊天一样'}

格式要求：
# [标题]

[开头段落]

[主体段落]

[结尾段落]

只输出文章，不要任何额外解释。"""

    content = llm_call(prompt, timeout=300)
    if len(content) < 100:
        content = f"# {title}\n\n## AI 生成失败，请检查 API 配置。\n\n{summary}"

    # 提取标题
    title_match = re.search(r'^#\s+(.+?)\s*$', content, re.MULTILINE)
    display_title = title_match.group(1).strip() if title_match else title

    return {
        "id": f"gen_{uuid.uuid4().hex[:8]}",
        "type": "wechat",
        "style": style,
        "styleLabel": style_label,
        "title": display_title,
        "content": content,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sourceTitle": item.get("title", ""),
        "sourceType": item_type,
    }


def generate_xiaohongshu(item, style, db):
    """生成小红书图文笔记"""
    title = item.get("title", "")
    src = item.get("source", "")
    summary = item.get("summary", "")
    item_type = item.get("type", "")

    style_prompt = OFFICIAL_STYLE if style == "official" else MATRIX_STYLE
    style_label = "官方号" if style == "official" else "矩阵号"
    type_cn = {"ai": "AI", "finance": "金融理财", "ecommerce": "电商好物", "worldcup": "世界杯",
               "seasonal": "节日活动", "industry": "行业趋势"}.get(item_type, "综合")

    prompt = f"""{style_prompt}

你是一个小红书博主，请基于以下热点，写一篇小红书图文风格的笔记（{style_label}，{type_cn}方向）。

热点：{title}
来源：{src}
背景：{summary}

【小红书笔记要求】
1. 标题：爆款标题风格，「」格式，要有钩子（15字以内）
2. 正文：分 point 式，每段短，大量换行
3. 带 emoji 分隔（姐妹们都看过来 💥 这种）
4. {'官号版：专业但不严肃，可以适度活泼' if style == 'official' else '矩阵号版：像朋友分享，可以有个人观点和吐槽'}
5. 结尾要有互动引导（点赞收藏关注）
6. 话题标签 3-5 个
7. 不要出现"原文来源"等引用信息
8. 不要拉踩竞品{'（官号绝对禁止）' if style == 'official' else '（可以轻度吐槽但不要恶意）'}

格式：
【标题】

正文内容（emoji分隔，短句多换行）

标签：
#tag1 #tag2 #tag3

直接输出小红书笔记。"""

    content = llm_call(prompt, timeout=200)

    # 尝试提取标题
    title_match = re.search(r'【(.+?)】', content)
    display_title = title_match.group(1) if title_match else title[:15]

    return {
        "id": f"gen_{uuid.uuid4().hex[:8]}",
        "type": "xiaohongshu",
        "style": style,
        "styleLabel": style_label,
        "title": display_title,
        "content": content,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sourceTitle": item.get("title", ""),
        "sourceType": item_type,
    }


def generate_copywriting(text, style):
    """洗稿：将原始文案改写为官号或矩阵号版本"""
    style_prompt = OFFICIAL_STYLE if style == "official" else MATRIX_STYLE
    style_label = "官方号" if style == "official" else "矩阵号"

    prompt = f"""{style_prompt}

请将以下原始文案进行洗稿改写，保持核心信息和关键点不变，但重新组织语言、调整结构、优化表达。

原始文案：
---
{text}
---

改写要求：
1. {'官号风格：专业克制，逻辑清晰，适合品牌传播' if style == 'official' else '矩阵号风格：口语化自然，有个人态度，适合社媒传播'}
2. 保留所有核心数据和关键信息点
3. 重新组织结构，不按原文段落顺序
4. 语言表达完全重写，不用原文的句式
5. 可以适当增加背景信息或过渡内容让文章更流畅
6. {'绝对不拉踩、不攻击、不贬低任何品牌或个人' if style == 'official' else '可以有个性化的观点和态度，但不要恶意攻击'}
7. 字数保持与原文相当或略多 10-20%

直接输出改写后的文案，不要额外解释。"""

    content = llm_call(prompt, timeout=200)
    return content if len(content) > 50 else f"【改写失败，请检查 API 配置】\n\n{text[:200]}..."


# ═══════════════════════════════════════════
# 抖音文案提取
# ═══════════════════════════════════════════
def extract_douyin(url):
    """尝试从抖音链接提取文案"""
    try:
        import urllib.request

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        # 尝试直接请求
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 尝试多种方式提取
        desc = ""

        # 方式1：搜索 title 标签
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
        if title_match:
            desc = title_match.group(1).strip()
            # 清理抖音标题中的通用后缀
            desc = re.sub(r'\s*[-–—|]\s*抖音\s*$', '', desc)

        # 方式2：搜索 meta description
        if not desc or len(desc) < 20:
            meta_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
            if meta_match:
                desc = meta_match.group(1)

        # 方式3：从 JSON-LD 或 script 中提取
        if not desc or len(desc) < 20:
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.I | re.S)
            for s in scripts:
                try:
                    data = json.loads(s)
                    if isinstance(data, dict):
                        desc = data.get("description", data.get("name", ""))
                        if desc and len(desc) > 20:
                            break
                except Exception:
                    pass

        if desc and len(desc) > 10:
            # 清理 HTML entity
            desc = desc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
            return {"success": True, "text": desc, "source": url, "title": desc[:80]}

        return {"success": False, "error": "无法从页面提取到有效文案", "hint": "建议手动复制抖音视频的文案内容粘贴到下方文本框", "url": url}

    except Exception as e:
        return {"success": False, "error": f"提取失败：{str(e)}", "hint": "抖音页面可能需要登录或使用了反爬机制。请手动复制文案内容粘贴到下方。", "url": url}


# ═══════════════════════════════════════════
# HTTP Server
# ═══════════════════════════════════════════

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # API 路由
        if path == "/api/status":
            db = load_db()
            self._send_json({
                "ai_ready": bool(DEEPSEEK_API_KEY or USE_EASYCODE),
                "backend": "easycode" if USE_EASYCODE else ("deepseek" if DEEPSEEK_API_KEY else "none"),
                "counts": {
                    "hotspots": len(db.get("hotspots", [])),
                    "events": len(db.get("events", [])),
                    "generated": len(db.get("generated", [])),
                },
                "last_updated": db.get("last_updated", ""),
            })

        elif path == "/api/hotspots":
            db = load_db()
            if not db.get("hotspots"):
                db = init_demo_data()
                save_db(db)
            # 返回近3天热点
            three_days = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            hotspots = [h for h in db["hotspots"] if h["date"] >= three_days]
            hotspots.sort(key=lambda x: (x["date"], x.get("time", "")), reverse=True)
            self._send_json(hotspots)

        elif path == "/api/events":
            db = load_db()
            if not db.get("events"):
                db = init_demo_data()
                save_db(db)
            today = datetime.now().strftime("%Y-%m-%d")
            events = [e for e in db["events"] if e["date"] >= today]
            events.sort(key=lambda x: x["date"])
            self._send_json(events)

        elif path == "/api/generated":
            db = load_db()
            generated = db.get("generated", [])
            generated.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            self._send_json(generated)

        # 静态文件
        elif path == "/" or path == "":
            self._serve_file("index.html", "text/html")
        elif path.endswith(".html"):
            self._serve_file(path.lstrip("/"), "text/html")
        elif path.endswith(".js"):
            self._serve_file(path.lstrip("/"), "application/javascript")
        elif path.endswith(".css"):
            self._serve_file(path.lstrip("/"), "text/css")
        elif path.endswith(".json"):
            self._serve_file(path.lstrip("/"), "application/json")
        else:
            # 尝试作为静态文件
            file_path = SITE_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                ext = path.rsplit(".", 1)[-1].lower()
                content_types = {
                    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "gif": "image/gif", "svg": "image/svg+xml", "ico": "image/x-icon",
                    "woff2": "font/woff2", "woff": "font/woff",
                }
                self._serve_file(path.lstrip("/"), content_types.get(ext, "application/octet-stream"))
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/generate":
            item = body.get("item", {})
            gen_type = body.get("type", "wechat")  # wechat | xiaohongshu | copywriting
            style = body.get("style", "matrix")  # official | matrix
            douyin_text = body.get("text", "")  # 洗稿原始文案

            db = load_db()

            if gen_type == "wechat":
                result = generate_wechat_article(item, style, db)
            elif gen_type == "xiaohongshu":
                result = generate_xiaohongshu(item, style, db)
            elif gen_type == "copywriting":
                if not douyin_text:
                    self._send_json({"error": "请提供需要洗稿的文案内容"}, 400)
                    return
                content = generate_copywriting(douyin_text, style)
                result = {
                    "id": f"gen_{uuid.uuid4().hex[:8]}",
                    "type": "copywriting",
                    "style": style,
                    "styleLabel": "官方号" if style == "official" else "矩阵号",
                    "title": douyin_text[:80] + "...(改写)",
                    "content": content,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "sourceTitle": douyin_text[:80],
                }

            # 保存到历史记录
            if "generated" not in db:
                db["generated"] = []
            db["generated"].insert(0, result)  # 最新在前
            db["generated"] = db["generated"][:100]  # 保留最近100条
            save_db(db)

            self._send_json(result)

        elif path == "/api/extract-douyin":
            url = body.get("url", "")
            if not url:
                self._send_json({"success": False, "error": "请提供抖音链接"}, 400)
                return
            result = extract_douyin(url)
            self._send_json(result)

        elif path == "/api/init-demo":
            db = init_demo_data()
            save_db(db)
            self._send_json({"success": True, "message": "演示数据已初始化"})

        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, rel_path, content_type):
        file_path = SITE_DIR / rel_path
        if file_path.exists():
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def main():
    detect_ai_backend()
    port = int(os.environ.get("PORT", 5199))
    server = HTTPServer(("0.0.0.0", port), RequestHandler)
    print(f"\n{'='*60}")
    print(f"🦞 国内社媒 x AI Native 服务已启动")
    print(f"📍 http://localhost:{port}")
    print(f"📡 AI 后端: {'easycode' if USE_EASYCODE else ('DeepSeek API' if DEEPSEEK_API_KEY else '⚠️ 未配置')}")
    print(f"{'='*60}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
