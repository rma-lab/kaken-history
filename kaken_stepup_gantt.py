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
    .venv/bin/python kaken_stepup_gantt.py     # → output/kaken_stepup_gantt.pdf
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import kaken_gantt as kg
from kaken_stepup import (DATA_DIR, EXCLUDE_FIRST, is_large,
                          pi_projects, researcher_name)

OUT_PATH = Path("output/kaken_stepup_gantt.pdf")


def load_aligned():
    """大型持ちの研究者を、課題年度を相対年に変換して返す（所要年数の短い順）。"""
    researchers = []
    for path in sorted(DATA_DIR.glob("*.xml")):
        erad = path.stem
        projects = [p for p in pi_projects(path, erad)
                    if p["category"] not in EXCLUDE_FIRST]
        if not projects:
            continue
        larges = [p for p in projects if is_large(p)]
        if not larges:
            continue
        origin = larges[0]["start"]            # 基準年（大型初採択の開始年度）
        for p in projects:
            p["start"] -= origin
            p["end"] -= origin
            p["highlight"] = p is larges[0]
        researchers.append({
            "erad": erad,
            "name": researcher_name(path, erad),
            "projects": projects,
            "years_to_large": origin - min(p["start"] + origin for p in projects),
        })
    researchers.sort(key=lambda r: (r["years_to_large"], r["erad"]))
    return researchers


def main():
    researchers = load_aligned()
    year_min, year_max = kg.axis_range(researchers)
    pages = kg.paginate(researchers)

    OUT_PATH.parent.mkdir(exist_ok=True)
    with PdfPages(OUT_PATH) as pdf:
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
                     "研究代表者として初採択した開始年度）。黒枠がその課題。研究代表課題のみ表示。",
                     ha="center", va="bottom", fontsize=6.5, color="#555")
            pdf.savefig(fig)
            plt.close(fig)

    print(f"対象: 大型科研費あり {len(researchers)}人（所要年数の短い順）")
    print(f"相対年の範囲: {year_min:+d} 〜 {year_max:+d}")
    print(f"出力: {OUT_PATH}  （{len(pages)}ページ・A4縦）")


if __name__ == "__main__":
    main()
