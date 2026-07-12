#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんなの未来給食 未来シミュレーター ── 品質チェックスクリプト

使い方:
    python3 scripts/check.py              # リポジトリの index.html を検査
    python3 scripts/check.py <htmlパス>   # 任意のファイル（マスター等）を検査

検査項目:
  1. i18n辞書の孤児キー（HTML中に存在しない日本語キー = 編集でズレた翻訳）
  2. 献立データの整合（menuTemplatesのlabel ⇔ MENU_VARIANTSのキー）
  3. 禁止語（ヴィーガン/ビーガン/vegan、28品目・特定原材料の断定）
  4. 動物性食材の混入（献立名の強いシグナルのみ・誤検知抑制済み）
  5. サイトURLの不整合（SITE_URLとOGP等のズレ）

終了コード: 問題なし=0 / 問題あり=1
※「日本語を編集したのに翻訳辞書を直していない」は本スクリプトで検出できます。
  逆方向（新規テキストの翻訳漏れ）はブラウザでの監査が必要です → MAINTENANCE.md参照。
"""
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(__file__).resolve().parent.parent / "index.html"
    if not path.exists():
        print(f"NG: ファイルが見つかりません: {path}")
        return 1
    html = path.read_text(encoding="utf-8")
    print(f"検査対象: {path}\n")
    problems = 0

    # ── 1. i18n辞書の孤児キー ──────────────────────────────
    m = re.search(r"const I18N_EN = (\{.*?\});\n", html, re.S)
    if not m:
        print("NG: I18N_EN 辞書が見つかりません（構造が変わった？）")
        problems += 1
        dic = {}
    else:
        try:
            dic = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            print(f"NG: I18N_EN がJSONとして読めません: {e}")
            problems += 1
            dic = {}
    # 辞書自身を除いた本文からキーを探す（辞書内のキー自身と誤マッチしないように）
    body = html.replace(m.group(0), "") if m else html
    orphans = [k for k in dic if k not in body]
    if orphans:
        problems += 1
        print(f"NG: i18n孤児キー {len(orphans)}件（日本語を編集したら辞書キーも更新が必要）")
        for k in orphans[:10]:
            print(f"   - {k[:70]}")
    else:
        print(f"OK: i18n辞書 {len(dic)}キー すべてHTML中に存在")

    # ── 2. 献立データの整合 ──────────────────────────────
    labels = re.findall(r'label:\s*"([^"]+)"', html)
    vm = re.search(r"const MENU_VARIANTS = \{(.*?)\n\};", html, re.S)
    vkeys = re.findall(r'\n\s*"([^"]+)":\s*\[', vm.group(1)) if vm else []
    lab_set, var_set = set(labels), set(vkeys)
    if lab_set != var_set:
        problems += 1
        only_l = lab_set - var_set
        only_v = var_set - lab_set
        print("NG: 献立データ不整合")
        if only_l:
            print(f"   バリエーションが無いlabel: {sorted(only_l)[:5]}")
        if only_v:
            print(f"   labelが無いバリエーションキー: {sorted(only_v)[:5]}")
    else:
        print(f"OK: 献立データ {len(lab_set)}食材 label⇔バリエーション完全一致")

    # ── 3. 禁止語 ──────────────────────────────────────
    banned = ["ヴィーガン", "ビーガン", "vegan", "Vegan", "VEGAN",
              "28品目不使用", "特定原材料28品目"]
    hits = [(w, html.count(w)) for w in banned if w in html]
    if hits:
        problems += 1
        print(f"NG: 禁止語が混入: {hits}")
    else:
        print("OK: 禁止語（ヴィーガン等）なし")

    # ── 4. 動物性食材の混入（献立名のみ・強いシグナルのみ）────
    dishes = []
    for arr in re.findall(r'dishes:\s*\[([^\]]*)\]', html):
        dishes += re.findall(r'"([^"]+)"', arr)
    if vm:
        for arr in re.findall(r'\[((?:"[^"]*",?\s*)+)\]', vm.group(1)):
            dishes += re.findall(r'"([^"]+)"', arr)
    strong = re.compile(r"卵|たまご|玉子|チーズ|牛乳|ヨーグルト|ベーコン|ソーセージ|ウインナ|ツナ|かつおだし|煮干|じゃこ|ちりめん")
    meat = re.compile(r"鶏|豚|牛(?!乳)")
    plant_ok = re.compile(r"大豆ミート|植物性|豆乳|風")
    bad = []
    for d in set(dishes):
        if strong.search(d):
            bad.append(d)
        elif meat.search(d) and not plant_ok.search(d):
            bad.append(d)
    if bad:
        problems += 1
        print(f"NG: 動物性の疑いがある献立名 {len(bad)}件: {bad[:8]}")
    else:
        print(f"OK: 献立名 {len(set(dishes))}品 動物性シグナルなし")

    # ── 5. サイトURLの不整合 ────────────────────────────
    site = re.search(r"const SITE_URL = 'https://smile-kyushoku-project\.github\.io/([^/']+)/'", html)
    if site:
        repo = site.group(1)
        others = set(re.findall(r"smile-kyushoku-project\.github\.io/([\w\-]+)", html))
        if others - {repo}:
            problems += 1
            print(f"NG: SITE_URL({repo}) と異なるURLが混在: {sorted(others - {repo})}")
        else:
            print(f"OK: サイトURL統一（…/{repo}/）")
    else:
        problems += 1
        print("NG: SITE_URL が見つかりません")

    # ── 結果 ──────────────────────────────────────────
    print()
    if problems:
        print(f"✗ {problems}項目に問題があります。修正してから公開してください。")
        return 1
    print("✓ すべてのチェックに合格しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
