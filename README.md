# 楽天市場・Yahoo! HTMLジェネレーター

超柔軟なパーサーでバラバラな商品情報を解析し、楽天市場とYahoo!ショッピング向けのHTMLを一括生成するツールです。ExcelやPDFからのコピペ、CSVファイル、崩れたテキストでも可能な限り情報を抽出します。

## 特徴

- **超柔軟なパース**: 項目名の表記ゆれ、順不同、全角/半角混在、箇条書きなどに対応。
- **4種類のHTMLを同時生成**: 楽天PC/スマホ、Yahoo! PC/スマホの4パターンを生成し、プレビューとコードを提供。
- **CSVサポート**: 区切り文字自動判定・ヘッダー検出・栄養成分のセクション化まで自動化。
- **安全設計**: 入力サイズ制限、危険タグ検出、XSS対策済みのHTMLエスケープを実装。
- **ログ出力**: パース結果を警告レベル付きで取得でき、原因調査が容易。
- **Vercel対応**: Python Serverless FunctionとReactフロントエンドを同一プロジェクトでデプロイ可能。

## プロジェクト構成

```
├── api/
│   └── generate.py          # Vercel Python Serverless Function
├── docs/
│   ├── good_examples.md
│   ├── bad_examples.md
│   └── faq.md
├── public/
│   └── index.html
├── src/
│   ├── App.jsx
│   ├── App.css
│   ├── index.jsx
│   └── index.css
├── tests/
│   └── test_parser.py
├── package.json
├── requirements.txt
├── vercel.json
├── vite.config.js
└── README.md
```

## セットアップ

### 前提条件

- Node.js 18 以上
- npm 9 以上
- Python 3.10 以上
- Vercel CLI (任意 / デプロイ時)

### 依存関係のインストール

```bash
# フロントエンド依存関係
npm install

# (オプション) Python仮想環境
python -m venv .venv
source .venv/bin/activate  # Windowsは .venv\Scripts\activate
pip install -r requirements.txt  # 現時点で外部依存はありません
```

> **メモ:** 環境によってnpmキャッシュが破損している場合があります。`npm cache clean --force` を実行してから再試行してください。

### ローカル開発

```bash
# Reactフロントエンド (Vite)
npm run dev

# Vercel Dev (バックエンド) - 別ターミナルで実行
vercel dev
```

### テスト

Pythonのユニットテストで主要なパーサー挙動をカバーしています。

```bash
python -m unittest discover
```

## API 仕様

### エンドポイント

- `POST /api/generate`

### リクエスト例

```json
{
  "text": "■商品名：テスト\n名称：スイーツ",
  "type": "text"  // text | csv
}
```

### レスポンス例

```json
{
  "success": true,
  "html": {
    "rakuten_pc": "<div>...</div>",
    "rakuten_sp": "<p>...</p>",
    "yahoo_pc": "<section>...</section>",
    "yahoo_sp": "<div>...</div>"
  },
  "product_info": {
    "product_name": "テスト",
    "nutrition": { "energy": "595kcal" },
    "extra_fields": {}
  },
  "logs": [
    { "level": "info", "message": "product_nameを抽出..." },
    { "level": "warning", "message": "sellerが見つかりませんでした" }
  ],
  "user_logs": ["解析とHTML生成が完了しました。"],
  "normalized_text": "...",
  "input_type": "text"
}
```

## フロントエンド機能

- テキストエリア (Ctrl / ⌘ + Enterで送信、文字数カウント付き)
- CSVドラッグ&ドロップ + ボタン選択
- 4種類のHTMLタブ表示 (プレビュー + コード + コピー)
- ログビューア (警告レベル別カラーリング)
- 解析結果サマリー (商品情報 / 栄養成分)

## バックエンド実装ポイント

- `FlexibleParser` が前処理 → 多段抽出 → 栄養成分処理 → 未知項目検出を担当
- `HTMLGenerator` が楽天/Yahoo! 4種のHTMLを生成
- `process_input` が入力安全性チェック、CSV解析、ロガー統合を行う
- セキュリティ: 入力長制限・危険タグ検出・HTMLエスケープ・CORS対応済み

## デプロイ

1. Vercel CLIでログインし、初期設定を行う
2. `vercel` または `vercel --prod`
3. 自動的に `api/generate.py` がServerless Functionとして、`npm run build` の成果物が静的ホスティングとして配備されます

## トラブルシューティング

| 症状 | 対応 |
| --- | --- |
| npm インストール時に TAR エラー | `npm cache clean --force` を実行し、再度 `npm install`|
| 入力が長すぎるエラー | 不要行を削除するか、CSV入力をテキストに変換した上で分割してください |
| ログに警告が多い | 重要な項目が欠落している可能性があります。`docs/good_examples.md` を参照し補完してください |

## 参考ドキュメント

- `docs/good_examples.md`: 良い入力例
- `docs/bad_examples.md`: 失敗入力パターンと改善策
- `docs/faq.md`: よくある質問と回答

---

柔軟性重視のツールです。不完全な入力でもまずはHTMLを返すことを設計ポリシーとしています。改善アイデア・追加要件があればIssue等でご連絡ください。
