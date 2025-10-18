import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';

const MAX_INPUT_LENGTH = 100_000;
const API_ENDPOINT = '/api/generate';

const TAB_CONFIG = [
  { key: 'rakuten_pc', label: '楽天 PC' },
  { key: 'rakuten_sp', label: '楽天 スマホ' },
  { key: 'yahoo_pc', label: 'Yahoo! PC' },
  { key: 'yahoo_sp', label: 'Yahoo! スマホ' },
];

const FIELD_LABELS = {
  product_name: '商品名',
  product_type: '名称',
  ingredients: '原材料',
  content: '内容量',
  expiry: '賞味期限',
  storage: '保存方法',
  seller: '販売者',
  manufacturer: '製造者',
  processor: '加工者',
  importer: '輸入者',
};

const LOG_LEVEL_CLASS = {
  info: 'log-item info',
  warning: 'log-item warning',
  error: 'log-item error',
};

const SAMPLE_PLACEHOLDER = `■商品名：蒜山高原ミックスチョコレート\n■名称：チョコレート\n■原材料：チョコレート(砂糖、ココアバター...)\n■内容量：300g\n■賞味期限：製造より180日\n■保存方法：28℃以下で保存\n■販売者：株式会社天然生活\n【栄養成分表示(100g当たり)】（推定値）\nエネルギー：595kcal\nたんぱく質：6.7g\n脂質：41.0g\n炭水化物：49.9g\n食塩相当量：0.3g\n※本品製造工場では...`;

function formatNumber(value) {
  return value.toLocaleString('ja-JP');
}

export default function App() {
  const [inputText, setInputText] = useState('');
  const [inputMode, setInputMode] = useState('text');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState(TAB_CONFIG[0].key);
  const [logsOpen, setLogsOpen] = useState(false);
  const [copiedTab, setCopiedTab] = useState('');

  const charCount = inputText.length;
  const charCountLabel = `${formatNumber(charCount)} / ${formatNumber(MAX_INPUT_LENGTH)} 文字`;

  const productSummary = useMemo(() => {
    if (!result?.product_info) {
      return [];
    }
    const entries = Object.entries(FIELD_LABELS)
      .map(([key, label]) => ({ key, label, value: result.product_info[key] }))
      .filter((entry) => entry.value);
    return entries;
  }, [result]);

  const nutritionSummary = useMemo(() => {
    if (!result?.product_info?.nutrition) {
      return [];
    }
    return Object.entries(result.product_info.nutrition).map(([key, value]) => ({ key, value }));
  }, [result]);

  const handleGenerate = useCallback(async () => {
    if (!inputText.trim()) {
      setErrorMessage('入力が空です。商品情報を貼り付けてください。');
      return;
    }
    if (inputText.length > MAX_INPUT_LENGTH) {
      setErrorMessage('入力が長すぎます（最大100,000文字）。不要なテキストを削除してください。');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');

    try {
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: inputText,
          type: inputMode,
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        setErrorMessage(data.error || '解析に失敗しました。入力内容をご確認ください。');
        return;
      }

      setResult(data);
      setActiveTab(TAB_CONFIG[0].key);
      setLogsOpen(false);
    } catch (error) {
      setErrorMessage('サーバーへの接続に失敗しました。ネットワークをご確認ください。');
    } finally {
      setIsLoading(false);
    }
  }, [inputText, inputMode]);

  useEffect(() => {
    const shortcutHandler = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'enter') {
        event.preventDefault();
        handleGenerate();
      }
    };
    window.addEventListener('keydown', shortcutHandler);
    return () => window.removeEventListener('keydown', shortcutHandler);
  }, [handleGenerate]);

  const handleCopy = useCallback(async (tabKey) => {
    if (!result?.html?.[tabKey]) {
      return;
    }
    try {
      await navigator.clipboard.writeText(result.html[tabKey]);
      setCopiedTab(tabKey);
      setTimeout(() => setCopiedTab(''), 2000);
    } catch (error) {
      setErrorMessage('クリップボードへのコピーに失敗しました。ブラウザの設定をご確認ください。');
    }
  }, [result]);

  const handleFile = useCallback((file) => {
    if (!file) {
      return;
    }
    if (!file.type.includes('csv') && !file.name.toLowerCase().endsWith('.csv')) {
      setErrorMessage('CSVファイルを選択してください。');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result?.toString() ?? '';
      setInputText(text);
      setInputMode('csv');
      setUploadedFileName(file.name);
      setErrorMessage('');
    };
    reader.onerror = () => setErrorMessage('ファイルの読み込みに失敗しました。');
    reader.readAsText(file, 'utf-8');
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    setIsDragActive(false);
    const file = event.dataTransfer.files?.[0];
    handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((event) => {
    event.preventDefault();
    setIsDragActive(false);
  }, []);

  const currentHtml = result?.html?.[activeTab] ?? '';
  const logs = result?.logs ?? [];
  const userLogs = result?.user_logs ?? [];

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>楽天市場・Yahoo! HTMLジェネレーター</h1>
        <p className="lead">
          バラバラな商品情報を貼り付けるだけで、楽天・Yahoo! 向けのHTMLを自動生成します。
        </p>
      </header>

      <main className="main-content">
        <section className="panel input-panel">
          <div className="panel-header">
            <h2>入力</h2>
            <div className="mode-toggle" role="group" aria-label="入力モード">
              <button
                type="button"
                className={inputMode === 'text' ? 'active' : ''}
                onClick={() => setInputMode('text')}
              >
                テキスト
              </button>
              <button
                type="button"
                className={inputMode === 'csv' ? 'active' : ''}
                onClick={() => setInputMode('csv')}
              >
                CSV
              </button>
            </div>
          </div>

          <div
            className={`drop-zone ${isDragActive ? 'active' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <p>CSVファイルをドラッグ＆ドロップ、または下のボタンから選択</p>
            <label className="file-button">
              ファイルを選択
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => handleFile(event.target.files?.[0])}
              />
            </label>
            {uploadedFileName && <p className="file-name">選択中: {uploadedFileName}</p>}
          </div>

          <label className="textarea-label" htmlFor="inputText">
            商品情報
            <span className={charCount > MAX_INPUT_LENGTH ? 'char-count error' : 'char-count'}>
              {charCountLabel}
            </span>
          </label>
          <textarea
            id="inputText"
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            placeholder={SAMPLE_PLACEHOLDER}
            rows={20}
            className="input-textarea"
          />

          <div className="actions">
            <button
              type="button"
              className="primary-button"
              onClick={handleGenerate}
              disabled={isLoading}
            >
              {isLoading ? '解析中…' : 'HTMLを生成'}
            </button>
            <span className="shortcut-hint">ショートカット: Ctrl / ⌘ + Enter</span>
          </div>

          {errorMessage && <div className="error-banner">{errorMessage}</div>}
        </section>

        <section className="panel output-panel">
          <div className="panel-header">
            <h2>出力</h2>
            {result?.product_info?.product_name && (
              <span className="result-status">解析済み: {result.product_info.product_name}</span>
            )}
          </div>

          {!result && (
            <div className="empty-state">
              <p>右の入力欄にテキストを貼り付け、「HTMLを生成」を押してください。</p>
            </div>
          )}

          {result && (
            <>
              <div className="tab-header">
                {TAB_CONFIG.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    className={activeTab === tab.key ? 'tab-button active' : 'tab-button'}
                    onClick={() => setActiveTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="tab-content">
                {currentHtml ? (
                  <div className="preview">
                    <h3>プレビュー</h3>
                    <div
                      className="preview-body"
                      dangerouslySetInnerHTML={{ __html: currentHtml }}
                    />
                  </div>
                ) : (
                  <div className="empty-preview">このタブのHTMLは生成されませんでした。</div>
                )}

                <div className="code-block">
                  <div className="code-header">
                    <h3>HTMLコード</h3>
                    <button type="button" className="secondary-button" onClick={() => handleCopy(activeTab)}>
                      {copiedTab === activeTab ? 'コピーしました！' : 'コピー'}
                    </button>
                  </div>
                  <textarea
                    readOnly
                    value={currentHtml}
                    className="code-textarea"
                    spellCheck={false}
                  />
                </div>
              </div>

              <div className="summary-grid">
                {productSummary.length > 0 && (
                  <div className="summary-card">
                    <h3>抽出された商品情報</h3>
                    <ul>
                      {productSummary.map((item) => (
                        <li key={item.key}>
                          <span className="summary-label">{item.label}</span>
                          <span className="summary-value">{item.value}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {nutritionSummary.length > 0 && (
                  <div className="summary-card">
                    <h3>栄養成分</h3>
                    <ul>
                      {nutritionSummary.map((item) => (
                        <li key={item.key}>
                          <span className="summary-label">{item.key}</span>
                          <span className="summary-value">{item.value}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="logs-section">
                <button type="button" className="log-toggle" onClick={() => setLogsOpen((open) => !open)}>
                  {logsOpen ? 'ログを閉じる' : 'ログを表示'}
                </button>
                {logsOpen && (
                  <div className="logs-body">
                    {userLogs.length > 0 && (
                      <div className="user-logs">
                        <h4>処理メモ</h4>
                        <ul>
                          {userLogs.map((log, index) => (
                            <li key={index}>{log}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {logs.length > 0 && (
                      <div className="parser-logs">
                        <h4>詳細ログ</h4>
                        <ul>
                          {logs.map((log, index) => {
                            const className = LOG_LEVEL_CLASS[log.level] || LOG_LEVEL_CLASS.info;
                            return (
                              <li key={`${log.level}-${index}`} className={className}>
                                <span className="log-level">[{log.level}]</span>
                                <span className="log-message">{log.message}</span>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                    {logs.length === 0 && userLogs.length === 0 && (
                      <p className="empty-logs">ログはありません。</p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <p>超柔軟パーサー方針: エラーで止めず、読み取れた情報を最優先で提供します。</p>
      </footer>
    </div>
  );
}
