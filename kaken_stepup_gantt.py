#!/usr/bin/env python3
"""大型科研費の初採択年を基準0にアラインした相対年ガントチャートPDF。

kaken_fetch.py で取得した生涯実績（data/researchers/<erad>.xml）のうち、
大型科研費（kaken_stepup.is_large、PIのみ）を持つ研究者だけを対象に、
各課題の年度から「大型初採択の開始年度」を引いた相対年で横棒を描く。

  - 横軸 = 相対年（…, -5, …, 0, +5, …）。0 が大型初採択の開始年度。
  - 相対年 0 の位置に縦の破線。大型初採択の課題は黒枠で強調。
  - 研究者は所要年数（最初の科研費 → 大型）の短い順に並べる。
  - 表示する課題は集計と同じ条件（PIのみ・特別研究員奨励費除外・declined除外）。

使い方:
    .venv/bin/python kaken_stepup_gantt.py jaist
    .venv/bin/python kaken_stepup_gantt.py fukushima
    # → output/kaken_stepup_gantt_<機関キー>.pdf
"""
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import kaken_gantt as kg
from kaken_data import load_researchers
from kaken_inst import key_from_args, paths
from kaken_stepup import EXCLUDE_FIRST, FIRST_YEAR_MIN, is_large


def load_aligned(researchers_in):
    """大型持ちの研究者を、課題年度を相対年に変換して返す（所要年数の短い順）。

    入力は kaken_data.load_researchers が返す研究者dictのリスト（JSON/XML両対応）。
    """
    aligned = []
    for r in researchers_in:
        projects = [p for p in r["projects"] if p["category"] not in EXCLUDE_FIRST]
        if not projects:
            continue
        if FIRST_YEAR_MIN is not None and projects[0]["start"] < FIRST_YEAR_MIN:
            continue                       # 古い世代は分析対象外（kaken_stepup と同条件）
        larges = [p for p in projects if is_large(p)]
        if not larges:
            continue
        origin = larges[0]["start"]            # 基準年（大型初採択の開始年度）
        years_to_large = origin - projects[0]["start"]   # projects は開始年順
        shifted = []
        for p in projects:                     # 元を壊さないよう複製して相対年に
            q = dict(p)
            q["highlight"] = p is larges[0]
            q["start"] -= origin
            q["end"] -= origin
            shifted.append(q)
        aligned.append({
            "erad": r["erad"],
            "name": r.get("name", ""),
            "projects": shifted,
            "years_to_large": years_to_large,
            "year_label": f"{years_to_large}年",
        })
    aligned.sort(key=lambda r: (r["years_to_large"], r["erad"]))
    return aligned


def main():
    key, _ = key_from_args(sys.argv[1:])
    p = paths(key)
    researchers_in, _src = load_researchers(key)
    researchers = load_aligned(researchers_in)
    year_min, year_max = kg.axis_range(researchers)
    pages = kg.paginate(researchers)

    p["gantt"].parent.mkdir(exist_ok=True)
    with PdfPages(p["gantt"]) as pdf:
        for page in pages:
            fig = plt.figure(figsize=(kg.A4_W, kg.A4_H))
            ax = kg.render_page(fig, page, year_min, year_max)
            # 相対年は範囲が広いので目盛りは5年刻み（+付きラベル）、0に基準線
            ticks = [y for y in range(year_min, year_max + 1) if y % 5 == 0]
            ax.set_xticks(ticks)
            ax.set_xticklabels([f"{y:+d}" if y else "0" for y in ticks])
            ax.axvline(0, color="black", linestyle="--", linewidth=0.8, zorder=4)
            fig.text(0.5, 0.018,
                     "横軸=相対年（0 = 大型科研費〈基盤B/A/S・特別推進・挑戦的(開拓)等〉を"
                     "研究代表者として初採択した開始年度）。\n"
                     "黒枠がその課題。研究代表課題のみ表示。"
                     f"最初の科研費が{FIRST_YEAR_MIN}年度以降の研究者に限定。",
                     ha="center", va="bottom", fontsize=6.5, color="#555",
                     linespacing=1.5)
            pdf.savefig(fig)
            plt.close(fig)

    print(f"対象: 大型科研費あり {len(researchers)}人（所要年数の短い順）")
    print(f"相対年の範囲: {year_min:+d} 〜 {year_max:+d}")
    print(f"出力: {p['gantt']}  （{len(pages)}ページ・A4縦）")


if __name__ == "__main__":
    main()
