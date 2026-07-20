#!/usr/bin/env python3
"""分析の入力ソースを一元化する。

研究者(人)単位の課題リストを、次の優先順で読み込んで返す:
  1. data/<key>/researchers.json  … KAKEN「研究者をさがす」JSONエクスポート（appid不要・推奨）
  2. data/<key>/researchers/*.xml … kaken_fetch.py が API で取得した従来方式（appid必要）

どちらも同じ構造 {"erad","name","yomi","projects":[...]} のリストを返すので、
下流（kaken_stepup / kaken_stepup_gantt / kaken_report）はソースを気にしなくてよい。
"""
from kaken_inst import paths


def load_researchers(key):
    """機関キーの研究者リストと、使ったソース種別 ("json"|"xml") を返す。"""
    p = paths(key)
    if p["json"].exists():
        import kaken_json
        return kaken_json.load(p["json"]), "json"

    # 従来のAPI取得XML（研究者ごと1ファイル）にフォールバック
    from kaken_stepup import pi_projects, researcher_name
    researchers = []
    for path in sorted(p["researchers"].glob("*.xml")):
        erad = path.stem
        researchers.append({
            "erad": erad,
            "name": researcher_name(path, erad),
            "yomi": "",
            "projects": pi_projects(path, erad),
        })
    return researchers, "xml"
