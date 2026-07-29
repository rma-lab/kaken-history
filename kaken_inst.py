#!/usr/bin/env python3
"""機関ごとの設定とデータ配置。

分析対象の機関を増やすときは INSTITUTIONS にキーと正式名称を足す。
データは data/<キー>/ 以下に置く（すべて git 除外）。
"""
from pathlib import Path

# 機関キー → KAKEN 検索に使う正式名称
INSTITUTIONS = {
    "jaist": "北陸先端科学技術大学院大学",
    "fukushima": "福島大学",
    "okayama": "岡山大学",
}

DEFAULT_KEY = "jaist"


def inst_name(key):
    if key not in INSTITUTIONS:
        raise SystemExit(f"未知の機関キー: {key}（候補: {', '.join(INSTITUTIONS)}）")
    return INSTITUTIONS[key]


def paths(key):
    """機関キーに対するデータ/出力パス一式。"""
    inst_name(key)                       # キーの検証
    root = Path("data") / key
    out = Path("output")
    return {
        "root": root,
        "all_xml": root / "all.xml",           # 機関検索の全課題
        "erads": root / "erads.txt",           # 母集団の研究者番号リスト
        "researchers": root / "researchers",   # 研究者ごとの生涯全課題XML（API方式）
        "json": root / "researchers.json",     # 研究者検索JSONエクスポート（appid不要）
        "csv": root / "stepup.csv",
        "hist": out / f"kaken_stepup_hist_{key}.pdf",
        "gantt": out / f"kaken_stepup_gantt_{key}.pdf",
        "gantt_nolarge": out / f"kaken_nolarge_gantt_{key}.pdf",
        "report": out / f"kaken_report_{key}.pdf",
    }


def key_from_args(args):
    """argv から機関キーを1つ取り出す（無ければ DEFAULT_KEY）。残りも返す。"""
    keys = [a for a in args if a in INSTITUTIONS]
    rest = [a for a in args if a not in INSTITUTIONS]
    return (keys[0] if keys else DEFAULT_KEY), rest
