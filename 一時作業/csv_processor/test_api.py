#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# 親ディレクトリのapiモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'api'))
from generate import FlexibleParser, HTMLGenerator

# テストテキスト（■記号なし）
test_text = """品名:宇治抹茶

原材料名:緑茶(国産)

内容量:200g

賞味期限:製造より常温180日(約60〜180日弱賞味期限が残ったものでのお届けとなります）

保存方法:高温多湿を避け移り香に御注意下さい

販売者:株式会社天然生活
〒141-0032　東京都品川区大崎3-6-4　トキワビル7F"""

print("=== テスト入力 ===")
print(test_text)
print("\n")

parser = FlexibleParser()
product_info = parser.parse(test_text)

print("=== パース結果 ===")
print(f"product_name: {product_info.product_name}")
print(f"ingredients: {product_info.ingredients}")
print(f"content: {product_info.content}")
print(f"expiry: {product_info.expiry}")
print(f"storage: {product_info.storage}")
print(f"seller: {product_info.seller}")
print(f"extra_fields: {product_info.extra_fields}")
print("\n")

generator = HTMLGenerator()
html_variants = generator.generate_all(product_info)

yahoo_pc = html_variants['yahoo_pc']
print("=== Yahoo PC HTML ===")
print(yahoo_pc)
print("\n")

print("=== 重複チェック ===")
print(f"原材料の出現回数: {yahoo_pc.count('原材料')}")
print(f"内容量の出現回数: {yahoo_pc.count('内容量')}")
