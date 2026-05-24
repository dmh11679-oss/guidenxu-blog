#!/usr/bin/env python3
"""
归灯序·黑灯工厂 - 博客自动发布脚本 v2.0
新结构：老兵判断 → 30秒看懂 → 能不能搞 → 图表 → 怎么上手 → 坑在哪 → 我的态度
"""
import json, os, sys, base64, math, textwrap
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================
BLOG_DIR = Path(__file__).parent
POSTS_DIR = BLOG_DIR / "posts"
ASSETS_DIR = BLOG_DIR / "assets"
REPORTS_DIR = BLOG_DIR.parent / "reports"

GITEE_TOKEN = "2a1bf843c7e5da216750893e8155d619"
GITEE_USER = "hdmhdm100"
GITEE_REPO = "guidenxu-blog"

BRAND = "归灯序"
TAGLINE = "帮散户避开坑，找到真机会"

# 颜色体系
C = {
    "green": "#10b981", "green_light": "#d1fae5", "green_bg": "#ecfdf5",
    "orange": "#f59e0b", "orange_light": "#fff3cd",
    "red": "#ef4444", "red_light": "#fee2e2", "red_bg": "#fff5f5",
    "blue": "#3b82f6", "blue_light": "#dbeafe",
    "gray": "#6c757d", "gray_light": "#e9ecef", "gray_bg": "#f8f9fa",
    "text": "#1a1a2e", "text_soft": "#4a4a6a", "white": "#ffffff",
}


# ============================================================
# 图表引擎
# ============================================================

def chart_earnings_bar(project):
    """收益预估条 - 适合有明确收益范围的项目"""
    lo = project.get("earn_low", 0)
    hi = project.get("earn_high", 100)
    unit = project.get("earn_unit", "元")
    period = project.get("earn_period", "月")

    w, h = 520, 90
    bar_max = max(hi * 1.15, 100)
    lo_pct = lo / bar_max
    hi_pct = hi / bar_max
    bar_x = 120
    bar_w = w - bar_x - 60

    svg = f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="chart-earnings">'
    svg += f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{C["gray_bg"]}"/>'

    # 低端标签
    svg += f'<text x="{bar_x - 12}" y="32" text-anchor="end" font-size="13" fill="{C["gray"]}" font-family="sans-serif">{unit}{lo}</text>'
    # 高端标签
    svg += f'<text x="{bar_x + bar_w + 8}" y="32" font-size="13" fill="{C["gray"]}" font-family="sans-serif">{unit}{hi}</text>'

    # 范围条
    y_bar = 42
    bar_h = 14
    x1 = bar_x + bar_w * lo_pct
    x2 = bar_x + bar_w * hi_pct
    svg += f'<rect x="{x1:.0f}" y="{y_bar}" width="{x2 - x1:.0f}" height="{bar_h}" rx="7" fill="{C["green"]}" opacity="0.85"/>'

    # 最小/最大端点
    for x_val, label in [(x1, "保守估计"), (x2, "乐观估计")]:
        svg += f'<circle cx="{x_val:.0f}" cy="{y_bar + bar_h/2:.0f}" r="6" fill="{C["white"]}" stroke="{C["green"]}" stroke-width="2.5"/>'
        anchor = "end" if x_val > bar_x + bar_w * 0.7 else "start"
        svg += f'<text x="{x_val:.0f}" y="{y_bar + bar_h + 28}" text-anchor="{anchor}" font-size="11" fill="{C["gray"]}" font-family="sans-serif">{label} {unit}{lo if x_val == x1 else hi}/{period}</text>'

    # 月收益标签
    svg += f'<text x="{bar_x + bar_w / 2:.0f}" y="18" text-anchor="middle" font-size="14" font-weight="600" fill="{C["text"]}" font-family="sans-serif">预计收益范围</text>'
    svg += "</svg>"
    return svg


def chart_threshold_ladder(project):
    """门槛阶梯 - 直观显示项目难度"""
    threshold = project.get("threshold", "零门槛")
    levels = [
        ("零门槛", "不需要技术\n不需要钱\n能上网就行", 0),
        ("需要技能", "要学点东西\n几天能上手", 1),
        ("需要资金", "得投点钱\n几百到几千", 2),
        ("需要身份", "有特定条件\n不是人人都行", 3),
    ]
    current_level = {"零门槛": 0, "需要技能": 1, "需要资金": 2, "需要身份": 3}.get(threshold, 0)

    w, h = 520, 160
    step_w = 110
    gap = 12
    start_x = (w - (step_w * 4 + gap * 3)) // 2

    svg = f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="chart-ladder">'
    svg += f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{C["gray_bg"]}"/>'
    svg += f'<text x="{w/2:.0f}" y="24" text-anchor="middle" font-size="14" font-weight="600" fill="{C["text"]}" font-family="sans-serif">门槛分级</text>'

    for i, (name, desc, lv) in enumerate(levels):
        x = start_x + i * (step_w + gap)
        y_top = 48
        step_h = 95
        is_active = (lv <= current_level)

        if lv == current_level:
            fill = C["green"]
            text_c = C["white"]
            desc_c = C["white"]
        elif is_active:
            fill = C["green_light"]
            text_c = C["green"]
            desc_c = C["gray"]
        else:
            fill = C["gray_light"]
            text_c = C["gray"]
            desc_c = C["gray"]

        svg += f'<rect x="{x}" y="{y_top}" width="{step_w}" height="{step_h}" rx="10" fill="{fill}"/>'
        svg += f'<text x="{x + step_w/2:.0f}" y="{y_top + 28}" text-anchor="middle" font-size="15" font-weight="700" fill="{text_c}" font-family="sans-serif">{name}</text>'

        # 当前级别的指示箭头
        if lv == current_level:
            svg += f'<polygon points="{x + step_w/2:.0f},{y_top + step_h - 10} {x + step_w/2 - 8:.0f},{y_top + step_h} {x + step_w/2 + 8:.0f},{y_top + step_h}" fill="{C["green"]}"/>'
            svg += f'<text x="{x + step_w/2:.0f}" y="{y_top + step_h + 16}" text-anchor="middle" font-size="10" font-weight="600" fill="{C["green"]}" font-family="sans-serif">当前项目</text>'

        # 描述行
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            svg += f'<text x="{x + step_w/2:.0f}" y="{y_top + 52 + j*16}" text-anchor="middle" font-size="11" fill="{desc_c}" font-family="sans-serif">{line}</text>'

    svg += "</svg>"
    return svg


def chart_timeline(project):
    """时间线 - 适合短期机会/套利类"""
    events = project.get("timeline", [
        ("今天", "开始操作"),
        ("1周内", "完成设置"),
        ("1个月", "看到收益"),
    ])
    w, h = 520, 130
    start_x = 80
    line_y = 55

    svg = f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="chart-timeline">'
    svg += f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{C["gray_bg"]}"/>'
    svg += f'<text x="{w/2:.0f}" y="22" text-anchor="middle" font-size="14" font-weight="600" fill="{C["text"]}" font-family="sans-serif">操作时间线</text>'

    # 主线
    svg += f'<line x1="{start_x}" y1="{line_y}" x2="{w - 30}" y2="{line_y}" stroke="{C["gray_light"]}" stroke-width="3" stroke-linecap="round"/>'

    n = len(events)
    for i, (time_label, event_label) in enumerate(events):
        x = start_x + (w - start_x - 30) * i / max(n - 1, 1)
        color = C["green"] if i == 0 else (C["blue"] if i == n - 1 else C["orange"])
        svg += f'<circle cx="{x:.0f}" cy="{line_y}" r="8" fill="{C["white"]}" stroke="{color}" stroke-width="3"/>'
        svg += f'<circle cx="{x:.0f}" cy="{line_y}" r="3" fill="{color}"/>'

        # 时间标签（上方）
        svg += f'<text x="{x:.0f}" y="{line_y - 18}" text-anchor="middle" font-size="12" font-weight="700" fill="{color}" font-family="sans-serif">{time_label}</text>'
        # 事件标签（下方）
        svg += f'<text x="{x:.0f}" y="{line_y + 30}" text-anchor="middle" font-size="13" fill="{C["text_soft"]}" font-family="sans-serif">{event_label}</text>'

    svg += "</svg>"
    return svg


def chart_radar(project):
    """雷达图 - 仅用于需要多维对比的项目"""
    dims = [
        ("可行性", 25), ("竞争度", 20), ("成本", 15),
        ("回本", 15), ("扩展", 10), ("自动化", 15),
    ]
    scores = project.get("scores_detail", {})
    keys = ["feasibility", "competition", "cost", "time_to_return", "scalability", "automation"]
    vals = []
    for (name, w), k in zip(dims, keys):
        v = scores.get(k, 7)
        vals.append((name, float(v)))

    size = 260
    cx, cy, r = size // 2, size // 2, size // 2 - 45
    n = len(vals)

    svg = f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
    # 网格
    for level in range(1, 6):
        lr = r * level / 5
        pts = []
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / n
            pts.append(f"{cx + lr * math.cos(a):.1f},{cy + lr * math.sin(a):.1f}")
        svg += f'<polygon points="{" ".join(pts)}" fill="none" stroke="{C["gray_light"]}" stroke-width="0.8"/>'

    # 轴线
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / n
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(a):.1f}" y2="{cy + r * math.sin(a):.1f}" stroke="{C["gray_light"]}" stroke-width="0.8"/>'

    # 数据区
    data_pts = []
    for i, (_, sv) in enumerate(vals):
        a = -math.pi / 2 + 2 * math.pi * i / n
        d = r * sv / 10
        data_pts.append(f"{cx + d * math.cos(a):.1f},{cy + d * math.sin(a):.1f}")
    svg += f'<polygon points="{" ".join(data_pts)}" fill="rgba(16,185,129,0.12)" stroke="{C["green"]}" stroke-width="2"/>'

    # 数据点
    for i, (_, sv) in enumerate(vals):
        a = -math.pi / 2 + 2 * math.pi * i / n
        d = r * sv / 10
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{C["green"]}"/>'

    # 标签
    for i, (name, _) in enumerate(vals):
        a = -math.pi / 2 + 2 * math.pi * i / n
        lx = cx + (r + 32) * math.cos(a)
        ly = cy + (r + 32) * math.sin(a)
        svg += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="10.5" fill="{C["gray"]}" font-family="sans-serif">{name}</text>'

    # 中心分数
    avg = sum(v[1] for v in vals) / n
    svg += f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" font-size="26" font-weight="800" fill="{C["green"]}" font-family="sans-serif">{avg:.1f}</text>'
    svg += f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="10" fill="{C["gray"]}" font-family="sans-serif">综合</text>'
    svg += "</svg>"
    return svg


def pick_chart(project):
    """根据项目类型自动选择合适的图表"""
    chart_type = project.get("chart_type", "auto")
    if chart_type == "auto":
        threshold = project.get("threshold", "零门槛")
        category = project.get("category", "")
        # 有收益范围→收益条
        if project.get("earn_low") and project.get("earn_high"):
            chart_type = "earnings"
        # 需要多维对比→雷达
        elif threshold in ("需要技能", "需要资金"):
            chart_type = "radar"
        # 套利/短期→时间线
        elif "套利" in category or "短期" in category:
            chart_type = "timeline"
        # 默认→门槛阶梯
        else:
            chart_type = "ladder"

    if chart_type == "earnings":
        return chart_earnings_bar(project)
    elif chart_type == "ladder":
        return chart_threshold_ladder(project)
    elif chart_type == "timeline":
        return chart_timeline(project)
    else:
        return chart_radar(project)


# ============================================================
# 内容构建
# ============================================================

def build_section_verdict(project):
    """老兵判断 - 开门见山，直接下判断"""
    verdict = project.get("verdict", "")
    timing = project.get("timing", "")
    if not verdict:
        return ""
    timing_label = {"红利期": "红利期", "稳健期": "稳健期", "尾声": "接近尾声", "持续": "持续有效"}.get(timing, "")
    timing_badge = ""
    if timing_label:
        color = C["green"] if timing in ("红利期", "持续") else (C["orange"] if timing == "稳健期" else C["red"])
        timing_badge = f'<span class="timing-badge" style="background:{color}15;color:{color}">{timing_label}</span>'
    return f'''
    <div class="sec-verdict">
        <div class="verdict-inner">
            <span class="verdict-icon">&#9889;</span>
            <div class="verdict-content">
                <span class="verdict-text">{verdict}</span>
                {timing_badge}
            </div>
        </div>
    </div>'''


def build_section_quick(project):
    """30秒看懂"""
    quick = project.get("quick_view", project.get("summary", ""))
    if not quick:
        return ""
    return f'''
    <div class="sec-quick">
        <div class="sec-label">30秒看懂</div>
        <p class="quick-text">{quick}</p>
    </div>'''


def build_section_cando(project):
    """能不能搞 - 明确划线"""
    suitable = project.get("suitable", [])
    not_suitable = project.get("not_suitable", [])

    if isinstance(suitable, str):
        # 从旧数据格式转换
        if "有海外" in suitable or "海外身份" in suitable:
            suitable = []
            not_suitable = ["没有海外身份或银行账户", "信用记录不能太差"]
        else:
            suitable = [suitable]

    if isinstance(not_suitable, str):
        not_suitable = [not_suitable]

    return f'''
    <div class="sec-cando">
        <div class="sec-label">能不能搞</div>
        <div class="cando-grid">
            <div class="cando-col cando-yes">
                <div class="cando-col-title">&#9989; 你可以，如果你——</div>
                <ul>
                    {"".join(f'<li>{s}</li>' for s in suitable) if suitable else '<li>大多数人都可以试试</li>'}
                </ul>
            </div>
            <div class="cando-col cando-no">
                <div class="cando-col-title">&#10060; 先别碰，如果你——</div>
                <ul>
                    {"".join(f'<li>{s}</li>' for s in not_suitable) if not_suitable else '<li>暂无明确限制</li>'}
                </ul>
            </div>
        </div>
    </div>'''


def build_section_chart(project):
    """图表区"""
    chart_svg = pick_chart(project)
    return f'''
    <div class="sec-chart">
        {chart_svg}
    </div>'''


def build_section_howto(project):
    """怎么上手 - 关键节点，不是百科"""
    steps = project.get("how_to", project.get("steps", []))
    if not steps:
        return ""
    items = []
    for i, s in enumerate(steps[:4], 1):
        items.append(f'''
        <div class="howto-step">
            <span class="howto-num">{i:02d}</span>
            <p class="howto-text">{s}</p>
        </div>''')
    return f'''
    <div class="sec-howto">
        <div class="sec-label">怎么上手</div>
        <div class="howto-list">
            {"".join(items)}
        </div>
    </div>'''


def build_section_traps(project):
    """坑在哪 - 真正的坑，不是官方风险"""
    traps = project.get("traps", project.get("risk", ""))
    if not traps:
        return ""
    if isinstance(traps, str):
        traps = [traps]
    items = "".join(f'<li>{t}</li>' for t in traps)
    return f'''
    <div class="sec-traps">
        <div class="sec-label">&#9888;&#65039; 坑在哪</div>
        <ul class="trap-list">{items}</ul>
    </div>'''


def build_section_attitude(project):
    """我的态度 - 一句话，敢下结论"""
    attitude = project.get("attitude", "")
    if not attitude:
        return ""
    return f'''
    <div class="sec-attitude">
        <div class="attitude-bar">
            <span class="attitude-label">我的态度：</span>
            <span class="attitude-text">{attitude}</span>
        </div>
    </div>'''


# ============================================================
# HTML 模板
# ============================================================

def build_post_html(projects, date_str, hook_line=""):
    """构建单日博客HTML"""
    today = datetime.now()
    date_display = f"{today.year}年{today.month}月{today.day}日"

    if not hook_line:
        hook_line = f"今天看了{len(projects)}个项目，选了{sum(1 for p in projects if p.get('score', 0) >= 7)}个值得聊的。"

    cards = []
    for p in projects:
        title = p.get("title", "")
        category = p.get("category", "")
        threshold = p.get("threshold", "零门槛")
        score = p.get("score", 7)

        # 分数颜色
        sc = C["green"] if score >= 7.5 else (C["orange"] if score >= 6 else C["red"])

        card = f'''
        <article class="project-card">
            <div class="pc-top">
                <div class="pc-badges">
                    <span class="badge-category">{category}</span>
                    <span class="badge-threshold threshold-{threshold.replace("零门槛","zero").replace("需要技能","skill").replace("需要资金","capital").replace("需要身份","identity")}">{threshold}</span>
                </div>
                <div class="pc-score-box">
                    <span class="pc-score-num" style="color:{sc}">{score:.1f}</span>
                    <span class="pc-score-unit">分</span>
                </div>
            </div>

            <h2 class="pc-title">{title}</h2>

            {build_section_verdict(p)}
            {build_section_quick(p)}
            {build_section_cando(p)}
            {build_section_chart(p)}
            {build_section_howto(p)}
            {build_section_traps(p)}
            {build_section_attitude(p)}
        </article>'''
        cards.append(card)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{BRAND} - {date_display} 全网赚钱机会深度扫描">
    <title>{BRAND} · {date_display} | 帮散户找到真机会</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container header-row">
            <div>
                <h1 class="brand">{BRAND}</h1>
                <p class="tagline">{TAGLINE}</p>
            </div>
            <span class="date-badge">{date_display}</span>
        </div>
    </header>

    <main class="container">
        <section class="day-hook">
            <p>{hook_line}</p>
        </section>

        <section class="projects-list">
            {"".join(cards)}
        </section>

        <section class="day-closing">
            <p>以上。这些都是扫描器从全网筛出来的项目，我挑了几个值得说的。</p>
            <p>记住：看分析是为了自己做判断，不是别人说行你就冲。尤其是要花钱的，多用几秒钟想想。</p>
        </section>

        <section class="disclaimer">
            <p>黑灯工厂自动化出品 · 老兵人工把关 · 仅供参考不构成投资建议</p>
        </section>
    </main>

    <footer class="site-footer">
        <p>归灯序 &mdash; 帮散户避开坑，找到真机会</p>
    </footer>
</body>
</html>'''

    return html


def build_index_html():
    """首页"""
    posts = sorted(POSTS_DIR.glob("*.html"), reverse=True)
    now = datetime.now()

    items = "".join(
        f'<li><a href="posts/{p.name}">{p.stem.replace("post_", "").replace("-", "年", 1).replace("-", "月")}日</a></li>'
        for p in posts[:30]
    ) if posts else '<li class="empty">内容即将上线</li>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{BRAND} - 全网自动扫描，帮散户找到真机会">
    <title>{BRAND} · 黑灯工厂</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header-index">
        <div class="container header-center">
            <h1 class="brand-index">{BRAND}</h1>
            <p class="tagline-index">{TAGLINE}</p>
            <p class="factory-desc">全自动扫描工厂 &middot; 关灯也能自己转</p>
        </div>
    </header>
    <main class="container">
        <section class="intro">
            <p>每天自动扫描全网赚钱机会——不是教你发财，是帮你看清楚。</p>
            <p>12个领域、100+关键词、30+平台，AI采集+老兵把关。</p>
        </section>
        <section class="archive">
            <h2>往期内容</h2>
            <ul class="post-list">{items}</ul>
        </section>
    </main>
    <footer class="site-footer"><p>归灯序 &mdash; 不保证赚钱，但保证说实话</p></footer>
</body>
</html>'''


# ============================================================
# CSS
# ============================================================

def write_css():
    css = '''/* 归灯序 · 博客样式 v2.0 · 清爽克制 */

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
    --green:#10b981;--green-light:#d1fae5;--green-bg:#ecfdf5;
    --orange:#f59e0b;--orange-light:#fff3cd;
    --red:#ef4444;--red-light:#fee2e2;--red-bg:#fff5f5;
    --blue:#3b82f6;--blue-light:#dbeafe;
    --gray:#6c757d;--gray-light:#e9ecef;--gray-bg:#f8f9fa;
    --text:#1a1a2e;--text-soft:#4a4a6a;--text-muted:#8890a0;
    --radius:14px;--radius-sm:8px;
    --shadow:0 2px 8px rgba(0,0,0,0.06);
}

body{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
    background:#f2f3f7;color:var(--text);line-height:1.75;font-size:16px;
}
.container{max-width:780px;margin:0 auto;padding:0 20px}

/* Header */
.site-header{
    background:rgba(255,255,255,0.94);backdrop-filter:blur(12px);
    border-bottom:1px solid var(--gray-light);padding:16px 0;
    position:sticky;top:0;z-index:100;
}
.header-row{display:flex;justify-content:space-between;align-items:center}
.brand{font-size:20px;font-weight:700;color:var(--text);letter-spacing:.5px}
.tagline{font-size:12px;color:var(--gray);margin-top:1px}
.date-badge{background:var(--orange-light);color:#92400e;padding:5px 14px;border-radius:20px;font-size:13px;font-weight:600}

/* Index Header */
.site-header-index{padding:60px 0 36px;background:linear-gradient(135deg,#fff 0%,#fef9e7 100%);border:none}
.header-center{text-align:center}
.brand-index{font-size:40px;font-weight:800;color:var(--text);margin-bottom:6px}
.tagline-index{font-size:17px;color:var(--text-soft)}
.factory-desc{font-size:14px;color:var(--text-muted);margin-top:8px}
.intro{text-align:center;background:#fff;border-radius:var(--radius);padding:32px;margin:-16px 0 28px;box-shadow:var(--shadow)}
.intro p{font-size:15px;color:var(--text-soft);margin:4px 0}
.archive{background:#fff;border-radius:var(--radius);padding:28px 32px;box-shadow:var(--shadow);margin-bottom:32px}
.archive h2{font-size:18px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--gray-light)}
.post-list{list-style:none}
.post-list li{padding:12px 0;border-bottom:1px solid var(--gray-light)}
.post-list li:last-child{border:none}
.post-list a{color:var(--text);text-decoration:none;font-size:15px;padding:6px 10px;border-radius:var(--radius-sm);display:block;transition:background .15s}
.post-list a:hover{background:var(--gray-bg);color:var(--orange)}
.post-list .empty{color:var(--text-muted);text-align:center;padding:20px}

/* Daily Hook */
.day-hook{background:var(--green);color:#fff;padding:18px 24px;border-radius:var(--radius);margin:24px 0 20px;font-size:15px;line-height:1.7;box-shadow:0 4px 16px rgba(16,185,129,0.18)}
.day-hook p{margin:0}

/* Project Card */
.project-card{
    background:#fff;border-radius:var(--radius);padding:32px;margin-bottom:24px;
    box-shadow:var(--shadow);transition:box-shadow .2s,border-color .2s;
    border:1px solid transparent;
}
.project-card:hover{box-shadow:0 6px 24px rgba(0,0,0,0.10);border-color:var(--gray-light)}

/* Top area */
.pc-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.pc-badges{display:flex;gap:8px;flex-wrap:wrap}
.badge-category{font-size:12px;color:var(--blue);background:var(--blue-light);padding:3px 12px;border-radius:12px;font-weight:500}
.badge-threshold{font-size:12px;padding:3px 12px;border-radius:12px;font-weight:500}
.threshold-zero{background:var(--green-light);color:#065f46}
.threshold-skill{background:var(--orange-light);color:#92400e}
.threshold-capital{background:var(--red-light);color:#991b1b}
.threshold-identity{background:var(--red-light);color:#991b1b}

.pc-score-box{display:flex;align-items:baseline;gap:2px}
.pc-score-num{font-size:40px;font-weight:800;line-height:1}
.pc-score-unit{font-size:14px;color:var(--gray)}

.pc-title{font-size:21px;font-weight:700;color:var(--text);margin-bottom:18px;line-height:1.4}

/* Section Common */
.sec-label{font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.sec-label::before{content:'';display:inline-block;width:4px;height:14px;background:var(--green);border-radius:2px}

/* Verdict */
.sec-verdict{margin-bottom:18px}
.verdict-inner{display:flex;gap:12px;background:var(--green-bg);padding:14px 18px;border-radius:var(--radius-sm);border-left:3px solid var(--green);align-items:flex-start}
.verdict-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.verdict-content{flex:1;display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap}
.verdict-text{font-size:15px;font-weight:600;color:#065f46;line-height:1.6}
.timing-badge{font-size:11px;padding:2px 10px;border-radius:10px;font-weight:600;white-space:nowrap;flex-shrink:0}

/* Quick */
.sec-quick{margin-bottom:18px}
.quick-text{font-size:15px;color:var(--text-soft);line-height:1.8}

/* Can/Can't Do */
.sec-cando{margin-bottom:20px}
.cando-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.cando-col{padding:16px 18px;border-radius:var(--radius-sm);font-size:14px}
.cando-yes{background:var(--green-bg)}
.cando-no{background:var(--red-bg)}
.cando-col-title{font-weight:700;margin-bottom:8px;font-size:13px}
.cando-col ul{list-style:none;padding:0}
.cando-col li{padding:3px 0 3px 12px;position:relative;line-height:1.7;font-size:13px}
.cando-col li::before{content:'\u2022';position:absolute;left:0;color:var(--gray)}
.cando-yes li::before{color:var(--green)}
.cando-no li::before{color:var(--red)}

/* Chart */
.sec-chart{margin-bottom:20px;text-align:center}
.sec-chart svg{max-width:100%;height:auto}

/* How-to */
.sec-howto{margin-bottom:20px}
.howto-list{display:flex;flex-direction:column;gap:10px}
.howto-step{display:flex;gap:14px;align-items:flex-start}
.howto-num{flex-shrink:0;width:32px;height:32px;background:var(--gray-bg);color:var(--text);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;font-family:monospace}
.howto-text{font-size:14px;color:var(--text-soft);line-height:2.2;padding-top:3px}

/* Traps */
.sec-traps{margin-bottom:20px}
.trap-list{list-style:none;padding:0}
.trap-list li{padding:8px 12px 8px 22px;position:relative;line-height:1.7;font-size:14px;color:var(--text-soft)}
.trap-list li::before{content:'\u26A0';position:absolute;left:0;top:8px;font-size:12px}

/* Attitude */
.sec-attitude{margin-top:8px}
.attitude-bar{display:flex;gap:8px;align-items:center;padding:14px 18px;background:var(--orange-light);border-radius:var(--radius-sm)}
.attitude-label{font-weight:700;font-size:13px;color:#92400e;white-space:nowrap}
.attitude-text{font-size:14px;color:#92400e;line-height:1.6}

/* Closing */
.day-closing{text-align:center;padding:20px 0;font-size:14px;color:var(--text-muted);line-height:1.8}
.disclaimer{text-align:center;padding:16px 0;font-size:12px;color:var(--text-muted);border-top:1px solid var(--gray-light);margin-top:8px}

/* Footer */
.site-footer{text-align:center;padding:20px 0;font-size:13px;color:var(--text-muted)}

@media(max-width:640px){
    .container{padding:0 14px}
    .project-card{padding:22px 18px}
    .cando-grid{grid-template-columns:1fr}
    .pc-score-num{font-size:32px}
    .brand-index{font-size:30px}
}
'''
    (ASSETS_DIR / "style.css").write_text(css, encoding="utf-8")


# ============================================================
# 演示数据
# ============================================================

def demo_projects():
    return [
        {
            "title": "上门喂猫/遛狗 · 宠物托管",
            "category": "零门槛 · 本地服务",
            "score": 8.3,
            "timing": "持续",
            "threshold": "零门槛",
            "chart_type": "earnings",
            "earn_low": 800,
            "earn_high": 4000,
            "earn_unit": "¥",
            "earn_period": "月",
            "verdict": "这不是什么新概念，但今年一线城市的宠物托管需求涨了40%以上。不需要证书、不需要店面、不需要投钱。唯一的门槛是你得不怕猫狗。",
            "quick_view": "在小红书、闲鱼、小区群发布宠物托管服务，按次收费30-80元。节假日需求暴增。一个人最多同时接3-4单，时间自由，比送外卖舒服。",
            "suitable": ["喜欢猫狗，不害怕不抵触", "家里有条件临时接宠物", "在人口密集的小区或城市", "有耐心，不是急脾气"],
            "not_suitable": ["对宠物毛发过敏", "租房且合同不让养", "经常出差不在家", "指望一个月就爆单"],
            "how_to": [
                "先免费帮邻居/朋友托管一次，积累口碑和好评",
                "在小红书发「上门喂猫日记」，实拍记录，不是广告是真实生活",
                "闲鱼和小区群挂信息：明确服务范围、价格、时间",
                "节假日提前1个月开始接单——那是真正的旺季"
            ],
            "traps": [
                "嘴上说喜欢猫狗和真的每天铲屎是两回事，先试一次免费的再决定",
                "有些人会把你当「宠物酒店」要求24小时陪护，说清楚你的服务边界",
                "遇到咬人/有攻击性的宠物，第一次上门一定要有主人在场"
            ],
            "attitude": "最适合被AI替代下来的普通人——宠物不会找AI托管。如果你住在大城市，周末愿意出个门，这比送外卖轻松得多。"
        },
        {
            "title": "Notion模板 · 数字产品销售",
            "category": "数字产品 · 复利收入",
            "score": 7.8,
            "timing": "红利期",
            "threshold": "需要技能",
            "chart_type": "ladder",
            "earn_low": 200,
            "earn_high": 3000,
            "earn_unit": "¥",
            "earn_period": "月",
            "verdict": "做一个模板，卖一百次、一千次。这是真正的「睡后收入」。但前提是你得理解用户到底需要什么——不是你会用Notion就行，是你能把别人的需求翻译成一个好用的工具。",
            "quick_view": "设计一个Notion模板（记账本、项目管理、习惯追踪等），上传到Gumroad或Notion官方市场。一次制作，持续销售。一个好模板可以卖29-99元。",
            "suitable": ["用过Notion或类似工具，不陌生", "有一点审美和排版意识", "愿意花2-3天研究别人的模板", "有耐心——第一批收入来得慢"],
            "not_suitable": ["完全没碰过Notion，也不想学", "指望做出来立刻爆单", "没有任何耐心打磨产品"],
            "how_to": [
                "去Notion市场和Gumroad上翻100个热门模板，看看什么类型最好卖",
                "选一个你最熟悉的领域（记账/学习/工作流），做一个比市面上更好的模板",
                "录一段2分钟的使用视频，比写1000字描述有用得多"
            ],
            "traps": [
                "第一个模板大概率卖不动，不是你的错——是没人知道你的存在，先免费送几个换评价",
                "别做「万能模板」，做得太全反而没人用。做一个痛点就够了",
                "Gumroad抽成10%，定价的时候把这个算进去"
            ],
            "attitude": "如果你本来就熟悉某个领域的流程，把这个流程变成模板卖钱，这是最干净的变现方式。不是割韭菜，是你把自己搞明白的东西产品化了。"
        },
        {
            "title": "朋友圈/社交媒体·AI图片接单",
            "category": "AI工具 · 本地变现",
            "score": 7.5,
            "timing": "红利期",
            "threshold": "零门槛",
            "chart_type": "ladder",
            "verdict": "大部分人只知道AI能聊天，不知道AI能直接帮你赚钱。朋友圈里每天有人需要P图、改证件照、做活动海报。你用AI几秒钟搞定，收个二三十块，双方都高兴。",
            "quick_view": "用即梦/通义万相等国产AI工具（免费），帮身边的人做图片处理：证件照换底色、老照片修复、活动海报、朋友圈封面。在朋友圈和小区群发几个案例，订单就来了。",
            "suitable": ["会用手机的人都能做", "朋友圈有一定人脉", "不怕被朋友说「你怎么干这个」", "有耐心学AI工具（半天够了）"],
            "not_suitable": ["觉得自己做这个是「掉价」", "完全不愿意发朋友圈展示", "对电脑操作完全零基础"],
            "how_to": [
                "花半天学会即梦/通义万相的基本操作（免费的，别花钱）",
                "先免费帮5个朋友做东西，让他们发朋友圈带上你的名字",
                "定个价格：简单修图10-20元，定制海报50-100元"
            ],
            "traps": [
                "免费AI工具有每日使用次数限制，别一天接太多单发现做不完",
                "有些客户会让你「修到满意为止」，提前说清楚免费修改几次",
                "AI生成的内容可能有版权问题，商用的时候注意甄别"
            ],
            "attitude": "这可能是所有项目里启动成本最低的一个。你缺的不是技术，是敢在朋友圈说「我能做这个」的勇气。"
        },
        {
            "title": "小红书 · 技能教程号",
            "category": "内容变现 · 长期积累",
            "score": 7.2,
            "timing": "稳健期",
            "threshold": "需要技能",
            "earn_low": 500,
            "earn_high": 5000,
            "earn_unit": "¥",
            "earn_period": "月",
            "verdict": "你会的东西一定有人想学。不用是专家，你只需要比想学的人多懂一步。小红书现在是知识类内容增长最快的平台。但注意——第一到第三个月可能颗粒无收。",
            "quick_view": "选一个你擅长的技能（Excel、剪视频、做手帐、育儿经验），在小红书发教程笔记，每条讲一个具体的小技巧。积累粉丝后通过接广告、卖课程、一对一咨询变现。",
            "suitable": ["有一项拿得出手的技能，哪怕很小", "表达不磕巴，写东西或拍视频不反感", "能接受3-6个月可能没有收入", "不是追求「快速赚钱」的人"],
            "not_suitable": ["没什么精通的技能也不想学", "文字表达很差且不愿意练", "需要马上就来钱", "怕被人说「你做这个有什么用」"],
            "how_to": [
                "先想清楚：你会的什么东西，别人不会但想学？",
                "拆成50个小知识点，每个发一篇小红书笔记",
                "头30篇不要想变现，专注把内容做好——数据会告诉你什么方向对",
            ],
            "traps": [
                "别一上来就卖课——粉丝都没几个，没人买。先免费输出价值",
                "小红书限流很玄学，一篇笔记没流量不代表方向不对，继续发",
                "想清楚你是在做「知识分享」还是「割韭菜」，前者才能长久"
            ],
            "attitude": "不是最快的路，但是最稳的路。如果你确实有技能且愿意花时间和人分享，这个方向能做很久。"
        }
    ]


# ============================================================
# 发布
# ============================================================

def ensure_dirs():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def load_report():
    files = sorted(REPORTS_DIR.glob("publish_*.html"), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return f.read()


def gitee_api_upload(path, content, msg="归灯序自动发布"):
    import urllib.request, urllib.error

    api = f"https://gitee.com/api/v5/repos/{GITEE_USER}/{GITEE_REPO}/contents"
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    sha = None
    try:
        req = urllib.request.Request(f"{api}/{path}?access_token={GITEE_TOKEN}")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            if isinstance(data, dict):
                sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  [WARN] check {path}: {e.code}")

    body = {"access_token": GITEE_TOKEN, "content": encoded, "message": msg}
    if sha:
        body["sha"] = sha

    req = urllib.request.Request(
        f"{api}/{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
        method="PUT" if sha else "POST"
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        print(f"  [OK] {'更新' if sha else '创建'} {path}")
        return True
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] {path}: {e.code}")
        return False


def push_all():
    files = []
    for f in BLOG_DIR.rglob("*"):
        if f.is_file() and ".git" not in str(f):
            rel = str(f.relative_to(BLOG_DIR)).replace("\\", "/")
            files.append((rel, f.read_text(encoding="utf-8")))
    if not files:
        return
    print(f"[INFO] {len(files)} files, uploading via API...")
    ok = sum(1 for p, c in files if gitee_api_upload(p, c))
    print(f"[OK] done: {ok}/{len(files)}")


def main():
    print("=" * 50)
    print(f"  {BRAND} · 黑灯工厂 v2.0")
    print("=" * 50)

    ensure_dirs()
    write_css()
    print("[OK] CSS")

    projects = demo_projects()
    date_str = datetime.now().strftime("%Y-%m-%d")

    hook = "今天4个项目，零门槛的占了3个。被AI替代下来的人，最适合的项目往往不是学新技术，而是做AI做不了的事。"
    post_html = build_post_html(projects, date_str, hook_line=hook)
    post_path = POSTS_DIR / f"post_{date_str}.html"
    post_path.write_text(post_html, encoding="utf-8")
    print(f"[OK] 文章: {post_path.name}")

    (BLOG_DIR / "index.html").write_text(build_index_html(), encoding="utf-8")
    print("[OK] 首页")

    print("\n[INFO] 上传到 Gitee...")
    push_all()
    print(f"\n  ✅ 完成！仓库: https://gitee.com/{GITEE_USER}/{GITEE_REPO}")
    print(f"  本地: {BLOG_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
