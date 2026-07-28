#!/usr/bin/env python3
"""機関の全課題を KAKEN から取得し、母集団（研究者番号リスト）を作る。

母集団 = 「科研費に関わったことがあり、その機関に一度でも所属した人」の近似：
  (a) 実施機関にその機関を含む課題の研究代表者（eRad あり）
  (b) memberList の affiliation がその機関のメンバー（全ロール・eRad あり）
の和集合。既知の限界: eRad の無い記録は追跡不能。在籍中に他機関の課題へ
分担参加しただけの人は機関検索にほぼ載らず漏れる（僅少とみなす）。

使い方:
    .venv/bin/python kaken_roster.py fukushima
    # → data/fukushima/all.xml, data/fukushima/erads.txt
"""
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from kaken_fetch import API, RW, SLEEP, load_appid
from kaken_gantt import find_lang, text
from kaken_inst import inst_name, key_from_args, paths

PI_ROLE = "principal_investigator"


def fetch_all(appid, name):
    """機関名で全課題を検索して grantAward 要素のリストを返す。"""
    awards, st, total = [], 1, None
    while total is None or st <= total:
        params = {"appid": appid, "format": "xml", "qe": name, "rw": RW, "st": st}
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "kaken-history/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            root = ET.fromstring(resp.read())
        if total is None:
            el = next((e for e in root.iter() if "totalResults" in e.tag), None)
            total = int(el.text) if el is not None else 0
            print(f"{name}: 全{total}課題")
        page = root.findall("grantAward")
        awards.extend(page)
        print(f"  st={st}: {len(page)}件")
        st += RW
        time.sleep(SLEEP)
    return awards


def extract_erads(awards, name):
    """課題リストから母集団の研究者番号集合を作る。"""
    erads = set()
    for a in awards:
        s = find_lang(a, "summary", "ja")
        if s is None:
            continue
        # (a) 実施機関にこの機関を含む課題のPI
        if any(text(i) == name for i in s.findall("institution")):
            for m in s.findall("member"):
                if m.get("role") == PI_ROLE and m.get("eradCode"):
                    erads.add(m.get("eradCode"))
        # (b) affiliation がこの機関のメンバー（全ロール）
        for ml in a.findall("memberList"):
            for m in ml.findall("member"):
                erad = m.get("eradCode")
                att = m.find("attribute")
                if not erad or att is None:
                    continue
                if any(text(aff.find("institution")) == name
                       for aff in att.findall("affiliation")):
                    erads.add(erad)
    return erads


def main():
    key, _ = key_from_args(sys.argv[1:])
    name = inst_name(key)
    p = paths(key)
    appid = load_appid()
    if not appid:
        sys.exit(".env に KAKEN_APP_ID を設定してください")

    awards = fetch_all(appid, name)
    p["root"].mkdir(parents=True, exist_ok=True)
    merged = ET.Element("grantAwards")
    merged.extend(awards)
    ET.ElementTree(merged).write(p["all_xml"], encoding="UTF-8", xml_declaration=True)

    erads = extract_erads(awards, name)
    p["erads"].write_text("\n".join(sorted(erads)) + "\n")
    print(f"保存: {p['all_xml']}（{len(awards)}課題） / {p['erads']}（{len(erads)}人）")


if __name__ == "__main__":
    main()
