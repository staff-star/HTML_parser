#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVの結果を表示するHTMLビューアーを生成
"""
import csv
from pathlib import Path
import html as html_module

def generate_viewer_html(csv_path, output_html_path):
    """CSVからHTMLビューアーを生成"""

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML生成結果ビューアー</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        .product-item {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 40px;
            overflow: hidden;
        }
        .product-header {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .product-header:hover {
            background: #34495e;
        }
        .product-code {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .toggle-icon {
            font-size: 1.2em;
            transition: transform 0.3s;
        }
        .toggle-icon.open {
            transform: rotate(180deg);
        }
        .product-content {
            display: none;
        }
        .product-content.open {
            display: block;
        }
        .tabs {
            display: flex;
            border-bottom: 2px solid #ddd;
            background: #fafafa;
            padding: 10px 20px 0;
        }
        .tab-button {
            padding: 10px 20px;
            border: none;
            background: none;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
        }
        .tab-button:hover {
            color: #333;
            background: #f0f0f0;
        }
        .tab-button.active {
            color: #2c3e50;
            border-bottom-color: #3498db;
        }
        .tab-content {
            display: none;
            padding: 20px;
        }
        .tab-content.active {
            display: block;
        }
        .preview-section {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px;
            background: white;
            margin-bottom: 20px;
        }
        .preview-section h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        .code-section {
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f8f8f8;
        }
        .code-section h3 {
            background: #e0e0e0;
            padding: 10px 15px;
            margin: 0;
            font-size: 1em;
            color: #333;
        }
        .code-content {
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        pre {
            background: white;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 0.85em;
            line-height: 1.5;
        }
        .copy-button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .copy-button:hover {
            background: #2980b9;
        }
        .copy-button.copied {
            background: #27ae60;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 HTML生成結果ビューアー</h1>
"""

    for idx, row in enumerate(rows, 1):
        product_name = html_module.escape(row.get('メインデータの商品名', ''))
        product_code = html_module.escape(row.get('メインデータの商品コード（楽天URL）', ''))

        rakuten_pc = row.get('楽天パソコン', '')
        rakuten_sp = row.get('楽天スマホ', '')
        yahoo_pc = row.get('Yahooパソコン', '')
        yahoo_sp = row.get('Yahooスマホ', '')

        html_content += f"""
        <div class="product-item">
            <div class="product-header" onclick="toggleProduct({idx})">
                <div>
                    <strong>{product_name}</strong><br>
                    <span class="product-code">商品コード: {product_code}</span>
                </div>
                <span class="toggle-icon" id="toggle-{idx}">▼</span>
            </div>
            <div class="product-content" id="content-{idx}">
                <div class="tabs">
                    <button class="tab-button active" onclick="showTab({idx}, 'rakuten-pc')">楽天PC</button>
                    <button class="tab-button" onclick="showTab({idx}, 'rakuten-sp')">楽天スマホ</button>
                    <button class="tab-button" onclick="showTab({idx}, 'yahoo-pc')">Yahoo! PC</button>
                    <button class="tab-button" onclick="showTab({idx}, 'yahoo-sp')">Yahoo! スマホ</button>
                </div>

                <div class="tab-content active" id="tab-{idx}-rakuten-pc">
                    <div class="preview-section">
                        <h3>プレビュー</h3>
                        <div>{rakuten_pc}</div>
                    </div>
                    <div class="code-section">
                        <h3>HTMLコード</h3>
                        <div class="code-content">
                            <pre>{html_module.escape(rakuten_pc)}</pre>
                            <button class="copy-button" onclick="copyCode(this, {idx}, 'rakuten-pc')">コピー</button>
                        </div>
                    </div>
                </div>

                <div class="tab-content" id="tab-{idx}-rakuten-sp">
                    <div class="preview-section">
                        <h3>プレビュー</h3>
                        <div>{rakuten_sp}</div>
                    </div>
                    <div class="code-section">
                        <h3>HTMLコード</h3>
                        <div class="code-content">
                            <pre>{html_module.escape(rakuten_sp)}</pre>
                            <button class="copy-button" onclick="copyCode(this, {idx}, 'rakuten-sp')">コピー</button>
                        </div>
                    </div>
                </div>

                <div class="tab-content" id="tab-{idx}-yahoo-pc">
                    <div class="preview-section">
                        <h3>プレビュー</h3>
                        <div>{yahoo_pc}</div>
                    </div>
                    <div class="code-section">
                        <h3>HTMLコード</h3>
                        <div class="code-content">
                            <pre>{html_module.escape(yahoo_pc)}</pre>
                            <button class="copy-button" onclick="copyCode(this, {idx}, 'yahoo-pc')">コピー</button>
                        </div>
                    </div>
                </div>

                <div class="tab-content" id="tab-{idx}-yahoo-sp">
                    <div class="preview-section">
                        <h3>プレビュー</h3>
                        <div>{yahoo_sp}</div>
                    </div>
                    <div class="code-section">
                        <h3>HTMLコード</h3>
                        <div class="code-content">
                            <pre>{html_module.escape(yahoo_sp)}</pre>
                            <button class="copy-button" onclick="copyCode(this, {idx}, 'yahoo-sp')">コピー</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
"""

    html_content += """
    </div>

    <script>
        function toggleProduct(id) {
            const content = document.getElementById('content-' + id);
            const icon = document.getElementById('toggle-' + id);
            content.classList.toggle('open');
            icon.classList.toggle('open');
        }

        function showTab(productId, tabName) {
            // すべてのタブを非アクティブに
            const product = document.getElementById('content-' + productId);
            const tabs = product.querySelectorAll('.tab-button');
            const contents = product.querySelectorAll('.tab-content');

            tabs.forEach(tab => tab.classList.remove('active'));
            contents.forEach(content => content.classList.remove('active'));

            // 選択したタブをアクティブに
            event.target.classList.add('active');
            document.getElementById('tab-' + productId + '-' + tabName).classList.add('active');
        }

        async function copyCode(button, productId, tabName) {
            const tab = document.getElementById('tab-' + productId + '-' + tabName);
            const pre = tab.querySelector('pre');
            const text = pre.textContent;

            try {
                await navigator.clipboard.writeText(text);
                button.textContent = 'コピーしました！';
                button.classList.add('copied');
                setTimeout(() => {
                    button.textContent = 'コピー';
                    button.classList.remove('copied');
                }, 2000);
            } catch (err) {
                alert('コピーに失敗しました');
            }
        }
    </script>
</body>
</html>
"""

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"ビューアーを生成しました: {output_html_path}")

if __name__ == '__main__':
    script_dir = Path(__file__).parent
    csv_path = script_dir / 'output_result.csv'
    html_path = script_dir / 'viewer.html'

    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        print("先にprocess_csv.pyを実行してください")
        exit(1)

    generate_viewer_html(csv_path, html_path)
    print(f"\nブラウザで開いてください: {html_path}")
