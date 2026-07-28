# kaken-history

科研費データベース（[KAKEN](https://kaken.nii.ac.jp/)）からダウンロードした XML を読み込み、
**研究代表者ごとの科研費取得履歴をガントチャート風にまとめた PDF** を生成するツールです。

- 1課題 = 1本の横棒、横軸 = 年度
- 研究者ごとにブロックを積み、黒い横線で区切り
- A4 縦・複数ページ（1人のブロックはページを跨がない）
- 種目（基盤研究(C)、挑戦的萌芽研究 など）で色分け

## 出力イメージ

各研究者について、こういった履歴が縦に並びます（年度軸はページ上下の2箇所、縦の格子線で揃う）：

```
氏名 / 研究者番号 |■ 若手研究(B) ■■■
                 |        ■ 基盤研究(C) ■■■■■
─────────────────────────────────────────────
2011 2012 2013 2014 2015 ... 2027
```

## 大型科研費までの道のり分析（他機関でも使える・appid不要）

所属機関の研究者が「最初の科研費 → 大型科研費（基盤研究(B)以上）」に何年で到達したかを
集計し、レポート・ヒストグラム・相対年ガントチャートのPDFを作ります。**KAKEN の appid や API は不要**。
KAKEN「**研究者をさがす**」からダウンロードした JSON（人単位で生涯全課題を含む）を読み込むだけ。

### Web版で使う（インストール不要・データは端末の外に出ない）

**<https://rma-lab.github.io/kaken-history/>** を開き、研究者JSONをドロップするだけ。
処理はすべてブラウザ内（[Pyodide](https://pyodide.org/)）で完結し、JSONはどこにも送信されません。
実装は `index.html` と `web/`（分析コードは Colab/ローカルと共通の `.py` をそのまま実行）。

### Colab で使う（インストール不要・ブラウザだけ）

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/rma-lab/kaken-history/blob/main/kaken-history.ipynb)

1. 上のバッジから Colab を開く
2. [KAKEN 研究者をさがす](https://nrid.nii.ac.jp/ja/) の詳細検索で、研究者情報の **所属機関＝自機関** を検索 →
   結果画面で **Select All → Export in JSON**（1回1万件まで。超える大規模機関は分割）
3. Colab のセルを上から実行し、JSON をアップロード → 機関名を入力 → PDF をダウンロード

アップロードした JSON は Colab セッション（Google のクラウド上の一時環境）で処理されます。
任意で Google ドライブをマウントした場合は、再アップロード回避のためあなた自身のドライブに
コピーが保存されます（マウントしなければ外部保存はされません）。

### ローカル（venv）で使う

```bash
# data/<機関キー>/researchers.json に研究者JSONを置く
.venv/bin/python kaken_stepup.py       <機関キー>   # 所要年数の集計＋ヒストグラム
.venv/bin/python kaken_report.py       <機関キー>   # A4縦1枚レポート
.venv/bin/python kaken_stepup_gantt.py <機関キー>   # 大型あり群: 相対年アラインのガントチャート
.venv/bin/python kaken_nolarge_gantt.py <機関キー>  # 大型なし群: 翌年度アラインのガントチャート
```

機関キーは `kaken_inst.py` の `INSTITUTIONS` に「キー→正式名称」を1行足して登録します。
`data/<機関キー>/researchers.json` があればそれを、無ければ従来の API 取得 XML を自動で使います。

## 必要環境

- Python 3.10+
- [matplotlib](https://matplotlib.org/)
- 日本語フォント（macOS の `Hiragino Sans` などを自動利用）

## セットアップ

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 使い方

KAKEN からダウンロードした XML をこのディレクトリに置き、スクリプト先頭の
`XML_DEFAULT` をそのファイル名に合わせるか、引数で XML パスを渡します。

```bash
# 全研究者を1つのPDF(output/kaken_gantt.pdf)に
.venv/bin/python kaken_gantt.py

# 研究者番号(eRad) または 氏名(部分一致) で絞り込み
.venv/bin/python kaken_gantt.py 00343187
.venv/bin/python kaken_gantt.py 鵜木

# 入力XMLを明示
.venv/bin/python kaken_gantt.py path/to/kaken.xml
```

出力は `output/kaken_gantt.pdf`。

## レイアウト調整

`kaken_gantt.py` 冒頭付近の定数で調整できます。

| 定数 | 意味 |
|------|------|
| `ROW_INCH` | 1課題あたりの行の高さ（バーの太さ） |
| `BAR_H` | 行内でバーが占める割合（1.0 で隙間ゼロ） |
| `GAP_ROWS` | 研究者ブロック間の空き（行数） |
| `LABEL_W` | 左の氏名・研究者番号欄の幅 |
| `MARGIN` | ページ余白 |
| `AXIS_MIN` / `AXIS_MAX` | 横軸の年度範囲（`None` でデータから自動。既定は最小開始年 〜 最大開始年+1） |

## 仕様・データの扱いに関するメモ

KAKEN 公開 XML の構造に基づき、以下のように処理しています。

- **研究者の同定は `summary/member@eradCode`（eRad 研究者番号）** で行う。
  `memberList/member` の `id="MEMBER-xxxxx"` は課題ごとのメンバー記録IDで人物単位ではないため使わない。
- 対象は研究代表者（`@role="principal_investigator"`）のみ。研究者番号の無い記録（特別研究員奨励費など）は除外。
- 研究期間は `periodOfAward` の `searchStartFiscalYear` / `searchEndFiscalYear`。
- `projectStatus@statusCode="declined"`（不採択・辞退）は獲得実績でないため除外。
- 種目名の全角ゆれ（`基盤研究(Ｃ)` など）は正規化。
- 研究者JSONの検索は**研究者情報の「所属機関」欄**で行う。研究課題情報の「研究機関」欄で
  検索すると、その機関に所属したことのない他機関の研究分担者まで大量に含まれ、集計が歪む。

公式仕様・マスタ:
- XML/JSON 定義書: <https://bitbucket.org/niijp/kaken_definition>
- マスタ（種目・審査区分などのコード一覧）: <https://bitbucket.org/niijp/grants_masterxml_kaken>

## データについて

入力の科研費 XML（`*.xml`）は研究者の氏名・研究者番号を含むため、本リポジトリには含めていません
（`.gitignore` で除外）。各自 KAKEN からダウンロードして配置してください。

## ライセンス

[MIT License](LICENSE)。

なお、入力データ（KAKEN の科研費情報）はこのライセンスの対象外です。データの利用条件は
[KAKEN](https://kaken.nii.ac.jp/) / NII の定めに従ってください。
