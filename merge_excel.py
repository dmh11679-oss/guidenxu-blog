# -*- coding: utf-8 -*-
"""
多表合并工具 —— 把一个目录里的 Excel/CSV 合成一张表
卖给谁：每月要手工把十几个分店/分公司/分月报表粘在一起的行政、运营、电商
解决什么：不再手工复制粘贴（外部真需求里排第一的是「多个 Excel 合并」）

用法:
  python merge_excel.py <目录> [-o 输出.xlsx] [--sheet 工作表名] [--keep-header]
默认: 合并目录下所有 .xlsx/.xls/.csv 的第一个工作表，自动加「来源文件」列，
      只保留第一份文件的表头（其余跳过表头行）。
"""
import os, sys, argparse, datetime
import openpyxl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EXTS = (".xlsx", ".xls", ".csv")


def smart_cast(v):
    """CSV 读进来一律是字符串，直接写进 xlsx 会导致「销量」列变成文本、无法求和。
    这里只把『一看就是数字/日期』的字符串转成真数值，拿不准的一律保留原文（不擅自改数据）。"""
    if v is None:
        return ""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s == "":
        return ""
    # 千分位: 1,200 / -1,200.5
    t = s
    if "," in t:
        import re as _re
        if _re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):
            t = t.replace(",", "")
        else:
            return v  # 含逗号但不是千分位 → 保留原文
    # 前导零视为编码（007 不能变成 7），一律保留文本
    body = t.lstrip("-")
    if body.isdigit() and len(body) > 1 and body.startswith("0"):
        return v
    # 整数/小数
    try:
        if body.isdigit():
            return int(t)
        if _isfloat(t):
            return float(t)
    except Exception:
        pass
    # 日期 2026-08-01 / 2026/08/01 / 2026-08-01 12:30:00
    for fmt, as_date in (("%Y-%m-%d", True), ("%Y/%m/%d", True), ("%Y-%m-%d %H:%M:%S", False)):
        try:
            got = datetime.datetime.strptime(s, fmt)
            return got.date() if as_date else got
        except ValueError:
            continue
    return v


def _isfloat(t):
    try:
        float(t)
        return True
    except ValueError:
        return False


def read_csv_rows(path, raw=False):
    import csv
    rows = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.reader(f):
            rows.append(r if raw else [smart_cast(c) for c in r])
    return rows


def read_xlsx_rows(path, sheet=None):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = []
    for r in ws.iter_rows(values_only=True):
        rows.append(["" if c is None else c for c in r])
    wb.close()
    return rows


def load(path, sheet=None, raw=False):
    if path.lower().endswith(".csv"):
        return read_csv_rows(path, raw=raw)
    return read_xlsx_rows(path, sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="输入目录（或单个文件）")
    ap.add_argument("-o", "--out", default=None, help="输出 xlsx，默认 <目录>/合并结果.xlsx")
    ap.add_argument("--sheet", default=None, help="指定工作表名（默认第一个）")
    ap.add_argument("--keep-header", action="store_true", help="每个文件都保留表头（默认只留第一份）")
    ap.add_argument("--raw", action="store_true", help="CSV 不做数值/日期识别，全部按文本写入")
    a = ap.parse_args()

    out = a.out or os.path.join(a.src if os.path.isdir(a.src) else os.path.dirname(a.src) or ".",
                                "合并结果.xlsx")

    if os.path.isdir(a.src):
        files = [os.path.join(a.src, f) for f in sorted(os.listdir(a.src))
                 if f.lower().endswith(EXTS) and not f.startswith("~$")]
    else:
        files = [a.src]
    files = [f for f in files if os.path.isfile(f)]
    # 输出文件默认就写在输入目录里，第二次跑会把自己也合并进去（行数翻倍）
    out_abs = os.path.abspath(out)
    files = [f for f in files if os.path.abspath(f) != out_abs]
    if not files:
        print("没找到可合并的文件（支持 xlsx/xls/csv）"); return 1

    out = a.out or os.path.join(a.src if os.path.isdir(a.src) else os.path.dirname(a.src) or ".",
                                "合并结果.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "合并结果"

    header_written = False
    total, per_file = 0, []
    for f in files:
        try:
            rows = load(f, a.sheet, raw=a.raw)
        except Exception as e:
            print("跳过 %s（读取失败: %s）" % (os.path.basename(f), str(e)[:60])); continue
        rows = [r for r in rows if any(str(c).strip() for c in r)]
        if not rows:
            continue
        if not header_written:
            ws.append(list(rows[0]) + ["来源文件"]); header_written = True
            body = rows[1:]
        else:
            body = rows if a.keep_header else rows[1:]
        n = 0
        for r in body:
            ws.append(list(r) + [os.path.basename(f)]); n += 1
        total += n
        per_file.append((os.path.basename(f), n))

    wb.save(out)
    print("输出: %s" % out)
    print("合并 %d 个文件，共 %d 行数据" % (len(per_file), total))
    for n, c in per_file:
        print("   %-32s %d 行" % (n[:32], c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
