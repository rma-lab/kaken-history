#!/usr/bin/env python3
"""大型科研費に未到達の研究者のガントチャート（次の開始年度=相対年0でアライン）。

大型あり群の kaken_stepup_gantt.py に対応する「大型なし群」版。
大型で揃える基準が無いので、代わりに「次に新しい課題が始まる年度」（既定=翌年度）を
相対年0に置き、各研究者の課題履歴をそこにアラインする。
名前の下に「経過N年」（= 基準年 − 最初の科研費の開始年度）を書き、大型到達者の
所要年数（中央値）と比べやすくする。

使い方:
    .venv/bin/python kaken_nolarge_gantt.py jaist
    # → output/kaken_nolarge_gantt_<機関キー>.pdf
"""
import datetime
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import kaken_gantt as kg
from kaken_data import load_researchers
from kaken_inst import key_from_args, paths
from kaken_stepup import EXCLUDE_FIRST, FIRST_YEAR_MIN, is_large


def next_fiscal_year(today=None):
    """次に新しい課題が始まる年度（日本の会計年度=4月開始）。

    例: 2026年7月時点なら現年度は2026、次に新規課題が始まるのは2027年度。
    """
    today = today or datetime.date.today()
    fy = today.year if today.month >= 4 else today.year - 1
    return fy + 1


def load_nolarge_aligned(researchers_in, align_year):
    """大型未到達の研究者を align_year=相対年0 にアライン（経過年の長い順）。

    表示条件は kaken_stepup の集計と同じ（PIのみ・特別研究員奨励費除外・
    declined除外・最初の科研費が FIRST_YEAR_MIN 年度以降）。
    """
    aligned = []
    for r in researchers_in:
        projects = [p for p in r["projects"] if p["category"] not in EXCLUDE_FIRST]
        if not projects:
            continue
        if FIRST_YEAR_MIN is not None and projects[0]["start"] < FIRST_YEAR_MIN:
            continue
        if any(is_large(p) for p in projects):
            continue                       # 大型ありは対象外（そちらは別ガント）
        elapsed = align_year - projects[0]["start"]   # 最初の科研費→基準年の経過年数
        shifted = []
        for p in projects:                 # 元を壊さないよう複製して相対年に
            q = dict(p)
            q["start"] -= align_year
            q["end"] -= align_year
            shifted.append(q)
        aligned.append({
            "erad": r["erad"],
            "name": r.get("name", ""),
            "projects": shifted,
            "elapsed": elapsed,
            "year_label": f"経過{elapsed}年",
        })
    aligned.sort(key=lambda r: (-r["elapsed"], r["erad"]))   # 経過年の長い順
    return aligned


def main():
    key, _ = key_from_args(sys.argv[1:])
    p = paths(key)
    align_year = next_fiscal_year()
    researchers_in, _src = load_researchers(key)
    researchers = load_nolarge_aligned(researchers_in, align_year)
    if not researchers:
        print("対象者なし（大型未到達の研究者がいません）")
        return

    year_min, year_max = kg.axis_range(researchers)
    year_max = max(year_max, 1)            # 基準年(0)とその前後が見えるように
    pages = kg.paginate(researchers)

    p["gantt_nolarge"].parent.mkdir(exist_ok=True)
    with PdfPages(p["gantt_nolarge"]) as pdf:
        for page in pages:
            fig = plt.figure(figsize=(kg.A4_W, kg.A4_H))
            ax = kg.render_page(fig, page, year_min, year_max)
            ticks = [y for y in range(year_min, year_max + 1) if y % 5 == 0]
            ax.set_xticks(ticks)
            ax.set_xticklabels([f"{y:+d}" if y else "0" for y in ticks])
            ax.axvline(0, color="black", linestyle="--", linewidth=0.8, zorder=4)
            fig.text(0.5, 0.018,
                     f"横軸=相対年（0 = {align_year}年度〈次に新しい課題が始まる年度〉）。"
                     "大型科研費に未到達の研究代表者のみ表示。\n"
                     "「経過N年」= 最初の科研費（研究代表者）から基準年までの年数。"
                     f"最初の科研費が{FIRST_YEAR_MIN}年度以降の研究者に限定。",
                     ha="center", va="bottom", fontsize=6.5, color="#555",
                     linespacing=1.5)
            pdf.savefig(fig)
            plt.close(fig)

    print(f"対象: 大型未到達 {len(researchers)}人（経過年の長い順、基準={align_year}年度）")
    print(f"相対年の範囲: {year_min:+d} 〜 {year_max:+d}")
    print(f"出力: {p['gantt_nolarge']}  （{len(pages)}ページ・A4縦）")


if __name__ == "__main__":
    main()
