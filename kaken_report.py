#!/usr/bin/env python3
"""A4縦1枚のレポートPDF（上=説明、下=所要年数ヒストグラム）を生成する。

数値はすべて data/researchers/ の集計から動的に埋め込む。
氏名・研究者番号を含まないため、生成物の中では公開できる体裁。

使い方:
    .venv/bin/python kaken_report.py jaist
    .venv/bin/python kaken_report.py fukushima
    # → output/kaken_report_<機関キー>.pdf
"""
import datetime
import sys

import matplotlib.pyplot as plt

from kaken_gantt import A4_W, A4_H
from kaken_data import load_researchers
from kaken_inst import inst_name, key_from_args, paths
from kaken_stepup import FIRST_YEAR_MIN, analyze_researcher, draw_histogram, median

INK = "#222222"
SUB = "#555555"


def collect(researchers):
    """集計を実行してレポートに埋める数値一式を返す。"""
    n_roster = len(researchers)
    rows = [r for r in (analyze_researcher(x) for x in researchers) if r]
    ys = sorted(r["years_to_large"] for r in rows if r["years_to_large"] is not None)
    ys_pos = [y for y in ys if y > 0]        # 0年組（初代表がいきなり大型）を除く
    from collections import Counter
    counts = Counter(ys)
    return {
        "n_roster": n_roster,
        "n_analyzed": len(rows),
        "n_large": len(ys),
        "n_no_large": len(rows) - len(ys),
        "median": median(ys),
        "median_pos": median(ys_pos) if ys_pos else None,
        "q1": ys[len(ys) // 4],
        "q3": ys[3 * len(ys) // 4],
        "max": ys[-1],
        "n_zero": counts.get(0, 0),
        "mode_count": max(counts.values()),
        "ys": ys,
    }


def section(fig, y, title, body, body_size=8.8):
    """見出し＋本文のテキストブロックを描き、次のブロックのy位置を返す。"""
    fig.text(0.09, y, title, fontsize=10.5, fontweight="bold", color=INK, va="top")
    y -= 0.020
    fig.text(0.09, y, body, fontsize=body_size, color=INK, va="top", linespacing=1.75)
    return y - 0.0155 * (body.count("\n") + 1) - 0.022


def main():
    key, _ = key_from_args(sys.argv[1:])
    name = inst_name(key)
    p = paths(key)
    researchers, source = load_researchers(key)
    s = collect(researchers)
    today = datetime.date.today().isoformat()

    fig = plt.figure(figsize=(A4_W, A4_H))

    # --- タイトル ---
    fig.text(0.5, 0.955, "大型科研費獲得までの道のり", ha="center",
             fontsize=17, fontweight="bold", color=INK)
    fig.text(0.5, 0.933, f"— {name}の研究者の科研費採択履歴にみる、最初の採択から大型種目までの年数 —",
             ha="center", fontsize=10, color=SUB)

    # --- 本文 ---
    y = 0.895
    y = section(fig, y, "■ 問い",
        "大型科研費（基盤研究(B)以上）を獲得した研究者は、研究代表者として最初に科研費を\n"
        "採択されてから何年で大型種目に到達しているか。")

    if source == "json":
        method = (
            f"・母集団: 科研費に参画したことがあり、{name}に一度でも所属した研究者 {s['n_roster']}人\n"
            f"　（KAKEN「研究者をさがす」で研究機関={name}を検索しJSONを取得）。\n"
            "・各研究者のJSONに含まれる生涯の全採択課題（全年代・全機関）を用いる。\n")
    else:
        method = (
            f"・母集団: 科研費に参画したことがあり、{name}に一度でも所属した研究者 {s['n_roster']}人\n"
            f"　（KAKEN の機関検索で{name}の全課題を取得し、研究代表者と所属メンバーを収集）。\n"
            "・各研究者について KAKEN（NII）OpenSearch API から生涯の全採択課題を取得（全年代）。\n")
    y = section(fig, y, "■ データと方法",
        method +
        f"・分析対象: 研究代表者としての採択があり、最初の採択が {FIRST_YEAR_MIN} 年度以降"
        f"（基盤研究制度の開始年）の {s['n_analyzed']}人。\n"
        "・「最初の科研費」= 研究代表者としての初採択（特別研究員奨励費・採択後辞退は除外）。\n"
        "・「大型科研費」= 基盤研究(B)/(A)/(S)・特別推進研究・挑戦的研究(開拓)、および\n"
        "　新学術領域・学術変革領域(A)(B)の領域代表。いずれも研究代表者としての採択のみ。\n"
        "・所要年数 = 大型種目の初採択の開始年度 − 最初の科研費の開始年度。")

    zero_note = f"・「0年」（研究代表者としての初採択がそのまま大型）が {s['n_zero']}人"
    zero_note += "と最頻。\n" if s["n_zero"] == s["mode_count"] else "。\n"
    y = section(fig, y, "■ 結果",
        f"・分析対象 {s['n_analyzed']}人のうち、大型科研費の獲得経験があるのは "
        f"{s['n_large']}人（{100 * s['n_large'] / s['n_analyzed']:.0f}%）。\n"
        f"・所要年数は中央値 {s['median']}年（0年組を含む全体。四分位範囲 {s['q1']}–{s['q3']}年、"
        f"最長 {s['max']}年）。0年組を除くと中央値 {s['median_pos']}年。\n"
        + zero_note +
        "　代表デビューがキャリア中盤以降の研究者（民間企業・海外機関の出身で科研費への応募資格を\n"
        "　得たのが遅い、または分担参加のみで代表応募してこなかった）が、最初の代表応募から\n"
        "　職位相応の種目に採択されるパターン。機関を移ったかどうかは本質ではない。\n"
        "・分布の詳細は下図のとおり（若手・基盤(C)等を経る積み上げ型はプラスの年数側）。")

    y = section(fig, y, "■ 留意点",
        f"・大型未獲得の {s['n_no_large']}人はヒストグラムに含まれない。この中には「まだ獲得して\n"
        "　いないだけ」の若手も多く、右打ち切りがある（長い所要年数ほど観測されにくい）。\n"
        "・分担者としての参画は実績に数えていない。不採択・応募行動は KAKEN からは観測できない。\n"
        f"・{name}という一機関の在籍経験者に限った集計であり、一般化には注意。")

    # --- ヒストグラム（下部）---
    ax = fig.add_axes([0.09, 0.085, 0.85, y - 0.13])
    draw_histogram(ax, s["ys"])

    # --- フッタ ---
    fig.text(0.09, 0.018, f"データ: 科学研究費助成事業データベース KAKEN（国立情報学研究所） / 取得・集計: {today}",
             fontsize=7, color=SUB)

    p["report"].parent.mkdir(exist_ok=True)
    fig.savefig(p["report"])
    plt.close(fig)
    print(f"出力: {p['report']}")


if __name__ == "__main__":
    main()
