#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV処理とビューアー生成を一括実行
"""
import subprocess
import sys
from pathlib import Path
import webbrowser

def main():
    script_dir = Path(__file__).parent

    print("=" * 60)
    print("CSV処理ツール - 一括実行")
    print("=" * 60)

    # Step 1: CSV処理
    print("\n[Step 1/2] CSVファイルを処理中...")
    process_script = script_dir / 'process_csv.py'
    result = subprocess.run([sys.executable, str(process_script)])

    if result.returncode != 0:
        print("\nエラー: CSV処理に失敗しました")
        return

    # Step 2: ビューアー生成
    print("\n[Step 2/2] ビューアーを生成中...")
    viewer_script = script_dir / 'generate_viewer.py'
    result = subprocess.run([sys.executable, str(viewer_script)])

    if result.returncode != 0:
        print("\nエラー: ビューアー生成に失敗しました")
        return

    # ブラウザで開く
    viewer_html = script_dir / 'viewer.html'
    if viewer_html.exists():
        print("\n" + "=" * 60)
        print("✅ 完了しました！")
        print("=" * 60)
        print(f"\n出力ファイル:")
        print(f"  - CSV: {script_dir / 'output_result.csv'}")
        print(f"  - HTML: {viewer_html}")

        print("\nブラウザでビューアーを開きます...")
        webbrowser.open(str(viewer_html))
    else:
        print("\nエラー: ビューアーファイルが見つかりません")

if __name__ == '__main__':
    main()
