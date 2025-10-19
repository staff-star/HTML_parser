#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVファイルを読み込み、楽天・Yahoo!用のHTMLを生成するスクリプト
"""
import sys
import os
import csv
import re
from pathlib import Path

# 親ディレクトリのapiモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'api'))
from generate import FlexibleParser, HTMLGenerator

def extract_images_and_links(html_text):
    """D列から画像とリンクのHTMLを抽出"""
    if not html_text:
        return ""

    # <a>タグと<img>タグを抽出（商品説明の前の部分）
    pattern = r'(<a[^>]*>.*?</a>|<img[^>]*>)'
    matches = re.findall(pattern, html_text, re.DOTALL | re.IGNORECASE)

    # tableタグより前の部分のみを対象にする
    table_pos = html_text.lower().find('<table')
    if table_pos > 0:
        prefix_html = html_text[:table_pos]
        matches = re.findall(pattern, prefix_html, re.DOTALL | re.IGNORECASE)

    return '\n'.join(matches)

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
        for label, value in rows:
            # HTMLタグを除去
            label = re.sub(r'<[^>]+>', '', label).strip()
            value = re.sub(r'<[^>]+>', '\n', value).strip()
            label = label.lstrip('■')

            # ラベルを正規化
            normalized_label = normalize_label(label)

            # 正規化されたラベルで重複チェック
            if normalized_label not in seen_items:
                seen_items[normalized_label] = (label, value)

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
    # ■記号を除去してAPIに渡す（APIが自動的にラベルのバリエーションを統一してくれる）
    result_parts = []
    for normalized_label, (original_label, value) in seen_items.items():
        # ■記号を除去（APIのFIELD_VARIATIONSで統一される）
        # 値内の改行をスペースに置換して1行にまとめる
        clean_value = value.replace('\n', ' ').strip()
        result_parts.append(f"{original_label}:{clean_value}")

    result_parts.extend(seen_nutrition.keys())

    # 各フィールドを改行で区切る（APIが正しくパースできるように）
    return '\n'.join(result_parts)

def create_product_info_from_dict(data_dict):
    """辞書からProductInfoオブジェクトを直接作成（パーサーをバイパス）"""
    from generate import ProductInfo

    return ProductInfo(
        product_name=data_dict.get('品名', ''),
        ingredients=data_dict.get('原材料', ''),
        content=data_dict.get('内容量', ''),
        expiry=data_dict.get('賞味期限', ''),
        storage=data_dict.get('保存方法', ''),
        seller=data_dict.get('販売者', ''),
        manufacturer=data_dict.get('製造者', ''),
        processor=data_dict.get('加工者', ''),
        product_type=data_dict.get('名称', ''),
        nutrition={},
        allergen='',
        extra_fields={}
    )

def extract_product_dict(pc_text, sp_text):
    """C列とD列から商品情報を辞書として抽出"""
    # SP版のテキストを優先的に使用
    text = sp_text if sp_text else pc_text

    if not text:
        return {}

    # HTMLタグから情報を抽出
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_matches = re.findall(table_pattern, text, re.DOTALL | re.IGNORECASE)

    # ラベルを正規化して格納
    data_dict = {}
    label_map = {
        '品名': '品名',
        '商品名': '品名',
        '原材料': '原材料',
        '原材料名': '原材料',
        '内容量': '内容量',
        '容量': '内容量',
        '賞味期限': '賞味期限',
        '保存方法': '保存方法',
        '販売者': '販売者',
        '製造者': '製造者',
        '加工者': '加工者',
        '名称': '名称',
    }

    # テーブルから情報抽出
    if table_matches:
        table_html = table_matches[0]
        row_pattern = r'<tr[^>]*>.*?<th[^>]*>(.*?)</th>.*?<td[^>]*>(.*?)</td>.*?</tr>'
        rows = re.findall(row_pattern, table_html, re.DOTALL | re.IGNORECASE)

        for label, value in rows:
            label = re.sub(r'<[^>]+>', '', label).strip().lstrip('■')
            value = re.sub(r'<[^>]+>', ' ', value).strip()

            # ラベルを正規化
            normalized_label = label_map.get(label, None)
            if normalized_label and normalized_label not in data_dict:
                data_dict[normalized_label] = value

    return data_dict

def process_row(row_data):
    """1行のデータを処理"""
    product_code = row_data.get('メインデータの商品コード（楽天URL）', '')
    product_name = row_data.get('メインデータの商品名', '')
    pc_text = row_data.get('PC用商品説明文', '')
    sp_text = row_data.get('スマートフォン用商品説明文', '')

    # 画像・リンク要素を抽出（楽天版のみ使用）
    rakuten_prefix = extract_images_and_links(sp_text)

    # 商品情報を辞書として抽出
    product_dict = extract_product_dict(pc_text, sp_text)

    if not product_dict:
        return {
            '楽天パソコン': '',
            '楽天スマホ': '',
            'Yahooパソコン': '',
            'Yahooスマホ': ''
        }

    # ProductInfoオブジェクトを直接作成
    product_info = create_product_info_from_dict(product_dict)

    generator = HTMLGenerator()
    html_variants = generator.generate_all(product_info)

    # 楽天版には画像・リンクを先頭に追加
    rakuten_pc_html = rakuten_prefix + '\n' + html_variants['rakuten_pc'] if rakuten_prefix else html_variants['rakuten_pc']
    rakuten_sp_html = rakuten_prefix + '\n' + html_variants['rakuten_sp'] if rakuten_prefix else html_variants['rakuten_sp']

    return {
        '楽天パソコン': rakuten_pc_html,
        '楽天スマホ': rakuten_sp_html,
        'Yahooパソコン': html_variants['yahoo_pc'],
        'Yahooスマホ': html_variants['yahoo_sp']
    }

def process_csv(input_path, output_path):
    """CSVファイルを処理"""
    results = []

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"処理開始: {len(rows)}行")

    for idx, row in enumerate(rows, 1):
        print(f"処理中: {idx}/{len(rows)} - {row.get('メインデータの商品名', '')[:30]}...")

        try:
            html_results = process_row(row)
            row.update(html_results)
            results.append(row)
        except Exception as e:
            print(f"エラー (行{idx}): {str(e)}")
            row.update({
                '楽天パソコン': f'<!-- エラー: {str(e)} -->',
                '楽天スマホ': f'<!-- エラー: {str(e)} -->',
                'Yahooパソコン': f'<!-- エラー: {str(e)} -->',
                'Yahooスマホ': f'<!-- エラー: {str(e)} -->'
            })
            results.append(row)

    # 結果をCSVに書き込み
    if results:
        fieldnames = list(results[0].keys())
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"完了: {output_path}")
    return results

if __name__ == '__main__':
    script_dir = Path(__file__).parent
    input_csv = script_dir.parent / '無題のスプレッドシート のコピー - ir-itemsub_楽天_美味セレクト楽天市場店 (9).csv'
    output_csv = script_dir / 'output_result.csv'

    if not input_csv.exists():
        print(f"エラー: 入力ファイルが見つかりません: {input_csv}")
        sys.exit(1)

    results = process_csv(str(input_csv), str(output_csv))
    print(f"\n処理完了: {len(results)}行")
    print(f"出力ファイル: {output_csv}")
