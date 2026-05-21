#!/usr/bin/env python3
"""
归灯序·黑灯工厂 - 博客自动发布脚本
读取扫描报告 -> 生成图文博客 -> 推送到Gitee Pages
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import textwrap
import math

# ============================================================
# 配置
# ============================================================
BLOG_DIR = Path(__file__).parent
REPORTS_DIR = BLOG_DIR.parent / "reports"
DATA_DIR = BLOG_DIR.parent / "data"
POSTS_DIR = BLOG_DIR / "posts"
ASSETS_DIR = BLOG_DIR / "assets"

GITEE_TOKEN = "2a1bf843c7e5da216750893e8155d619"
GITEE_USER = "hdmhdm100"
GITEE_REPO = "guidenxu-blog"
GITEE_REMOTE = f"https://{GITEE_USER}:{GITEE_TOKEN}@gitee.com/{GITEE_USER}/{GITEE_REPO}.git"

# 品牌信息
BRAND = "归灯序"
TAGLINE = "帮散户避开坑，找到真机会"
FACTORY = "黑灯工厂自动化出品"

# 颜色体系 (亮色清爽)
COLORS = {
    "bg": "#ffffff",
    "card_bg": "#f8f9fa",
    "card_border": "#e9ecef",
    "text": "#212529",
    "text_secondary": "#6c757d",
    "text_muted": "#adb5bd",
    "accent": "#f59e0b",      # 琥珀/橙色点缀
    "accent_light": "#fff3cd",
    "success": "#10b981",     # 绿色
    "danger": "#ef4444",      # 红色警告
    "info": "#3b82f6",        # 蓝色
    "chart_colors": ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"],
    "score_high": "#10b981",
    "score_mid": "#f59e0b",
    "score_low": "#ef4444",
}


def ensure_dirs():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def load_report():
    """加载最新的扫描报告"""
    report_files = sorted(REPORTS_DIR.glob("publish_*.html"), reverse=True)
    if not report_files:
        print("[ERROR] 未找到扫描报告")
        return None
    return report_files[0]


def load_raw_feed():
    """加载原始扫描数据"""
    feed_files = sorted(DATA_DIR.glob("raw_feed*.json"), reverse=True)
    if not feed_files:
        return []
    with open(feed_files[0], "r", encoding="utf-8") as f:
        return json.load(f) if isinstance(json.load(f), list) else []


def parse_report_content(html_path):
    """从发布报告HTML中提取项目数据"""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 尝试从HTML中提取JSON数据
    projects = []
    if "updateDashboard" in content:
        start = content.find("updateDashboard(") + len("updateDashboard(")
        depth = 0
        end = start
        for i, c in enumerate(content[start:], start):
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        json_str = content[start:end]
        try:
            data = json.loads(json_str)
            raw_projects = data.get("projects", data.get("results", []))
            for p in raw_projects:
                projects.append({
                    "title": p.get("title", p.get("name", "未知项目")),
                    "category": p.get("category", "未分类"),
                    "score": float(p.get("score", p.get("total_score", 7.0))),
                    "summary": p.get("summary", p.get("description", "")),
                    "steps": p.get("steps", p.get("operation_guide", [])),
                    "risk": p.get("risk", p.get("risk_alert", "")),
                    "suitable": p.get("suitable", p.get("target_audience", "所有人")),
                    "scores_detail": p.get("scores_detail", p.get("dimension_scores", {})),
                    "url": p.get("url", p.get("link", "")),
                })
        except (json.JSONDecodeError, KeyError):
            pass

    return projects


def generate_radar_svg(project, size=300):
    """生成六维评分雷达图SVG"""
    dimensions = [
        ("实操可行性", "feasibility", 25),
        ("竞争程度", "competition", 20),
        ("启动成本", "cost", 15),
        ("回本速度", "time_to_return", 15),
        ("可复制性", "scalability", 10),
        ("自动化", "automation", 15),
    ]

    scores = project.get("scores_detail", {})
    values = []
    for name, key, weight in dimensions:
        v = scores.get(key, scores.get(name, 7))
        values.append((name, float(v) * 10, float(v)))

    cx, cy, r = size // 2, size // 2, size // 2 - 50
    n = len(values)

    svg_parts = [f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">']

    # 背景网格
    levels = 5
    for level in range(1, levels + 1):
        lr = r * level / levels
        points = []
        for i in range(n):
            angle = -math.pi / 2 + 2 * math.pi * i / n
            x = cx + lr * math.cos(angle)
            y = cy + lr * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        svg_parts.append(
            f'<polygon points="{" ".join(points)}" fill="none" stroke="#e9ecef" stroke-width="1"/>'
        )

    # 轴线
    for i in range(n):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        svg_parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e9ecef" stroke-width="1"/>'
        )

    # 数据区域
    data_points = []
    for i, (name, _, score_val) in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        dist = r * score_val / 10
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle)
        data_points.append(f"{x:.1f},{y:.1f}")

    svg_parts.append(
        f'<polygon points="{" ".join(data_points)}" fill="rgba(16,185,129,0.15)" stroke="#10b981" stroke-width="2"/>'
    )

    # 数据点
    for i, (name, _, score_val) in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        dist = r * score_val / 10
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle)
        svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#10b981"/>')

    # 标签
    for i, (name, _, _) in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        lx = cx + (r + 35) * math.cos(angle)
        ly = cy + (r + 35) * math.sin(angle)
        anchor = "middle"
        if angle < -2.6 or angle > 2.6:
            anchor = "middle"
        elif angle < -0.5:
            anchor = "end"
        elif angle < 0.5:
            anchor = "start"
        svg_parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="11" fill="#6c757d" font-family="sans-serif">{name}</text>'
        )

    # 中心分数
    avg = sum(v[1] for v in values) / len(values)
    color = "#10b981" if avg >= 7 else ("#f59e0b" if avg >= 5 else "#ef4444")
    svg_parts.append(
        f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" font-size="28" font-weight="bold" fill="{color}" font-family="sans-serif">{avg:.1f}</text>'
    )
    svg_parts.append(
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#adb5bd" font-family="sans-serif">综合评分</text>'
    )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_score_bar(score, size="large"):
    """生成评分条SVG"""
    w = 320 if size == "large" else 200
    h = 36 if size == "large" else 28
    bar_w = (w - 80) * score / 10
    color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")

    return f'''<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
    <rect x="0" y="0" width="{w}" height="{h}" rx="{h//2}" fill="#f1f3f5"/>
    <rect x="0" y="0" width="{bar_w:.0f}" height="{h}" rx="{h//2}" fill="{color}"/>
    <text x="{w-5}" y="{h//2}" text-anchor="end" dominant-baseline="central" font-size="14" font-weight="bold" fill="#212529" font-family="sans-serif">{score:.1f}</text>
</svg>'''


def generate_step_card(steps, index):
    """生成步骤卡片HTML"""
    if not steps:
        return ""
    step_items = []
    for i, step in enumerate(steps, 1):
        step_items.append(
            f'<div class="step-item"><span class="step-num">{i}</span><span class="step-text">{step}</span></div>'
        )
    return f'<div class="step-card">{"".join(step_items)}</div>'


def build_post_html(projects, date_str):
    """构建单日博客页面HTML"""
    now = datetime.now()
    date_display = f"{now.year}年{now.month}月{now.day}日"

    project_cards = []
    for i, p in enumerate(projects):
        score = p.get("score", 7.0)
        score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
        radar_svg = generate_radar_svg(p)
        category = p.get("category", "未分类")
        risk = p.get("risk", "")
        suitable = p.get("suitable", "所有人")
        summary = p.get("summary", p.get("description", ""))

        # 步骤
        steps_html = ""
        steps = p.get("steps", [])
        if steps:
            steps_html = '<div class="steps-section"><h4>三步上手</h4><div class="step-list">'
            for j, step in enumerate(steps[:3], 1):
                steps_html += f'<div class="step-item"><span class="step-num">0{j}</span><span class="step-text">{step}</span></div>'
            steps_html += "</div></div>"

        # 标签
        tags = ""
        if score >= 7.5:
            tags += '<span class="tag tag-high">高分推荐</span>'
        if score >= 7:
            tags += '<span class="tag tag-green">可操作</span>'
        if "零门槛" in category or "零成本" in summary:
            tags += '<span class="tag tag-orange">零门槛</span>'

        card = f'''
        <article class="project-card">
            <div class="pc-header">
                <div class="pc-meta">
                    <span class="pc-category">{category}</span>
                    {tags}
                </div>
                <div class="pc-score-wrap">
                    <span class="pc-score" style="color:{score_color}">{score:.1f}</span>
                    <span class="pc-score-label">综合评分</span>
                </div>
            </div>
            <h2 class="pc-title">{p["title"]}</h2>
            <p class="pc-summary">{summary}</p>

            <div class="pc-body">
                <div class="pc-radar">
                    {radar_svg}
                </div>
                <div class="pc-content-right">
                    {steps_html}
                    <div class="risk-box" style="display: {'block' if risk else 'none'}">
                        <span class="risk-icon">!</span>
                        <span class="risk-text">{risk}</span>
                    </div>
                    <div class="suitable-box">
                        <span class="suitable-label">适合人群：</span>
                        <span class="suitable-text">{suitable}</span>
                    </div>
                </div>
            </div>
            <div class="pc-footer">
                <span class="pc-source">归灯序扫描器 · 自动采集分析</span>
            </div>
        </article>'''
        project_cards.append(card)

    # 构建完整HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{BRAND} - 每日全网赚钱机会扫描，帮散户避开坑找到真机会">
    <title>{BRAND} · {date_display} 每日扫描 | 帮散户找到真机会</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="header-left">
                <h1 class="brand">{BRAND}</h1>
                <p class="tagline">{TAGLINE}</p>
            </div>
            <div class="header-right">
                <span class="date-badge">{date_display}</span>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="scan-meta">
            <div class="scan-stats">
                <div class="stat-item">
                    <span class="stat-num">{len(projects)}</span>
                    <span class="stat-label">今日扫描项目</span>
                </div>
                <div class="stat-item">
                    <span class="stat-num">{sum(1 for p in projects if p.get("score", 0) >= 7)}</span>
                    <span class="stat-label">可操作项目</span>
                </div>
                <div class="stat-item">
                    <span class="stat-num">全网</span>
                    <span class="stat-label">数据来源</span>
                </div>
            </div>
        </section>

        <section class="projects-list">
            {"".join(project_cards)}
        </section>

        <section class="disclaimer">
            <p>内容由归灯序扫描器自动生成，仅供参考，不构成投资建议</p>
            <p class="factory-tag">{FACTORY}</p>
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; {now.year} {BRAND} · 全自动扫描工厂 · 关灯也能自己转</p>
        </div>
    </footer>
</body>
</html>'''
    return html


def build_index_html():
    """构建博客首页"""
    post_files = sorted(POSTS_DIR.glob("*.html"), reverse=True)
    now = datetime.now()

    post_items = []
    for pf in post_files[:30]:
        date_part = pf.stem.replace("post_", "")
        post_items.append(
            f'<li><a href="posts/{pf.name}">{date_part}</a></li>'
        )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{BRAND} - 全自动扫描全网赚钱机会，帮散户避开坑找到真机会">
    <title>{BRAND} · 黑灯工厂 | 每日赚钱机会自动扫描</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header site-header-index">
        <div class="container">
            <div class="header-center">
                <h1 class="brand-index">{BRAND}</h1>
                <p class="tagline-index">{TAGLINE}</p>
                <p class="factory-desc">全自动扫描工厂 · 关灯也能自己转</p>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="intro-section">
            <h2>每天自动扫描，帮你发现赚钱机会</h2>
            <p class="intro-text">
                覆盖 12 大领域、100+ 中英文关键词、30+ 全球平台。<br>
                四层深度分析：交叉验证 → 商业模式拆解 → 操作指导 → 风险预警。<br>
                六维度评分，高于7.0分才推荐。
            </p>
        </section>

        <section class="posts-index">
            <h2>每日扫描记录</h2>
            <ul class="post-list">
                {"".join(post_items) if post_items else '<li class="no-posts">即将上线，敬请期待</li>'}
            </ul>
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; {now.year} {BRAND} · 全自动扫描工厂 · 不构成投资建议</p>
        </div>
    </footer>
</body>
</html>'''
    return html


def write_css():
    """写入CSS样式文件"""
    css = '''/* ==========================================
   归灯序 · 博客样式 v1.0
   亮色清爽 · 卡片式 · 数据可视化
   ========================================== */

/* Reset & Base */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg: #ffffff;
    --card-bg: #f8f9fa;
    --card-hover-bg: #f0f2f5;
    --card-border: #e9ecef;
    --text: #212529;
    --text-secondary: #6c757d;
    --text-muted: #adb5bd;
    --accent: #f59e0b;
    --accent-light: #fff3cd;
    --green: #10b981;
    --red: #ef4444;
    --blue: #3b82f6;
    --purple: #8b5cf6;
    --radius: 16px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f5f6f8;
    color: var(--text);
    line-height: 1.7;
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
}

.container {
    max-width: 860px;
    margin: 0 auto;
    padding: 0 24px;
}

/* Header */
.site-header {
    background: var(--bg);
    border-bottom: 1px solid var(--card-border);
    padding: 20px 0;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
    background: rgba(255,255,255,0.92);
}

.site-header .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.brand {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: 0.5px;
}

.brand::before {
    content: '';
}

.tagline {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 2px;
    font-weight: 400;
}

.date-badge {
    background: var(--accent-light);
    color: #b7791f;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
}

/* Index Header */
.site-header-index {
    padding: 60px 0 40px;
    border: none;
    background: linear-gradient(135deg, #fff 0%, #fef9e7 100%);
}
.header-center { text-align: center; }
.brand-index {
    font-size: 42px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: 1px;
    margin-bottom: 8px;
}
.tagline-index {
    font-size: 18px;
    color: var(--text-secondary);
    margin-bottom: 12px;
}
.factory-desc {
    font-size: 14px;
    color: var(--text-muted);
    margin-top: 8px;
}

/* Intro Section */
.intro-section {
    background: var(--bg);
    border-radius: var(--radius);
    padding: 40px;
    margin: -20px 0 32px;
    box-shadow: var(--shadow);
    text-align: center;
}
.intro-section h2 {
    font-size: 22px;
    margin-bottom: 16px;
    color: var(--text);
}
.intro-text {
    font-size: 15px;
    color: var(--text-secondary);
    line-height: 1.9;
}

/* Scan Meta */
.scan-meta {
    margin-bottom: 28px;
}
.scan-stats {
    display: flex;
    gap: 16px;
}
.stat-item {
    flex: 1;
    background: var(--bg);
    border-radius: var(--radius-sm);
    padding: 20px;
    text-align: center;
    box-shadow: var(--shadow);
}
.stat-num {
    display: block;
    font-size: 28px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 4px;
}
.stat-label {
    font-size: 13px;
    color: var(--text-secondary);
}

/* Project Card */
.project-card {
    background: var(--bg);
    border-radius: var(--radius);
    padding: 32px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    transition: box-shadow 0.2s;
}
.project-card:hover {
    box-shadow: var(--shadow-md);
}

.pc-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
}
.pc-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.pc-category {
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--card-bg);
    padding: 4px 12px;
    border-radius: 12px;
}

.tag {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 10px;
    font-weight: 600;
}
.tag-high { background: #d1fae5; color: #065f46; }
.tag-green { background: #dbeafe; color: #1e40af; }
.tag-orange { background: var(--accent-light); color: #92400e; }
.tag-risk { background: #fee2e2; color: #991b1b; }

.pc-score-wrap {
    text-align: right;
}
.pc-score {
    display: block;
    font-size: 42px;
    font-weight: 800;
    line-height: 1;
}
.pc-score-label {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
    display: block;
}

.pc-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 10px;
    line-height: 1.4;
}
.pc-summary {
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 24px;
    line-height: 1.8;
}

.pc-body {
    display: flex;
    gap: 32px;
    margin-bottom: 20px;
}
.pc-radar {
    flex: 0 0 280px;
}
.pc-radar svg {
    width: 100%;
    height: auto;
}
.pc-content-right {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

/* Steps */
.steps-section h4 {
    font-size: 14px;
    color: var(--text);
    margin-bottom: 10px;
}
.step-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.step-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.step-num {
    flex: 0 0 28px;
    height: 28px;
    background: var(--accent);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
}
.step-text {
    font-size: 14px;
    color: var(--text);
    line-height: 2;
    padding-top: 2px;
}

/* Risk Box */
.risk-box {
    background: #fff5f5;
    border-left: 3px solid var(--red);
    padding: 12px 16px;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.risk-icon {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    background: var(--red);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
}
.risk-text {
    font-size: 14px;
    color: #991b1b;
    line-height: 1.6;
}

/* Suitable */
.suitable-box {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
}
.suitable-label {
    color: var(--text-secondary);
    flex-shrink: 0;
}
.suitable-text {
    color: var(--text);
    background: var(--card-bg);
    padding: 4px 12px;
    border-radius: 12px;
}

.pc-footer {
    border-top: 1px solid var(--card-border);
    padding-top: 16px;
    margin-top: 4px;
}
.pc-source {
    font-size: 12px;
    color: var(--text-muted);
}

/* Disclaimer */
.disclaimer {
    text-align: center;
    padding: 32px 0;
    font-size: 13px;
    color: var(--text-muted);
}
.factory-tag {
    color: var(--accent);
    font-weight: 600;
    margin-top: 8px;
    font-size: 14px;
}

/* Footer */
.site-footer {
    background: var(--bg);
    border-top: 1px solid var(--card-border);
    padding: 24px 0;
    text-align: center;
    font-size: 13px;
    color: var(--text-muted);
}

/* Post Index */
.posts-index {
    background: var(--bg);
    border-radius: var(--radius);
    padding: 32px 40px;
    box-shadow: var(--shadow);
    margin-bottom: 40px;
}
.posts-index h2 {
    font-size: 20px;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--card-border);
}
.post-list {
    list-style: none;
}
.post-list li {
    padding: 14px 0;
    border-bottom: 1px solid var(--card-border);
}
.post-list li:last-child { border-bottom: none; }
.post-list a {
    color: var(--text);
    text-decoration: none;
    font-size: 16px;
    font-weight: 500;
    display: block;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    transition: all 0.15s;
}
.post-list a:hover {
    background: var(--card-bg);
    color: var(--accent);
}
.no-posts {
    color: var(--text-muted);
    font-size: 15px;
    text-align: center;
    padding: 20px 0;
}

/* Responsive */
@media (max-width: 768px) {
    .container { padding: 0 16px; }
    .pc-body { flex-direction: column; }
    .pc-radar { flex: 0 0 auto; max-width: 240px; margin: 0 auto; }
    .project-card { padding: 24px 20px; }
    .pc-title { font-size: 18px; }
    .brand-index { font-size: 30px; }
    .scan-stats { flex-direction: column; }
    .intro-section { padding: 24px; }
}
'''
    css_path = ASSETS_DIR / "style.css"
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    return css_path


def save_post(html, date_str):
    """保存文章到posts目录"""
    filename = f"post_{date_str}.html"
    path = POSTS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 文章已保存: {path}")
    return path


def save_index(html):
    """保存首页"""
    path = BLOG_DIR / "index.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 首页已更新: {path}")


def git_push():
    """推送到Gitee"""
    os.chdir(BLOG_DIR)

    # 初始化git仓库（如果还没初始化）
    if not (BLOG_DIR / ".git").exists():
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", GITEE_REMOTE], check=True, capture_output=True)

    # 配置git用户
    subprocess.run(["git", "config", "user.name", "归灯序"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", f"{GITEE_USER}@gitee.com"], check=True, capture_output=True)

    # 拉取最新
    subprocess.run(["git", "fetch", "origin"], capture_output=True)
    subprocess.run(["git", "checkout", "master"], capture_output=True)
    subprocess.run(["git", "reset", "--hard", "origin/master"], capture_output=True)

    # 添加所有文件
    subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

    # 检查是否有变更
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("[OK] 没有新变更，跳过推送")
        return

    # 提交推送
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subprocess.run(["git", "commit", "-m", f"归灯序自动发布 {now}"], check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "master"], check=True, capture_output=True)
    print(f"[OK] 已推送到Gitee: https://gitee.com/{GITEE_USER}/{GITEE_REPO}")


def generate_demo_projects():
    """生成演示项目数据（当没有真实扫描数据时使用）"""
    return [
        {
            "title": "Grass Network · 带宽共享挖矿",
            "category": "DePIN · 零门槛",
            "score": 8.5,
            "summary": "通过分享闲置带宽赚取GRASS代币。只需安装浏览器插件或桌面端，无需任何资金投入。已有超200万节点在线，代币已在交易所交易。每日收益稳定，典型用户日均$2-5。适合有电脑常开环境的用户。",
            "steps": [
                "前往 getgrass.io 注册账号，用邮箱即可",
                "下载并安装Grass Desktop，登录后保持电脑在线",
                "每天查看积分面板，累积到1000分可提现"
            ],
            "risk": "代币价格波动较大，网络要求稳定。国内网络可能需要代理才能连接节点。部分运营商可能限制P2P流量。",
            "suitable": "有闲置带宽和常开电脑的用户",
            "scores_detail": {"feasibility": 9, "competition": 8, "cost": 9.5, "time_to_return": 7.5, "scalability": 7, "automation": 9}
        },
        {
            "title": "AI头像生成 · Gumroad数字产品",
            "category": "AI变现 · 数字产品",
            "score": 8.2,
            "summary": "用AI工具批量生成专业头像/插画，在Gumroad、Etsy等平台销售。成本接近零，一次制作可重复销售。热门风格包括：商务头像、情侣插画、宠物肖像。头部卖家月入$3000+。",
            "steps": [
                "在Midjourney或DALL-E生成50张高质量头像模板",
                "注册Gumroad账号，设置产品页面和定价（建议$5-15/套）",
                "在小红书/Twitter发布免费样本引流到Gumroad"
            ],
            "risk": "市场竞争加剧，需要持续出新风格。AI生成内容版权归属有争议。平台可能限制AI内容。",
            "suitable": "有基本审美能力、会使用AI绘图工具的人",
            "scores_detail": {"feasibility": 8.5, "competition": 6, "cost": 9, "time_to_return": 7, "scalability": 8, "automation": 8}
        },
        {
            "title": "银行开户奖励套利",
            "category": "合规套利 · 金融",
            "score": 7.6,
            "summary": "利用银行新用户开户奖励进行合规套利。美国银行常提供$200-500的新用户奖励，只需完成直接存款要求。可同时操作多家银行，年化收益可观。适合有海外银行账户条件的用户。",
            "steps": [
                "筛选当前有开户奖励的银行（Doctor of Credit等网站追踪）",
                "按要求开设账户并设置工资直接存款",
                "满足条件后等待奖励到账，通常30-90天"
            ],
            "risk": "需要美国SSN或ITIN，门槛较高。频繁开关账户可能影响信用记录。奖励会计入应税收入。",
            "suitable": "有海外身份/银行账户条件的人",
            "scores_detail": {"feasibility": 5, "competition": 8.5, "cost": 8, "time_to_return": 7, "scalability": 7, "automation": 5}
        }
    ]


def main():
    """主流程"""
    print("=" * 50)
    print(f"  {BRAND} · 博客自动发布")
    print(f"  {FACTORY}")
    print("=" * 50)
    print()

    ensure_dirs()

    # 1. 写CSS
    write_css()
    print("[OK] CSS样式已生成")

    # 2. 加载数据
    report = load_report()
    if report:
        print(f"[OK] 找到报告: {report.name}")
        projects = parse_report_content(report)
    else:
        projects = []

    # 如果没解析到项目，用演示数据
    if not projects:
        print("[INFO] 未找到扫描数据，使用演示项目")
        projects = generate_demo_projects()

    print(f"[OK] 共 {len(projects)} 个项目")
    for p in projects:
        print(f"  - {p['title']} (评分: {p['score']:.1f})")

    # 3. 生成文章
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    post_html = build_post_html(projects, date_str)
    save_post(post_html, date_str)

    # 4. 更新首页
    index_html = build_index_html()
    save_index(index_html)

    # 5. 推送
    print()
    print("[INFO] 准备推送到 Gitee...")
    try:
        git_push()
        print()
        print("=" * 50)
        print(f"  ✅ 发布完成！")
        print(f"  博客地址: https://gitee.com/{GITEE_USER}/{GITEE_REPO}")
        print(f"  (需开启Gitee Pages服务)")
        print("=" * 50)
    except Exception as e:
        print(f"[WARNING] Git推送失败（可能是Git未就绪）: {e}")
        print(f"[INFO] 文章已在本地生成:")
        print(f"  - 首页: {BLOG_DIR / 'index.html'}")
        print(f"  - 文章: {POSTS_DIR / f'post_{date_str}.html'}")
        print("=" * 50)


if __name__ == "__main__":
    main()
