#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import csv
import re
from pathlib import Path

# 親ディレクトリのapiモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'api'))

def normalize_label(label):
    """ラベルを正規化して類似ラベルを統一"""
    # ■記号を除去
    label = label.lstrip('■').strip()

    # 類似ラベルを統一
    label_mappings = {
        '原材料名': '原材料',
        '品名': '商品名',
        '内容量': '容量',
        '賞味期限': '賞味期限',
        '保存方法': '保存方法',
        '販売者': '販売者',
    }

    # マッピングに一致するものがあれば変換
    for key, value in label_mappings.items():
        if key in label or label in key:
            return value

    return label

def extract_product_info(pc_text, sp_text):
    """C列とD列から商品情報テキストを抽出（画像・リンクを除く）"""
    # SP版のテキストを優先的に使用
    text = sp_text if sp_text else pc_text

    if not text:
        return ""

    # HTMLタグから情報を抽出
    # <table>タグの内容を抽出
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_matches = re.findall(table_pattern, text, re.DOTALL | re.IGNORECASE)

    # 重複を除去：ラベルと値のペアで管理
    seen_items = {}  # {normalized_label: (original_label, value)}

    # テーブルから情報抽出（最初のテーブルのみ - 商品情報テーブル）
    if table_matches:
        table_html = table_matches[0]  # 最初のテーブルのみ使用
        # <tr><th>...</th><td>...</td></tr> 形式から抽出
        row_pattern = r'<tr[^>]*>.*?<th[^>]*>(.*?)</th>.*?<td[^>]*>(.*?)</td>.*?</tr>'
        rows = re.findall(row_pattern, table_html, re.DOTALL | re.IGNORECASE)

        print(f"\n=== テーブルから抽出された行: {len(rows)}個 ===")

        for label, value in rows:
            # HTMLタグを除去
            label = re.sub(r'<[^>]+>', '', label).strip()
            value = re.sub(r'<[^>]+>', '\n', value).strip()
            label = label.lstrip('■')

            # ラベルを正規化
            normalized_label = normalize_label(label)

            print(f"元ラベル: {repr(label)} -> 正規化: {repr(normalized_label)}")

            # 正規化されたラベルで重複チェック
            if normalized_label not in seen_items:
                seen_items[normalized_label] = (label, value)
                print(f"  → 追加")
            else:
                print(f"  → 重複のためスキップ")

    # 栄養成分情報のみを抽出（栄養成分キーワードを含む行のみ）
    nutrition_keywords = ['エネルギー', 'たんぱく質', 'タンパク質', '脂質', '炭水化物', '食塩', 'ナトリウム', '糖質', '食物繊維']

    # テーブル以外のテキストから栄養成分を探す
    # tableタグを削除して残りのテキストを取得
    text_without_tables = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 画像・リンクも削除
    text_without_tables = re.sub(r'<a[^>]*>.*?</a>', '', text_without_tables, flags=re.DOTALL | re.IGNORECASE)
    text_without_tables = re.sub(r'<img[^>]*>', '', text_without_tables, flags=re.IGNORECASE)

    # 全てのHTMLタグを除去
    clean_text = re.sub(r'<br\s*/?>', '\n', text_without_tables, flags=re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', '\n', clean_text)

    # 栄養成分行を格納（重複チェック付き）
    seen_nutrition = {}

    # 行ごとに分割
    lines = clean_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 栄養成分キーワードを含む行のみ追加（重複チェック付き）
        if any(keyword in line for keyword in nutrition_keywords):
            if line not in seen_nutrition:
                seen_nutrition[line] = True

    # 結果を組み立て（テーブル項目 + 栄養成分）
    result_parts = []
    for normalized_label, (original_label, value) in seen_items.items():
        result_parts.append(f"■{original_label}:{value}")

    result_parts.extend(seen_nutrition.keys())

    return '\n\n'.join(result_parts)

# テスト実行
input_csv = Path(__file__).parent.parent / '無題のスプレッドシート のコピー - ir-itemsub_楽天_美味セレクト楽天市場店 (9).csv'

with open(input_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    row = next(reader)

pc_text = row.get('PC用商品説明文', '')
sp_text = row.get('スマートフォン用商品説明文', '')

result = extract_product_info(pc_text, sp_text)

print('\n\n=== extract_product_infoの戻り値 ===')
print(result)
print('\n=== 統計 ===')
print(f'「内容量」の出現回数: {result.count("内容量")}')
print(f'「原材料」の出現回数: {result.count("原材料")}')
