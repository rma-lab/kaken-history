"""Pyodide（Web版）で分析パイプラインを実行するグルーコード。

worker.js が analysis の .py 一式と researchers.json を仮想FSに配置した後、
run(label) を呼ぶ。Colab 版のセル5と同じことをする：
フォント登録 → タイトルラベル登録 → 4スクリプトの main() 実行。
"""
import os
import sys


def run(label):
    os.chdir("/home/pyodide")

    # 日本語フォント（IPAゴシック）。kaken_gantt が import 時に候補から選ぶので先に登録
    import matplotlib.font_manager as fm
    fm.fontManager.addfont("/fonts/ipag.ttf")

    import kaken_inst
    kaken_inst.INSTITUTIONS["target"] = label or ""
    sys.argv = ["", "target"]

    import kaken_stepup, kaken_report, kaken_stepup_gantt, kaken_nolarge_gantt
    kaken_stepup.main()
    kaken_report.main()
    kaken_stepup_gantt.main()
    kaken_nolarge_gantt.main()

    import glob
    return sorted(glob.glob("output/*_target.pdf"))
