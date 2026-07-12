# みんなの未来給食 未来シミュレーター ── メンテナンスガイド

学校向け植物性給食のインパクト・シミュレーター。1枚のHTMLだけで動く静的サイトです。
このガイドは、**将来このサイトを更新する人（AIアシスタント含む）が壊さずに作業するため**のものです。

- 公開URL: https://smile-kyushoku-project.github.io/mirai-simulator/
- リポジトリ: `smile-kyushoku-project/mirai-simulator`（GitHub Pages / mainブランチ直公開）
- **マスターファイル**: `~/Documents/Claude/Projects/日本の小中学校でヴィーガン給食を！/impact_simulator.html`
  （編集は必ずマスターで行い、リポジトリの `index.html` へコピーして公開する）

---

## 1. 更新とデプロイの手順

```bash
# 1) マスターを編集したら、公開前チェックを必ず実行
python3 scripts/check.py "/Users/jayson/Documents/Claude/Projects/日本の小中学校でヴィーガン給食を！/impact_simulator.html"

# 2) 合格したらリポジトリへコピー
cp "/Users/jayson/Documents/Claude/Projects/日本の小中学校でヴィーガン給食を！/impact_simulator.html" index.html

# 3) コミットしてプッシュ
git add -A && git commit -m "..." && git push
```

- この回線では `git push` が connection reset で失敗することがある。その場合は
  `gh api repos/smile-kyushoku-project/mirai-simulator/contents/index.html -X PUT`
  （base64 content + 現在の sha を指定）で上げ、`git fetch && git reset --hard origin/main` でローカルを同期する。
- 公開反映は1〜2分。`.nojekyll` を置いてあるので Jekyll は走らない（**削除しないこと**。
  過去に Jekyll ビルドが原因で「Page build failed」が多発した）。

## 2. いちばん壊れやすい所：i18n（英語版）

翻訳は `I18N_EN` 辞書（**日本語のinnerHTMLがそのままキー**）＋ `I18N_SEL`（対象セレクタ一覧）で動く。

- **日本語の文章を1文字でも変えたら、辞書のキーも同じに変えること。**
  変え忘れると、英語版でその箇所だけ日本語のまま表示される（エラーは出ない）。
- 新しいテキスト要素を足したら：
  1. そのクラスを `I18N_SEL` に追加
  2. `I18N_EN` に「日本語（innerHTML完全一致）→ 英語」のエントリを追加
- ズレの検出：`scripts/check.py` が「辞書にあるのに本文にないキー（孤児）」を検出する。
  逆方向（新規テキストの翻訳漏れ）はブラウザで↓を実行:

```js
// DevToolsコンソールで（結果表示・details展開後に実行するとより網羅的）
[...document.querySelectorAll(I18N_SEL)].filter(el=>{
  const k=(el.__ja??el.innerHTML).trim();
  return I18N_EN[k]===undefined && /[぀-ヿ一-鿿]/.test(k);
}).map(el=>el.innerHTML.trim().slice(0,60))
```

- 献立ジェネレーター（`#menu-block`）は日本語専用（英語では非表示）。翻訳不要。
- 学校レポート（`#report-page`）も日本語のみ。翻訳不要。

## 3. コンテンツのルール（変更しないこと）

- **「ヴィーガン」「ビーガン」「vegan」という語は使わない**（キーメッセージは「選べること」）
- 「特定原材料28品目不使用」とは**書かない**（大豆・小麦を使うため矛盾する）
- 環境数値の計算定数：1食あたり **水200L / CO₂ 0.8kg / 土地15㎡**。
  出典表記は「オックスフォード大学の研究（Poore & Nemecek, 2018, Science）」
- 栄養データの出典：文部科学省「日本食品標準成分表2020年版（八訂）」
- アレルギー統計：主な原因の約70%が動物性（n=2,954）※「全アレルギー対応」とは書かない

## 4. サイトURLが埋め込まれている場所（URL変更時は全部直す）

HTML内の4箇所 ＋ 外部2つ：

1. OGPメタ（`og:url` / `og:image`）
2. JSの `const SITE_URL`
3. シェア画像・共有文のテンプレート
4. 学校レポートの連絡先行と**QRコード**（base64埋め込みPNG）
5. （外部）名刺データ `名刺カード/`（表面QRは `?src=card` 付き）
6. （外部）Googleフォームの説明文と `feedback_form.gs`

`scripts/check.py` が SITE_URL と他のURLの不整合を検出する。

### QRコードの作り直し方（Python `qrcode` インストール済み）

```python
import qrcode, io, base64
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
qr.add_data("https://smile-kyushoku-project.github.io/mirai-simulator/")
qr.make(fit=True)
# → PNG化してbase64にし、#report-page の .rp-qr img の data URI を差し替える
```

差し替え後は、ブラウザの `BarcodeDetector` で実際にデコードして新URLを指すことを確認する。

## 5. 学校レポート（3枚構成の提案書）の注意

`printReport()` → `window.print()`。`@media print` で `#report-page` だけを印刷。

- **背景色は印刷されない前提でデザインする**（ブラウザの既定設定）。
  色を確実に出したい要素は「文字色・border・インラインSVG」を使う
  （見出しの左バー、SDGsタイルがその方式）。
- 各ページは `.rp-page`（`page-break-after: always`）。
  **中身がA4を数ミリでも超えると"真っ白なページ"が挟まる**ので、
  文字サイズや余白を増やしたら必ず実機で印刷プレビュー確認。
- 献立を作成済みならレポート2枚目に自動掲載される（`rp-menu-section`）。

## 6. 構成メモ

- 計測: GoatCounter（https://smile-kyushoku.goatcounter.com）
  イベント: simulate / share-card / report-print / menu系 / cta-mail など
- 献立データ: `menuTemplates`（153食材）+ `MENU_VARIANTS`（153キー・計435品）+
  `COMMON_VEG`（共通野菜）+ `LOCAL_NAME_MAP`（他地域の特産品名を一般名に変換）。
  **labelとMENU_VARIANTSのキーは完全一致が必須**（check.pyが検証）。
- 連絡先: japan@animalallianceasia.org（mailtoには件名 `?subject=未来給食の導入相談` 付き）
- `LINKS` の公式サイト/Instagram は未設定（空のままだとボタン非表示）。

## 7. 公開前チェックリスト

```bash
python3 scripts/check.py <マスターのパス>   # 必須（i18n孤児/献立整合/禁止語/URL）
```

加えて手動で：
- [ ] スマホ幅での表示（Chrome DevTools）
- [ ] EN切替で新規テキストが翻訳されるか（§2のスニペット）
- [ ] レポートのPDF出力（ページ数・空白ページ・QR読み取り）
