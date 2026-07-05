#!/usr/bin/env python3
"""大型科研費（基盤B以上など）の初採択が、最初の科研費から何年後かを集計する。

データ源: kaken_fetch.py で取得した data/researchers/<erad>.xml
（研究者ごとの KAKEN 全件。代表・分担など全ロールを含む）。

定義:
  - 「最初の科研費」= 研究代表者(PI)としての最初の採択。
      分担者は含めない。特別研究員奨励費は除外。declined(採択後辞退)は除外。
  - 「大型科研費」= LARGE_CATEGORIES の種目を PI として初めて採択した課題。
      分担者は含めない。
  - 所要年数 = 大型の開始年度 - 最初の科研費の開始年度。

使い方:
    .venv/bin/python kaken_stepup.py jaist
    .venv/bin/python kaken_stepup.py fukushima
    # → data/<機関キー>/stepup.csv, output/kaken_stepup_hist_<機関キー>.pdf
"""
import csv
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

from kaken_gantt import find_lang, normalize_category, text, PI_ROLE
from kaken_inst import key_from_args, paths

# 「大型科研費」とみなす種目（normalize_category 後の名称）
LARGE_CATEGORIES = {
    "基盤研究(B)",
    "基盤研究(A)",
    "基盤研究(S)",
    "特別推進研究",
    "挑戦的研究(開拓)",
    # 旧種目（1995年度以前の基盤A/B相当）。ベテランの所要年数の過大評価を防ぐ
    "一般研究(A)",
    "一般研究(B)",
}

# 領域型は「領域代表」（総括班 projectType="organizer" の代表）のみ大型とみなす。
# 計画研究・公募研究の代表は含めない。
AREA_LARGE_CATEGORIES = {
    "新学術領域研究(研究領域提案型)",
    "学術変革領域研究(A)",
    "学術変革領域研究(B)",
}
AREA_LARGE_TYPES = {"organizer"}


def is_large(p):
    """課題 p が「大型科研費」（PI前提）かどうか。"""
    if p["category"] in LARGE_CATEGORIES:
        return True
    return (p["category"] in AREA_LARGE_CATEGORIES
            and p["project_type"] in AREA_LARGE_TYPES)

# 「最初の科研費」から除外する種目
EXCLUDE_FIRST = {"特別研究員奨励費"}

# 最初の科研費がこの年度より前の研究者は分析対象外にする。
# 1996 = 基盤研究(A)(B)(C) 制度の開始年。これより古いキャリアは旧制度種目が主で
# eRad 紐付けの信頼性も落ちるため除外（None で無効化）。
FIRST_YEAR_MIN = 1996

EXCLUDE_STATUS = {"declined"}    # 採択後辞退は実績に数えない


def pi_projects(path, erad):
    """1研究者のXMLから、PIとして採択した課題を (開始年順で) 返す。"""
    projects = []
    root = ET.parse(path).getroot()
    for award in root.findall("grantAward"):
        summary = find_lang(award, "summary", "ja")
        if summary is None:
            continue
        status_el = summary.find("projectStatus")
        status = status_el.get("statusCode") if status_el is not None else ""
        if status in EXCLUDE_STATUS:
            continue
        # この研究者が PI の課題のみ（分担者などは含めない）
        is_pi = any(m.get("eradCode") == erad and m.get("role") == PI_ROLE
                    for m in summary.findall("member"))
        if not is_pi:
            continue
        period = summary.find("periodOfAward")
        start = period.get("searchStartFiscalYear") if period is not None else None
        end = period.get("searchEndFiscalYear") if period is not None else None
        if not start:
            continue
        projects.append({
            "category": normalize_category(text(summary.find("category"))),
            "start": int(start),
            "end": int(end) if end else int(start),
            "award_number": award.get("awardNumber", ""),
            "status": status,
            "project_type": award.get("projectType", ""),
        })
    projects.sort(key=lambda p: p["start"])
    return projects


def researcher_name(path, erad):
    """XMLからこの研究者の氏名を1つ拾う。"""
    root = ET.parse(path).getroot()
    for award in root.findall("grantAward"):
        summary = find_lang(award, "summary", "ja")
        if summary is None:
            continue
        for m in summary.findall("member"):
            if m.get("eradCode") == erad:
                pn = m.find("personalName")
                if pn is not None:
                    name = text(pn.find("fullName"))
                    if name:
                        return name
    return ""


def analyze(erad, path):
    """1研究者の行を作る。大型なしの人も返す（large_* は None）。"""
    projects = pi_projects(path, erad)
    firsts = [p for p in projects if p["category"] not in EXCLUDE_FIRST]
    if not firsts:
        return None                       # PI課題なし（分析対象外）
    first = firsts[0]
    if FIRST_YEAR_MIN is not None and first["start"] < FIRST_YEAR_MIN:
        return None                       # 古い世代は分析対象外
    larges = [p for p in firsts if is_large(p)]
    large = larges[0] if larges else None
    before = [p for p in firsts
              if large is None or p["start"] < large["start"]]
    return {
        "erad": erad,
        "name": researcher_name(path, erad),
        "first_year": first["start"],
        "first_category": first["category"],
        "large_year": large["start"] if large else None,
        "large_category": large["category"] if large else None,
        "years_to_large": (large["start"] - first["start"]) if large else None,
        "n_pi_before_large": len(before),
        "categories_before_large": " / ".join(
            f"{p['start']}:{p['category']}" for p in before),
    }


def draw_histogram(ax, ys):
    """所要年数リスト ys のヒストグラムを ax に描く（図の入れ物は呼び出し側）。"""
    from collections import Counter

    counts = Counter(ys)
    xs = list(range(0, max(ys) + 1))
    median = sorted(ys)[len(ys) // 2]

    ax.bar(xs, [counts.get(x, 0) for x in xs], width=0.85,
           color="#34495e", zorder=3)
    ax.axvline(median, color="#c0392b", linestyle="--", linewidth=1.2, zorder=4)
    ax.text(median + 0.3, ax.get_ylim()[1] * 0.95, f"中央値 {median}年",
            color="#c0392b", fontsize=10, va="top")
    ax.set_xlabel("最初の科研費（研究代表者）から大型科研費の初採択までの年数")
    ax.set_ylabel("人数")
    ax.set_title(f"大型科研費までの所要年数（N={len(ys)}）", fontsize=12)
    ax.set_xticks(xs)
    ax.tick_params(labelsize=8)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", color="#ccc", zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def render_histogram(with_large, path):
    """所要年数のヒストグラムPDF。大型未取得の研究者は含めない。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    draw_histogram(ax, [r["years_to_large"] for r in with_large])
    note = ("大型科研費 = 基盤研究(B)/(A)/(S)・特別推進・挑戦的(開拓)・領域代表。"
            "研究代表者としての採択のみ。\n大型未取得の研究者は含まない。")
    if FIRST_YEAR_MIN is not None:
        note += f"最初の科研費が{FIRST_YEAR_MIN}年度以降の研究者に限定。"
    fig.text(0.5, 0.012, note, ha="center", va="bottom", fontsize=7,
             color="#555", linespacing=1.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main():
    key, _ = key_from_args(sys.argv[1:])
    p = paths(key)
    rows = []
    for path in sorted(p["researchers"].glob("*.xml")):
        row = analyze(path.stem, path)
        if row:
            rows.append(row)

    with_large = [r for r in rows if r["large_year"] is not None]
    without = [r for r in rows if r["large_year"] is None]

    p["csv"].parent.mkdir(parents=True, exist_ok=True)
    with open(p["csv"], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"分析対象(PI課題あり・最初の科研費{FIRST_YEAR_MIN}年度以降): {len(rows)}人")
    print(f"  大型あり: {len(with_large)}人 / 大型なし: {len(without)}人")
    print(f"  大型の定義: {sorted(LARGE_CATEGORIES)}")
    print(f"  ＋領域代表(総括班PI): {sorted(AREA_LARGE_CATEGORIES)}")
    print()
    if with_large:
        ys = sorted(r["years_to_large"] for r in with_large)
        mid = ys[len(ys) // 2]
        print(f"最初の科研費 → 大型初採択の所要年数:")
        print(f"  最小 {ys[0]} / 中央値 {mid} / 最大 {ys[-1]} 年")
        # 分布（ヒストグラム風）
        from collections import Counter
        c = Counter(ys)
        for y in range(ys[0], ys[-1] + 1):
            print(f"  {y:3d}年: {'#' * c.get(y, 0)} {c.get(y, '') if c.get(y) else ''}")
    if with_large:
        render_histogram(with_large, p["hist"])
        print(f"\n出力: {p['csv']} / {p['hist']}")
    else:
        print(f"\n出力: {p['csv']}")


if __name__ == "__main__":
    main()
