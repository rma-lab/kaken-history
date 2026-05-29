#!/usr/bin/env python3
"""KAKEN の XML から、研究代表者ごとに科研費の取得履歴をガントチャートで描く。

各課題を1本の横棒（1行）にして、横軸を年度にする。
シンプルに「いつ・何の種目を・いつまで」だけを見せる。

仕様: https://bitbucket.org/niijp/grants_masterxml_kaken,
      https://bitbucket.org/niijp/kaken_definition
  - 研究代表者は summary/member[@role=principal_investigator]
  - 人物の同定は @eradCode（eRad 研究者番号）。番号が無い人は省略。
  - 研究期間は periodOfAward の searchStart/EndFiscalYear（ja優先）。
  - statusCode="declined"（不採択/辞退）は獲得実績ではないので除外。

使い方:
    # 全研究者ぶんを output/ に出力
    .venv/bin/python kaken_gantt.py

    # 氏名(部分一致) / 研究者番号(eRad) で1人だけ描く
    .venv/bin/python kaken_gantt.py 鵜木
    .venv/bin/python kaken_gantt.py 00343187
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Hiragino Sans", "YuGothic", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42      # 日本語をTrueTypeで埋め込み（PDF出力に必須）

LANG = "{http://www.w3.org/XML/1998/namespace}lang"
PI_ROLE = "principal_investigator"
EXCLUDE_STATUS = {"declined"}     # 不採択/辞退は獲得実績でないため除外
XML_DEFAULT = "kaken.nii.ac.jp_2026-05-29_21-44-09.xml"
OUT_DIR = Path("output")


def text(el):
    return el.text.strip() if el is not None and el.text else ""


def find_lang(parent, tag, lang="ja"):
    fallback = None
    for child in parent.findall(tag):
        if child.get(LANG) == lang:
            return child
        if fallback is None:
            fallback = child
    return fallback


def normalize_category(cat):
    """全角カッコ・全角英字の表記ゆれを吸収（例: 基盤研究(Ｃ) → 基盤研究(C)）。"""
    if not cat:
        return cat
    cat = cat.translate(str.maketrans("（）ＡＢＣＳ", "()ABCS"))
    return cat


def parse(src):
    """研究者番号(eradCode) -> {"name","yomi","erad","projects":[...]} を返す。

    研究代表者(PI)は summary 内の member から取る（eradCode はここにある）。
    研究者番号が無い記録（特別研究員奨励費など）は省略する。
    """
    researchers = {}
    for _, el in ET.iterparse(src, events=("end",)):
        if el.tag != "grantAward":
            continue
        summary = find_lang(el, "summary", "ja")
        if summary is not None:
            status_el = summary.find("projectStatus")
            status = status_el.get("statusCode") if status_el is not None else ""
            period = summary.find("periodOfAward")
            start = period.get("searchStartFiscalYear") if period is not None else None
            end = period.get("searchEndFiscalYear") if period is not None else None
            if status not in EXCLUDE_STATUS and start and end:
                project = {
                    "category": normalize_category(text(summary.find("category"))),
                    "start": int(start),
                    "end": int(end),
                    "award_number": el.get("awardNumber", ""),
                    "status": status,
                }
                for m in summary.findall("member"):
                    if m.get("role") != PI_ROLE:
                        continue
                    erad = m.get("eradCode", "")
                    if not erad:                       # 研究者番号が無い人は省略
                        continue
                    r = researchers.setdefault(
                        erad, {"name": "", "yomi": "", "erad": erad, "projects": []})
                    pn = m.find("personalName")
                    if pn is not None and not r["name"]:
                        r["name"] = text(pn.find("fullName"))
                        fam, giv = pn.find("familyName"), pn.find("givenName")
                        r["yomi"] = " ".join(v for v in [
                            fam.get("yomi") if fam is not None else None,
                            giv.get("yomi") if giv is not None else None] if v)
                    r["projects"].append(project)
        el.clear()
    return researchers


# 種目ごとの色。表記は normalize_category 後の名称に合わせる。
CATEGORY_COLORS = {
    "基盤研究(S)": "#6c3483",
    "基盤研究(A)": "#c0392b",
    "基盤研究(B)": "#e67e22",
    "基盤研究(C)": "#27ae60",
    "挑戦的研究(開拓)": "#117a65",
    "挑戦的研究(萌芽)": "#1abc9c",
    "挑戦的萌芽研究": "#48c9b0",
    "若手研究": "#2980b9",
    "若手研究(A)": "#1f618d",
    "若手研究(B)": "#5dade2",
    "研究活動スタート支援": "#7f8c8d",
    "特別研究員奨励費": "#95a5a6",
    "新学術領域研究(研究領域提案型)": "#d35400",
    "学術変革領域研究(A)": "#ca6f1e",
    "学術変革領域研究(B)": "#e74c3c",
    "奨励研究": "#aab7b8",
}
_FALLBACK = ["#34495e", "#9b59b6", "#f39c12", "#16a085", "#2c3e50", "#c39bd3", "#d98880"]


def color_for(cat, _cache={}):
    if cat in CATEGORY_COLORS:
        return CATEGORY_COLORS[cat]
    if cat not in _cache:
        _cache[cat] = _FALLBACK[len(_cache) % len(_FALLBACK)]
    return _cache[cat]


# --- A4縦ページ・レイアウト定数（単位: インチ）---
A4_W, A4_H = 8.27, 11.69
MARGIN = 0.55         # ページ余白
AXIS_LABEL_H = 0.28   # 年度ラベル領域（ページ上下に各1つ）
LABEL_W = 0.85        # グラフ左の氏名・研究者番号の欄（幅）
ROW_INCH = 0.18       # 1課題あたりの行の高さ（小さいほど省スペース）
BAR_H = 1.0           # 行の中でバーが占める割合（1.0=バー同士の隙間ゼロ）
GAP_ROWS = 1.2        # 研究者ブロック間の空き（行数で指定）

# ページ内のプロット領域（インチ）。axes は1ページ1つ。上下に年度ラベル領域を確保。
AX_LEFT = MARGIN + LABEL_W
AX_WIDTH = A4_W - MARGIN - AX_LEFT
AX_BOTTOM = MARGIN + AXIS_LABEL_H
AX_TOP = A4_H - MARGIN - AXIS_LABEL_H
AX_HEIGHT = AX_TOP - AX_BOTTOM
ROWS_PER_PAGE = int(AX_HEIGHT / ROW_INCH)   # 1ページに入れられる行数


def paginate(researchers):
    """研究者をページに詰める。1人のブロックはページを跨がない。

    各研究者は (課題数) 行＋ブロック間 GAP_ROWS 行を占める。行数で詰める。
    返り値: [[researcher, ...], ...]
    """
    pages, cur, cur_rows = [], [], 0.0
    for r in researchers:
        n = len(r["projects"])
        need = n if not cur else n + GAP_ROWS
        if cur and cur_rows + need > ROWS_PER_PAGE:
            pages.append(cur)
            cur, cur_rows = [], 0.0
            need = n
        cur.append(r)
        cur_rows += need
    if cur:
        pages.append(cur)
    return pages


# 横軸の固定範囲（None=データから自動）。AXIS_MAX は「最大開始年+1」を入れる。
AXIS_MIN = None
AXIS_MAX = None


def axis_range(researchers):
    """全研究者共通の横軸 [year_min, year_max] を返す。

    デフォルト: year_min = 全課題の最小開始年, year_max = 最大開始年 + 1。
    """
    starts = [p["start"] for r in researchers for p in r["projects"]]
    year_min = AXIS_MIN if AXIS_MIN is not None else min(starts)
    year_max = AXIS_MAX if AXIS_MAX is not None else max(starts) + 1
    return year_min, year_max


def render_page(fig, page, year_min, year_max):
    """1ページぶん（研究者のリスト）を、共通軸の1つの Axes に描く。

    年度軸（目盛ラベル）はページ上下の2箇所のみ。縦の格子線はページ全体を貫く。
    """
    ax = fig.add_axes([
        AX_LEFT / A4_W, AX_BOTTOM / A4_H,
        AX_WIDTH / A4_W, AX_HEIGHT / A4_H,
    ])

    cursor = ROWS_PER_PAGE          # 上端の行位置から下へ
    for j, r in enumerate(page):
        projects = sorted(r["projects"], key=lambda p: (p["start"], p["end"]))
        n = len(projects)
        top = cursor
        for i, p in enumerate(projects):
            y = top - 0.5 - i                  # 上から古い順
            span = p["end"] - p["start"] + 1
            ax.barh(y, span, left=p["start"], height=BAR_H,
                    color=color_for(p["category"]), edgecolor="white",
                    linewidth=0.5, zorder=3)
            ax.text(p["start"] + 0.1, y, " " + p["category"],
                    ha="left", va="center", color="white", fontsize=6.5,
                    fontweight="bold", zorder=4)
        # 氏名・研究者番号をグラフ左に（このブロックの縦中央）
        ycenter = top - n / 2
        ax.text(-0.012, ycenter, f"{r['name']}\n{r['erad']}",
                transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=8, linespacing=1.4)
        # 研究者の区切り線（次のブロックとの間に黒い横線。氏名欄〜右端まで）
        if j < len(page) - 1:
            sep_y = (top - n) - GAP_ROWS / 2
            ax.plot([-LABEL_W / AX_WIDTH, 1.0], [sep_y, sep_y],
                    transform=ax.get_yaxis_transform(), color="black",
                    linewidth=0.8, clip_on=False, zorder=5)
        cursor -= n + GAP_ROWS

    ax.set_xlim(year_min - 0.3, year_max)
    ax.set_ylim(0, ROWS_PER_PAGE)
    ax.set_yticks([])
    ticks = list(range(year_min, year_max + 1))
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(y) for y in ticks])
    # 年度ラベルを上下の2箇所に
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=True,
                   labelbottom=True, length=2, pad=2, labelsize=7)
    ax.set_axisbelow(True)
    ax.grid(axis="x", linestyle=":", color="#ccc", zorder=0)
    for s in ("right", "left"):
        ax.spines[s].set_visible(False)


def render_pdf(researchers, path):
    """研究者リストをA4縦・複数ページの1つのPDFにまとめて出力する。"""
    from matplotlib.backends.backend_pdf import PdfPages

    year_min, year_max = axis_range(researchers)
    pages = paginate(researchers)
    with PdfPages(path) as pdf:
        for page in pages:
            fig = plt.figure(figsize=(A4_W, A4_H))
            render_page(fig, page, year_min, year_max)
            pdf.savefig(fig)
            plt.close(fig)
    return len(pages)


def main():
    src = XML_DEFAULT
    queries = []
    for arg in sys.argv[1:]:
        if arg.endswith(".xml"):
            src = arg
        else:
            queries.append(arg)

    researchers = parse(src)
    print(f"研究代表者(研究者番号あり・実人数): {len(researchers)}")

    # 指定があればその研究者だけ、無ければ全員。常にヨミ順。
    if queries:
        selected = [r for e, r in researchers.items()
                    if any(q == e or q in r["name"] for q in queries)]
        if not selected:
            print(f"該当なし: {queries}")
            return
    else:
        selected = list(researchers.values())
    selected.sort(key=lambda r: (r["yomi"], r["erad"]))

    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "kaken_gantt.pdf"
    n_pages = render_pdf(selected, path)
    print(f"出力: {path}  （研究者{len(selected)}人 / {n_pages}ページ・A4縦）")


if __name__ == "__main__":
    main()
