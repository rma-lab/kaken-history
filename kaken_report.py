#!/usr/bin/env python3
"""A4縦1枚のレポートPDF（上=説明、下=所要年数ヒストグラム）を生成する。

数値はすべて data/researchers/ の集計から動的に埋め込む。
氏名・研究者番号を含まないため、生成物の中では公開できる体裁。

使い方:
    .venv/bin/python kaken_report.py    # → output/kaken_report.pdf
"""
import datetime
from pathlib import Path

import matplotlib.pyplot as plt

from kaken_gantt import A4_W, A4_H
from kaken_stepup import DATA_DIR, FIRST_YEAR_MIN, analyze, draw_histogram

OUT_PATH = Path("output/kaken_report.pdf")

INK = "#222222"
SUB = "#555555"


def collect():
    """集計を実行してレポートに埋める数値一式を返す。"""
    n_roster = len(list(DATA_DIR.glob("*.xml")))
    rows = [r for r in (analyze(p.stem, p) for p in sorted(DATA_DIR.glob("*.xml"))) if r]
    ys = sorted(r["years_to_large"] for r in rows if r["years_to_large"] is not None)
    return {
        "n_roster": n_roster,
        "n_analyzed": len(rows),
        "n_large": len(ys),
        "n_no_large": len(rows) - len(ys),
        "median": ys[len(ys) // 2],
        "q1": ys[len(ys) // 4],
        "q3": ys[3 * len(ys) // 4],
        "max": ys[-1],
        "n_zero": sum(1 for y in ys if y == 0),
        "ys": ys,
    }


def section(fig, y, title, body, body_size=8.8):
    """見出し＋本文のテキストブロックを描き、次のブロックのy位置を返す。"""
    fig.text(0.09, y, title, fontsize=10.5, fontweight="bold", color=INK, va="top")
    y -= 0.020
    fig.text(0.09, y, body, fontsize=body_size, color=INK, va="top", linespacing=1.75)
    return y - 0.0155 * (body.count("\n") + 1) - 0.022


def main():
    s = collect()
    today = datetime.date.today().isoformat()

    fig = plt.figure(figsize=(A4_W, A4_H))

    # --- タイトル ---
    fig.text(0.5, 0.955, "大型科研費獲得までの道のり", ha="center",
             fontsize=17, fontweight="bold", color=INK)
    fig.text(0.5, 0.933, "— JAIST 研究者の科研費採択履歴にみる、最初の採択から大型種目までの年数 —",
             ha="center", fontsize=10, color=SUB)

    # --- 本文 ---
    y = 0.895
    y = section(fig, y, "■ 問い",
        "大型科研費（基盤研究(B)以上）を獲得した研究者は、研究代表者として最初に科研費を\n"
        "採択されてから何年で大型種目に到達しているか。")

    y = section(fig, y, "■ データと方法",
        f"・母集団: 科研費に参画したことがあり、JAISTに一度でも所属した研究者 {s['n_roster']}人\n"
        "　（KAKEN の機関検索でJAISTの全課題を取得し、研究代表者と JAIST 所属メンバーを収集）。\n"
        "・各研究者について KAKEN（NII）OpenSearch API から生涯の全採択課題を取得（全年代）。\n"
        f"・分析対象: 研究代表者としての採択があり、最初の採択が {FIRST_YEAR_MIN} 年度以降"
        f"（基盤研究制度の開始年）の {s['n_analyzed']}人。\n"
        "・「最初の科研費」= 研究代表者としての初採択（特別研究員奨励費・採択後辞退は除外）。\n"
        "・「大型科研費」= 基盤研究(B)/(A)/(S)・特別推進研究・挑戦的研究(開拓)、および\n"
        "　新学術領域・学術変革領域(A)(B)の領域代表。いずれも研究代表者としての採択のみ。\n"
        "・所要年数 = 大型種目の初採択の開始年度 − 最初の科研費の開始年度。")

    y = section(fig, y, "■ 結果",
        f"・分析対象 {s['n_analyzed']}人のうち、大型科研費の獲得経験があるのは "
        f"{s['n_large']}人（{100 * s['n_large'] / s['n_analyzed']:.0f}%）。\n"
        f"・所要年数は中央値 {s['median']}年（四分位範囲 {s['q1']}–{s['q3']}年、最長 {s['max']}年）。\n"
        f"・「0年」（研究代表者としての初採択がそのまま大型）が {s['n_zero']}人と最頻。\n"
        "　着任前の所属で実績を積んだシニア採用者のパターンで、紐付け不良ではないことを確認済み。\n"
        "・それ以外は 1〜10 年に緩やかな山があり（若手・基盤(C)等を経る積み上げ型）、\n"
        "　10年台後半〜20年超の長い経路も一定数存在する。")

    y = section(fig, y, "■ 留意点",
        f"・大型未獲得の {s['n_no_large']}人はヒストグラムに含まれない。この中には「まだ獲得して\n"
        "　いないだけ」の若手も多く、右打ち切りがある（長い所要年数ほど観測されにくい）。\n"
        "・分担者としての参画は実績に数えていない。不採択・応募行動は KAKEN からは観測できない。\n"
        "・JAIST という一機関の在籍経験者に限った集計であり、一般化には注意。")

    # --- ヒストグラム（下部）---
    ax = fig.add_axes([0.09, 0.085, 0.85, y - 0.13])
    draw_histogram(ax, s["ys"])

    # --- フッタ ---
    fig.text(0.09, 0.018, f"データ: 科学研究費助成事業データベース KAKEN（国立情報学研究所） / 取得・集計: {today}",
             fontsize=7, color=SUB)

    OUT_PATH.parent.mkdir(exist_ok=True)
    fig.savefig(OUT_PATH)
    plt.close(fig)
    print(f"出力: {OUT_PATH}")


if __name__ == "__main__":
    main()
