# CLAUDE.md

このリポジトリで作業する際のガイド（人間にも Claude にも向けたメモ）。

## コンセプト

科研費データベース（[KAKEN](https://kaken.nii.ac.jp/)）からダウンロードした XML を読み込み、
**研究代表者ごとの科研費取得履歴を「1課題＝1本の横棒」のガントチャートにまとめた A4縦 PDF** を生成する。

- 横軸＝年度（全研究者で共通スケール）、縦に研究者ブロックを積む
- 研究者ごとに黒い横線で区切り、年度軸はページ上下の2箇所のみ
- 種目（基盤研究(C) など）で色分け
- 1人のブロックはページを跨がない（行数で見積もってから配置）

成果物は `output/kaken_gantt.pdf` の1ファイル。

## 開発環境

- Python 仮想環境（`.venv`）を必ず使う。パッケージは `.venv/bin/pip` で入れる。
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt   # matplotlib
  ```
- 実行：
  ```bash
  .venv/bin/python kaken_gantt.py            # 全員 → output/kaken_gantt.pdf
  .venv/bin/python kaken_gantt.py 00343187   # 研究者番号(eRad)で絞り込み
  .venv/bin/python kaken_gantt.py 鵜木        # 氏名(部分一致)で絞り込み
  ```

## 出力（PDF）の確認方法

PDF は中身を直接目視できないので、確認時は PNG に変換してから見る（変換物は `/tmp` に置き、リポジトリには残さない）。

```bash
# 1ページPDF
sips -s format png output/kaken_gantt.pdf --out /tmp/check.png
# 複数ページPDFの特定ページ（poppler / brew install poppler）
pdftoppm -png -r 80 -f 1 -l 1 output/kaken_gantt.pdf /tmp/page
```
変換時の「font type mismatch」警告は無害。

## レイアウト調整

`kaken_gantt.py` 冒頭付近の定数で変える：
`ROW_INCH`（行高＝バー太さ）/ `BAR_H`（行内のバー割合、1.0で隙間ゼロ）/ `GAP_ROWS`（研究者間の空き行）/
`LABEL_W`（左の氏名欄幅）/ `MARGIN` / `AXIS_MIN`・`AXIS_MAX`（横軸範囲、None で自動）。

## KAKEN XML の扱い（重要な落とし穴）

実データ（655課題）と公式仕様で確認済みの要点。変更時はここを壊さないこと。

- **研究者の同定は `summary/member@eradCode`（eRad 研究者番号）で行う。**
  `memberList/member` の `id="MEMBER-xxxxx"` は課題ごとのメンバー記録IDで、同一人物でも課題ごとに別IDになるため名寄せに使えない。
- 対象は研究代表者（`@role="principal_investigator"`）のみ。研究者番号の無い記録（特別研究員奨励費など）は除外。
- 研究期間は `periodOfAward` の `searchStartFiscalYear` / `searchEndFiscalYear`（ja優先）。
- `projectStatus@statusCode`：project_closed / granted / adopted / discontinued / **declined**。
  **`declined`（不採択・辞退）は獲得実績でないため除外する。**
- 種目名の全角ゆれ（`基盤研究(Ｃ)`、全角カッコ）は `normalize_category()` で正規化。
- 横軸の既定：最小＝全課題の最小開始年、最大＝最大開始年+1。終了がそれを超える課題は右端で切れる（仕様）。

公式仕様・マスタ：
- XML/JSON 定義書: <https://bitbucket.org/niijp/kaken_definition>
- マスタ（種目・審査区分など）: <https://bitbucket.org/niijp/grants_masterxml_kaken>

## データと公開の注意点

- 入力 XML（`*.xml`）は**研究者の氏名・研究者番号を含む**ため、リポジトリに含めない（`.gitignore` で `*.xml` と `output/` を除外）。
- このリポジトリは Public。**コードのみ公開し、氏名入りの生成物（PDF/PNG）は公開しない**方針。
- 可視化の性質上、研究者ごとに並べると「採択が少ない／代表経験がない（図に登場しない）」といった**評価的な含意が一目で見えてしまう**点に配慮する。
  - 表示しているのは獲得済み課題のみ（不採択は出さない）だが、**少なさ・空白は“不在”として明確に伝わる**。
  - 用途は自己分析・所属機関内の把握を想定。個人比較・評価目的での再配布は想定しない。
  - 必要なら匿名化（氏名/番号を伏せる）や集計ビュー（人を特定しない）への切り替えを検討する。

## 機関別の分析パイプライン

**機関はパラメータ化**されている（`kaken_inst.py` の `INSTITUTIONS`、キー例: `jaist` / `fukushima`）。
データは `data/<機関キー>/`（all.xml・erads.txt・researchers/・stepup.csv）、
生成物は `output/*_<機関キー>.pdf`。新しい機関はキーと正式名称を1行足すだけ。

実行順（機関キーを引数に渡す。省略時は jaist）:
```bash
.venv/bin/python kaken_roster.py fukushima        # 機関の全課題→母集団リスト
.venv/bin/python kaken_fetch.py fukushima         # 研究者ごとの生涯全課題を取得
.venv/bin/python kaken_stepup.py fukushima        # 所要年数の集計+ヒストグラム
.venv/bin/python kaken_stepup_gantt.py fukushima  # 大型あり群：相対年アラインのガント
.venv/bin/python kaken_nolarge_gantt.py fukushima # 大型なし群：翌年度アラインのガント
.venv/bin/python kaken_report.py fukushima        # A4縦1枚レポート
```

## 入力ソース：研究者JSON（推奨・appid不要）と API取得XML（従来）

**入力は `kaken_data.load_researchers(key)` に一元化**され、下流（stepup/gantt/report）は
ソースを気にしない。優先順位：

1. `data/<key>/researchers.json` … KAKEN「**研究者をさがす**」(nrid.nii.ac.jp) の JSON
   エクスポート。**appid不要**。人単位で生涯全課題を内包するため、機関検索XMLで欠ける
   他機関時代の課題も入る（実データ検証済み：JAISTでAPI方式ロスターを完全被覆し、
   所要年数の集計も一致）。パーサは `kaken_json.py`。1回のエクスポート上限1万件。
2. `data/<key>/researchers/*.xml` … `kaken_fetch.py` が API で取得した従来方式（appid必要）。
   JSONが無ければ自動でこちらにフォールバック。

研究者JSONの取り方：「研究者をさがす」で研究機関＝機関名を検索 → Select All → Export in JSON。
XML↔JSONの対応：PI判定=課題top-levelの`role`に`principal_investigator`、領域代表=`role`に
`area_organizer`（XMLの`projectType="organizer"`相当）、期間=`since`/`until`の`fiscal:year`、
種目=`category[0].humanReadableValue(ja)`、状態=`projectStatus/statusCode`、氏名=`name`/ヨミは
`ja-Kana`。共通の分析ロジックは `kaken_stepup.analyze_researcher(r)`（研究者dictを受ける）。

**Colab配布**: `kaken_colab.ipynb`（他大学URA・研究者向け。ブラウザだけでJSON→PDF、appid不要）。
Colab(Linux)はMac日本語フォントが無いのでIPAゴシックを導入。Noto CJKは言語指定なしだと
中国語字形になるため使わない（`kaken_gantt.py` のフォント指定も同方針）。

## データ取得（kaken_fetch.py）と採択前実績の集計（kaken_stepup.py）

機関単位の検索結果は検索範囲外・他機関時代の課題を含まないため、
**KAKEN OpenSearch API で研究者ごとに全件取得し直す**（懸念は実データで確認済み。
例: エクスポート12課題 → API 26課題）。

- API: `https://kaken.nii.ac.jp/opensearch/?appid=…&format=xml&qm=<eRad>&rw=500&st=…`
  - **appid 必須**（取得済み。`.env` の `KAKEN_APP_ID`、git 除外）。無いと 403。
  - `qm`=研究者番号は**全ロール**（代表・分担…）にマッチ。ロールの絞り込みはパース側で行う。
- `kaken_roster.py`: 機関名で全課題を検索し（`qe`・年度制限なし）、母集団
  （JAIST方式: 実施機関にその機関を含む課題のPI ∪ affiliation がその機関のメンバー）
  の eRad リストを `data/<key>/erads.txt` に保存。
- `kaken_fetch.py`: 母集団全員の生涯全課題を `data/<key>/researchers/<erad>.xml` に保存。
  取得済みはスキップ（`--force` で上書き）。1秒間隔のポライトアクセス。
- `kaken_stepup.py`: 「最初の科研費 → 大型科研費の初採択」の所要年数を集計 → `data/stepup.csv`。
  - **最初の科研費** = PIとしての初採択。分担除外・特別研究員奨励費除外・declined除外。
  - **大型科研費** = 基盤研究(B)/(A)/(S)・特別推進研究・挑戦的研究(開拓)＋旧種目の一般研究(A)/(B)
    （1995年度以前の基盤A/B相当）。PIのみ。
    領域型（新学術・学術変革(A)/(B)）は**領域代表（総括班 `projectType="organizer"` のPI）のみ**大型
    とみなす（計画研究・公募研究の代表は含めない）。※現245人に領域代表は0人。
- **母集団**: 「科研費に関わったことがあり、JAISTに一度でも所属した人」= 484人。
  作り方: APIの機関検索（`qe=北陸先端科学技術大学院大学`、年度制限なし、全1440課題
  → `data/jaist/all.xml`）から、(a) 実施機関にJAISTを含む課題のPI、
  (b) `memberList/member/attribute/affiliation/institution` がJAISTのメンバー（全ロール）
  の eRad を集めた和集合 → `data/jaist/erads.txt`（この手順は kaken_roster.py に一般化済み）。
  - 限界: eRadの無い記録（特別研究員等・古い記録）は追跡不能。JAIST在籍中に
    **他機関の課題に分担参加しただけ**の人は `qe` 検索にほぼ載らず漏れる（僅少とみなす）。
  - 旧エクスポートXML（機関=JAIST×2011年度以降、245人）はこの母集団の部分集合。
- `kaken_stepup.py` は所要年数ヒストグラムも出力 → `output/kaken_stepup_hist.pdf`
  （大型未取得者は含めない。氏名を含まないので公開可能性のある唯一の生成物）。
- **世代カットオフ**: 最初の科研費が **1996年度以降** の研究者だけを分析する
  （`kaken_stepup.py` の `FIRST_YEAR_MIN`、ガントも同条件）。データ取得自体は全年代行い、
  分析段階でフィルタする方式。1996 = 基盤研究(A)(B)(C) 制度の開始年。
  理由: (1) キャリアが現行に近い種目体系に収まる、(2) eRad 紐付けが怪しい1980年代を除外、
  (3) 観測窓30年を確保（2002年開始だと窓24年で長い経路の裾が切れ始める）。
  なお「0年組」（初代表がいきなり大型）は紐付け不良ではなく実態と確認済み。
  実態の内訳（JAISTの25人で検証）: 17人は大型以前のKAKEN記録が皆無（民間企業・海外機関
  出身で応募資格の取得がシニア期）、3人は他機関で分担のみ、5人は**同一機関内**で分担のみ。
  つまり本質は「代表デビューがキャリア中盤」であり、機関移動（着任）は必須要素ではない。
- **打ち切りバイアスに注意**: ヒストグラムは大型到達者だけの条件付き分布。
  「大型なし」には「まだ取っていないだけ」の若手が混ざる。本格的には生存時間分析が必要。
- `kaken_report.py`: A4縦1枚のレポートPDF（上=問い・方法・結果・留意点、下=ヒストグラム）
  → `output/kaken_report.pdf`。数値は集計から動的に埋め込み。氏名なしで配布可能な体裁。
- パース上の注意: 古い課題では `summary/member` に分担者が載らないことがある
  （`memberList` 側にのみ記載）。PI は `summary/member` に必ず載るので PI 分析には影響なし。
  分担者を含める分析をするなら `memberList` を見ること。
- `kaken_stepup_gantt.py`: 大型初採択の開始年度を**相対年0**にアラインしたガントチャート
  → `output/kaken_stepup_gantt.pdf`（大型あり95人、所要年数の短い順）。0に縦破線、
  大型初採択の課題は黒枠（`highlight`）。表示条件は kaken_stepup.py の集計と同一。
  氏名の下に所要年数（`year_label`）を添える。
- `kaken_nolarge_gantt.py`: **大型なし群**のガント → `output/kaken_nolarge_gantt_<key>.pdf`。
  揃える基準が無いので「次に新しい課題が始まる年度」（`next_fiscal_year()`＝翌年度、
  今日の日付から算出）を**相対年0**に置く。氏名の下に「経過N年」（最初の科研費→基準年）を
  添え、大型到達者の所要年数（中央値）と比較できるようにする。経過年の長い順。表示条件は
  kaken_stepup.py の集計と同一（PIのみ・特別研究員奨励費/declined除外・FIRST_YEAR_MIN以降）。
  ※相対年ガントの左ラベルの年数表記は `kaken_gantt.render_page` が `year_label` を見る共通実装。

## 今後の計画（ロードマップ）

現状のガント可視化は**前段階**。本当にやりたいのは次の分析。

### 目的
**大型科研費（基盤研究(A) など）を採択した研究者が、その採択以前にどのような科研費採択実績を積み上げてきたか**を、可視化＋統計で明らかにする。

### アイデア1: 採択時点でアラインした可視化
- 対象種目（既定: 基盤研究(A)。設定で 基盤(S) / 学術変革(A) 等も）を「**指標イベント**」とする。
- 研究者ごとに、指標イベントの採択開始年を **基準年=0** に置き、横軸を**相対年**（−5, −4, …, 0, +1 …）に変換して全研究者をアラインする。
- これにより「基盤A の N 年前に何を持っていたか」が研究者間で重ね合わせられる。
- 実装の足がかり: 既存の `AXIS_MIN`/`AXIS_MAX`（絶対年）に加え、**相対年モード**を追加。各課題の `start`/`end` から指標イベント年を引いてオフセットすればよい。指標イベントを持たない研究者は対象外 or 別扱い。

### アイデア2: 採択前実績の統計処理
基準（指標イベント）より前の期間に限定して、研究者ごとに特徴量を作り集計・検定する。候補：
- 指標イベントまでの**所要年数**（最初の科研費 → 基盤A）。
- 直前までの**代表課題数**、**種目の内訳**（若手 / 基盤C / 基盤B / 挑戦的萌芽 …）。
- **ステップアップ経路**（例: 若手→基盤C→基盤B→基盤A）の典型パターン・遷移分析。
- **空白期間**（無採択の年）の有無・長さ。
- 大型採択**あり群 vs なし群**の比較（前実績の分布差、ロジスティック回帰や生存分析など）。
- 配分額を使う分析（後述の通り現状はパースを外しているため要復活）。

### 着手前に解消すべきデータ上の論点（重要）
- **このXMLは検索結果のエクスポート（おそらく特定機関/クエリ）であり、KAKEN全体ではない。**
  研究者の**生涯フル実績**を見るには不十分な可能性が高い（他機関時代の課題や、クエリ外の課題が欠ける）。
  → 正確な「採択前実績」分析には、**研究者番号(eRad)ごとにKAKENから全件取得**し直す必要がありそう。データ取得の設計から要検討。
- 現状は**研究代表者(PI)のみ**。前実績として**研究分担者**経験も含めるべきか要検討（含めるなら summary/member の他ロール、または memberList の分担者を eradCode で名寄せ。分担者にも eradCode があるか確認）。
- **配分額は現状パースしていない**（途中で「研究費不要」としたため `Project` から除外）。金額を使う統計には `overallAwardAmount` / `awardAmountList/awardAmount` のパース復活が必要。
- `declined`（不採択）は除外済みだが、分析次第では「不採択も含めた応募行動」を見たい場合があり得る。その際は除外条件を見直す。
