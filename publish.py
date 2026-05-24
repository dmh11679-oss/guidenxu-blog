#!/usr/bin/env python3
"""
归灯序·黑灯工厂 — 博客发布脚本 v3.0
用法：
    python publish.py post.md                    # MD → HTML → Git push
    python publish.py post.md --dry-run          # 只生成HTML，不push
    python publish.py post.md --skip-gitee       # 只推GitHub
    python publish.py --index-only               # 仅重建首页
    python publish.py --help
"""
import argparse, json, os, sys, subprocess, re
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================
BLOG_DIR = Path(__file__).parent.absolute()
POSTS_DIR = BLOG_DIR / "posts"
ASSETS_DIR = BLOG_DIR / "assets"

GIT_REMOTE_GITHUB = "github"
GIT_REMOTE_GITEE = "origin"

BRAND = "归灯序"
TAGLINE = "帮散户避开坑，找到真机会"

# ============================================================
# 工具函数
# ============================================================

def run(cmd, cwd=None):
    """执行命令，返回 (returncode, stdout, stderr)"""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or BLOG_DIR)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def slug(text):
    """将中文标题转为英文slug"""
    text = re.sub(r'[^\w\u4e00-\u9fff\-]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    # 保留前60个字符
    if len(text) > 60:
        text = text[:60].rstrip('-')
    return text


def parse_md_metadata(md_text):
    """从MD头部提取标题和日期"""
    title = ""
    date_str = datetime.now().strftime("%Y-%m-%d")
    desc = ""

    lines = md_text.strip().split("\n")
    for line in lines[:15]:
        line = line.strip()
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("> ") and "归灯序" in line and "年" in line:
            m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', line)
            if m:
                date_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        elif line.startswith("> ") and not desc:
            desc = line[2:].strip()[:160]

    if not title:
        title = f"归灯序 · {date_str}"

    return {
        "title": title,
        "date": date_str,
        "desc": desc or f"{BRAND} - {date_str} 深度内容",
    }


def md_to_html_body(md_text):
    """极简 Markdown → HTML 转换（处理归灯序文章常用格式）"""
    lines = md_text.split("\n")
    html_lines = []
    in_code_block = False
    in_table = False
    in_list = False

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # 跳过 YAML front matter
        if line == "---" and i == 0:
            i += 1
            while i < len(lines):
                if lines[i].strip() == "---":
                    i += 1
                    break
                i += 1
            continue

        # Code block
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                html_lines.append('<pre><code>')
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            html_lines.append(line)
            i += 1
            continue

        # 分隔线
        if line.strip() == "---":
            html_lines.append("<hr>")
            i += 1
            continue

        # H2
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append(f'<h2>{line[3:].strip()}</h2>')
            i += 1
            continue

        # H3
        if line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h3>{line[4:].strip()}</h3>')
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            # 检查是否多行 blockquote
            bq_lines = [line[2:]]
            j = i + 1
            while j < len(lines) and lines[j].startswith("> "):
                bq_lines.append(lines[j][2:])
                j += 1
            # 检查最后一行是否是归灯序签名
            bq_text = "<br>".join(bq_lines)
            if "归灯序" in bq_text and ("帮散户" in bq_text or "你出时间" in bq_text):
                html_lines.append(f'<blockquote class="signature">{bq_text}</blockquote>')
            else:
                html_lines.append(f"<blockquote>{bq_text}</blockquote>")
            i = j
            continue

        # 表格检测
        if "|" in line and not line.startswith(">"):
            if not in_table:
                # 检查下一行是否是分隔行
                if i + 1 < len(lines) and re.match(r'^\|[\s\-:|]+\|$', lines[i + 1].strip()):
                    in_table = True
                    # Header row
                    headers = [c.strip() for c in line.split("|")[1:-1]]
                    align_row = [c.strip() for c in lines[i + 1].split("|")[1:-1]]

                    html_lines.append('<table class="priority-table"><thead><tr>')
                    for j, h in enumerate(headers):
                        align = ""
                        if j < len(align_row) and align_row[j].startswith(":") and align_row[j].endswith(":"):
                            align = ' style="text-align:center"'
                        elif j < len(align_row) and align_row[j].endswith(":"):
                            align = ' style="text-align:right"'
                        html_lines.append(f"<th{align}>{h}</th>")
                    html_lines.append("</tr></thead><tbody>")
                    i += 2
                    continue

            if in_table:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                html_lines.append("<tr>")
                for c in cells:
                    html_lines.append(f"<td>{c}</td>")
                html_lines.append("</tr>")
                i += 1
                continue
            else:
                # 普通文本中的 |
                pass

        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

        # 无序列表
        if re.match(r'^- ', line):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
            i += 1
            continue

        if re.match(r'^\d+\. ', line):
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
            content = re.sub(r'^\d+\. ', '', line)
            html_lines.append(f"<li>{content}</li>")
            i += 1
            continue

        # 结束列表
        if in_list and line == "":
            if in_list:
                tag = "</ul>" if html_lines and html_lines[-1].startswith("<li>") else ""
                if not tag:
                    # 判断是 ul 还是 ol
                    for h in reversed(html_lines):
                        if h.startswith("<ul>"):
                            tag = "</ul>"
                            break
                        elif h.startswith("<ol>"):
                            tag = "</ol>"
                            break
                if tag:
                    html_lines.append(tag)
                in_list = False
            i += 1
            continue

        # 空行
        if line == "":
            html_lines.append("")
            i += 1
            continue

        # 普通段落
        # 处理行内格式
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
        line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', line)
        html_lines.append(f"<p>{line}</p>")
        i += 1

    # 清理未闭合标签
    if in_list:
        html_lines.append("</ul>")
    if in_table:
        html_lines.append("</tbody></table>")
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def build_post_html(md_text, metadata):
    """构建完整文章HTML"""
    body = md_to_html_body(md_text)
    title = metadata["title"]
    date_str = metadata["date"]
    desc = metadata["desc"]

    # 中文日期显示
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = f"{d.year}年{d.month}月{d.day}日"
    except:
        date_display = date_str

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{desc}">
    <title>{title} · 归灯序 | 帮散户找到真机会</title>
    <link rel="stylesheet" href="../assets/style.css">
    <style>
        /* === 文章内页样式 === */
        .article-header{{text-align:center;padding:36px 20px 20px;margin-bottom:20px}}
        .article-header h1{{font-size:26px;font-weight:800;color:#1a1a2e;margin-bottom:10px;line-height:1.4}}
        .article-header .meta{{font-size:14px;color:#8890a0}}
        .article-body{{background:#fff;border-radius:14px;padding:36px 40px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:24px}}
        .article-body h2{{font-size:20px;font-weight:700;color:#1a1a2e;margin:32px 0 12px;padding-bottom:8px;border-bottom:2px solid #e9ecef}}
        .article-body h2:first-child{{margin-top:0}}
        .article-body h3{{font-size:17px;font-weight:600;color:#1a1a2e;margin:24px 0 8px}}
        .article-body p{{font-size:15px;color:#4a4a6a;line-height:1.85;margin-bottom:14px}}
        .article-body ul,.article-body ol{{padding-left:22px;margin-bottom:16px}}
        .article-body li{{font-size:15px;color:#4a4a6a;line-height:1.85;margin-bottom:6px}}
        .article-body blockquote{{background:#f8f9fa;border-left:3px solid #f59e0b;padding:12px 18px;margin:16px 0;border-radius:0 8px 8px 0;font-size:14px;color:#6c757d}}
        .article-body blockquote.signature{{background:transparent;border-left:3px solid #10b981;font-size:13px;color:#8890a0;font-style:italic;margin-top:32px}}
        .article-body code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:14px;color:#e11d48}}
        .article-body pre{{background:#1e293b;color:#e2e8f0;padding:20px;border-radius:10px;overflow-x:auto;margin:16px 0}}
        .article-body pre code{{background:none;color:inherit;padding:0}}
        .article-body a{{color:#3b82f6;text-decoration:underline}}
        .article-body hr{{border:none;border-top:1px solid #e9ecef;margin:32px 0}}
        .article-body table{{width:100%;border-collapse:collapse;margin:16px 0}}
        .article-body th{{background:#f1f5f9;padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#4a4a6a}}
        .article-body td{{padding:10px 14px;border-bottom:1px solid #e9ecef;font-size:14px;color:#4a4a6a}}
        .disclaimer-box{{background:#fff3cd;border:1px solid #f59e0b;border-radius:12px;padding:16px 20px;margin-bottom:24px}}
        .disclaimer-box p{{font-size:14px;color:#92400e;margin:4px 0}}
        .step-section{{background:#f8f9fa;border-radius:10px;padding:20px 24px;margin:16px 0}}
        .back-link{{text-align:center;padding:20px 0}}
        .back-link a{{color:#3b82f6;text-decoration:none;font-size:14px}}
        @media(max-width:640px){{.article-body{{padding:22px 18px}}.article-header h1{{font-size:22px}}}}
    </style>
</head>
<body>
    <header class="article-header">
        <h1>{title}</h1>
        <p class="meta">{BRAND} · {date_display}</p>
    </header>

    <main class="container">
        <div class="article-body">
{body}
        </div>
        <div class="back-link">
            <a href="../index.html">&larr; 回到归灯序首页</a>
        </div>
    </main>

    <footer class="site-footer">
        <p>归灯序 &mdash; 不保证赚钱，但保证说实话</p>
    </footer>
</body>
</html>'''


def build_index_html():
    """重建首页 index.html"""
    posts = sorted(
        [p for p in POSTS_DIR.glob("post_*.html")],
        reverse=True
    )

    items = ""
    for p in posts:
        stem = p.stem.replace("post_", "")
        # 尝试读取标题
        title = stem
        try:
            content = p.read_text(encoding="utf-8")
            m = re.search(r'<h1>(.+?)</h1>', content)
            if m:
                title = m.group(1)
            else:
                m = re.search(r'<title>(.+?)</title>', content)
                if m:
                    title = m.group(1).replace(" · 归灯序 | 帮散户找到真机会", "")
        except:
            pass
        # 日期格式化
        try:
            d = datetime.strptime(stem[:10], "%Y-%m-%d")
            date_label = f"{d.month}月{d.day}日"
        except:
            date_label = stem[:10]
        items += f'\n                    <li><a href="posts/{p.name}">{date_label} — {title}</a></li>'

    if not items:
        items = '\n                    <li class="empty">内容即将上线</li>'

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
            <ul class="post-list">{items}
                </ul>
        </section>
    </main>
    <footer class="site-footer"><p>归灯序 &mdash; 不保证赚钱，但保证说实话</p></footer>
</body>
</html>'''


def ensure_dirs():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 主流程
# ============================================================

def publish(md_path, dry_run=False, skip_gitee=False):
    """MD文件 → HTML → Git Push"""
    md_path = Path(md_path)
    if not md_path.exists():
        print(f"[ERROR] 文件不存在: {md_path}")
        return 1

    ensure_dirs()

    # 1. 读取 MD
    print(f"[1/5] 读取: {md_path.name}")
    md_text = md_path.read_text(encoding="utf-8")

    # 2. 提取元数据
    metadata = parse_md_metadata(md_text)
    date_str = metadata["date"]
    print(f"  标题: {metadata['title']}")
    print(f"  日期: {date_str}")

    # 3. 生成 HTML
    print(f"[2/5] 生成 HTML...")
    html = build_post_html(md_text, metadata)

    slug_name = slug(metadata["title"])
    html_filename = f"post_{date_str}.html"
    html_path = POSTS_DIR / html_filename
    html_path.write_text(html, encoding="utf-8")
    print(f"  → posts/{html_filename}")

    # 4. 更新首页
    print(f"[3/5] 更新首页...")
    index_html = build_index_html()
    (BLOG_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  → index.html 已更新")

    if dry_run:
        print(f"\n[DONE] 干跑模式，HTML已生成但未推送。")
        print(f"  文章: {html_path}")
        print(f"  首页: {BLOG_DIR / 'index.html'}")
        return 0

    # 5. Git Push
    print(f"[4/5] Git add + commit...")
    code, out, err = run("git add -A")
    if code != 0:
        print(f"  git add 失败: {err}")
        return 1

    commit_msg = f"发布: {metadata['title']} ({date_str})"
    code, out, err = run(f'git commit -m "{commit_msg}"')
    if code != 0:
        # 可能是 nothing to commit
        if "nothing to commit" in err or "nothing to commit" in out:
            print("  (无变更，跳过 commit)")
        else:
            print(f"  git commit 失败: {err}")
            return 1

    # 推 GitHub
    print(f"[5/5] 推送到 GitHub Pages...")
    code, out, err = run(f"git push {GIT_REMOTE_GITHUB} master")
    if code == 0:
        print(f"  ✅ GitHub Pages: https://dmh11679-oss.github.io/guidenxu-blog/")
    else:
        print(f"  ⚠️ GitHub push 失败: {err[:200]}")

    # 推 Gitee（可选）
    if not skip_gitee:
        code, out, err = run(f"git push {GIT_REMOTE_GITEE} master")
        if code == 0:
            print(f"  ✅ Gitee: https://gitee.com/hdmhdm100/guidenxu-blog")
        else:
            print(f"  ⚠️ Gitee push 失败: {err[:200]}")

    print(f"\n=== 发布完成 ===")
    print(f"  本地: {html_path}")
    print(f"  线上: https://dmh11679-oss.github.io/guidenxu-blog/posts/{html_filename}")
    return 0


def index_only():
    """仅重建首页"""
    ensure_dirs()
    index_html = build_index_html()
    (BLOG_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("[OK] index.html 已重建")


def main():
    parser = argparse.ArgumentParser(
        description="归灯序·博客发布脚本 v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python publish.py article.md               # MD → HTML → Git push
  python publish.py article.md --dry-run     # 只生成HTML，不push
  python publish.py article.md --skip-gitee  # 只推GitHub
  python publish.py --index-only             # 仅重建首页
        """
    )
    parser.add_argument("md_file", nargs="?", help="Markdown 文章文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅生成HTML，不执行Git操作")
    parser.add_argument("--skip-gitee", action="store_true", help="跳过Gitee推送")
    parser.add_argument("--index-only", action="store_true", help="仅重建首页index.html")
    args = parser.parse_args()

    if args.index_only:
        return index_only()

    if not args.md_file:
        parser.print_help()
        return 1

    return publish(args.md_file, dry_run=args.dry_run, skip_gitee=args.skip_gitee)


if __name__ == "__main__":
    sys.exit(main())
