#!/usr/bin/env python3
"""
トレンドウォッチャー - Google トレンド リアルタイム表示（Webアプリ版）

使い方:
  pip install -r requirements.txt
  python app.py

ブラウザで http://localhost:8081 を開いてください。
終了するには Ctrl+C を押してください。
"""

import json
import os
import re
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request as flask_request

app = Flask(__name__)

REGIONS = {
    "JP": "日本",
    "US": "アメリカ",
    "GB": "イギリス",
    "DE": "ドイツ",
    "FR": "フランス",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def fetch_daily_trends(geo="JP"):
    """Fetch daily trending searches from Google Trends."""
    url = f"https://trends.google.com/trends/api/dailytrends?hl=ja&tz=-540&geo={geo}&ns=15"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    # Google prepends ")]}'" to the JSON response
    text = resp.text
    if text.startswith(")]}'"):
        text = text[5:]

    data = json.loads(text)
    trends = []

    days = data.get("default", {}).get("trendingSearchesDays", [])
    rank = 0
    for day in days:
        for search in day.get("trendingSearches", []):
            rank += 1
            title_data = search.get("title", {})
            keyword = title_data.get("query", "")
            traffic = search.get("formattedTraffic", "")

            # Related queries
            related = []
            for rq in search.get("relatedQueries", []):
                related.append(rq.get("query", ""))

            # Articles
            articles = []
            for art in search.get("articles", [])[:2]:
                articles.append({
                    "title": art.get("title", ""),
                    "source": art.get("source", ""),
                    "url": art.get("url", ""),
                })

            # Heat score (approximate from traffic string)
            heat = 90 - (rank - 1) * 4
            if heat < 5:
                heat = 5

            trends.append({
                "keyword": keyword,
                "traffic": traffic,
                "related": related[:5],
                "articles": articles,
                "heat": heat,
                "rank": rank,
            })

            if rank >= 20:
                break
        if rank >= 20:
            break

    return trends


def fetch_realtime_trends(geo="JP"):
    """Fetch realtime trending topics from Google Trends."""
    url = (
        f"https://trends.google.com/trends/api/realtimetrends"
        f"?hl=ja&tz=-540&cat=all&fi=0&fs=0&geo={geo}&ri=300&rs=20&sort=0"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    text = resp.text
    if text.startswith(")]}'"):
        text = text[5:]

    data = json.loads(text)
    trends = []
    rank = 0

    stories = data.get("storySummaries", {}).get("trendingStories", [])
    for story in stories:
        rank += 1
        # Get entity names as keywords
        entities = story.get("entityNames", [])
        keyword = "、".join(entities[:3]) if entities else "不明"

        # Articles
        articles = []
        for art in story.get("articles", [])[:2]:
            articles.append({
                "title": art.get("articleTitle", ""),
                "source": art.get("source", ""),
                "url": art.get("url", ""),
            })

        heat = 95 - (rank - 1) * 4
        if heat < 5:
            heat = 5

        trends.append({
            "keyword": keyword,
            "traffic": "",
            "related": entities[:5],
            "articles": articles,
            "heat": heat,
            "rank": rank,
        })

        if rank >= 20:
            break

    return trends


@app.route("/")
def index():
    return HTML_PAGE


@app.route("/api/trends")
def api_trends():
    geo = flask_request.args.get("geo", "JP")
    mode = flask_request.args.get("mode", "daily")

    try:
        if mode == "realtime":
            trends = fetch_realtime_trends(geo)
        else:
            trends = fetch_daily_trends(geo)
        return jsonify({"trends": trends, "geo": geo, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


HTML_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>トレンドウォッチャー - Google Trends</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700;900&family=DM+Mono:wght@400;500&display=swap');

  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface-hover: #1a1a26;
    --border: #2a2a3a;
    --text: #e8e8f0;
    --text-dim: #8888a0;
    --accent: #ff6b4a;
    --accent-glow: rgba(255, 107, 74, 0.15);
    --rank-gold: #ffd700;
    --rank-silver: #c0c0d0;
    --rank-bronze: #cd7f32;
    --up: #4ade80;
    --link: #6eb5ff;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans JP', sans-serif;
    min-height: 100vh;
  }

  .container {
    max-width: 800px;
    margin: 0 auto;
    padding: 36px 20px;
  }

  header { margin-bottom: 28px; }

  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .logo-icon {
    width: 38px; height: 38px;
    background: var(--accent);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 900;
    color: var(--bg);
    box-shadow: 0 0 20px var(--accent-glow);
  }

  h1 { font-size: 21px; font-weight: 700; }
  .subtitle { color: var(--text-dim); font-size: 12px; margin-top: 3px; }

  .controls {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
    flex-wrap: wrap;
    align-items: center;
  }

  .tab {
    padding: 7px 14px;
    border-radius: 18px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    font-family: 'Noto Sans JP', sans-serif;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab:hover { border-color: var(--accent); color: var(--text); }
  .tab.active { background: var(--accent); border-color: var(--accent); color: var(--bg); font-weight: 500; }

  .mode-controls {
    display: flex;
    gap: 6px;
    margin-bottom: 20px;
    align-items: center;
  }

  .mode-btn {
    padding: 5px 12px;
    border-radius: 14px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    font-family: 'Noto Sans JP', sans-serif;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .mode-btn:hover { border-color: var(--accent); color: var(--text); }
  .mode-btn.active { background: var(--surface); border-color: var(--accent); color: var(--accent); font-weight: 500; }

  .fetch-btn {
    padding: 7px 18px;
    border-radius: 18px;
    border: none;
    background: var(--accent);
    color: var(--bg);
    font-family: 'Noto Sans JP', sans-serif;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    margin-left: auto;
  }

  .fetch-btn:hover { opacity: 0.85; }
  .fetch-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .info-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    font-size: 11px;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
  }

  .status-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

  .update-time {
    font-family: 'DM Mono', monospace;
    color: var(--text-dim);
  }

  .trend-list {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .trend-item {
    display: grid;
    grid-template-columns: 44px 1fr auto;
    align-items: center;
    gap: 16px;
    padding: 14px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    animation: slideIn 0.35s ease-out both;
  }

  .trend-item:hover {
    background: var(--surface-hover);
    border-color: rgba(255,107,74,0.3);
    transform: translateX(3px);
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-16px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .rank-num {
    font-family: 'DM Mono', monospace;
    font-size: 20px;
    font-weight: 500;
    text-align: center;
  }

  .rank-1 .rank-num { color: var(--rank-gold); }
  .rank-2 .rank-num { color: var(--rank-silver); }
  .rank-3 .rank-num { color: var(--rank-bronze); }
  .trend-item:not(.rank-1):not(.rank-2):not(.rank-3) .rank-num { color: var(--text-dim); }

  .trend-keyword {
    font-size: 15px;
    font-weight: 500;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .expand-hint {
    font-size: 10px;
    color: var(--text-dim);
    transition: transform 0.3s;
  }

  .trend-item.expanded .expand-hint { transform: rotate(180deg); }

  .trend-meta {
    font-size: 11px;
    color: var(--text-dim);
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .traffic-badge {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--accent);
    font-weight: 500;
  }

  .heat-bar {
    width: 60px; height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }

  .heat-bar-fill { height: 100%; border-radius: 2px; background: var(--accent); }

  .detail-panel {
    grid-column: 1 / -1;
    overflow: hidden;
    max-height: 0;
    transition: max-height 0.4s ease-out, padding 0.4s ease-out;
  }

  .trend-item.expanded .detail-panel {
    max-height: 600px;
    padding: 12px 0 4px;
  }

  .detail-section {
    margin-bottom: 10px;
  }

  .detail-label {
    font-size: 11px;
    color: var(--accent);
    font-weight: 500;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .detail-label::before {
    content: '';
    width: 12px; height: 1px;
    background: var(--accent);
  }

  .related-tags { display: flex; flex-wrap: wrap; gap: 6px; }

  .related-tag {
    font-size: 12px;
    padding: 5px 12px;
    border-radius: 16px;
    background: rgba(255,107,74,0.08);
    border: 1px solid rgba(255,107,74,0.2);
    color: var(--text);
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
  }

  .related-tag:hover {
    background: rgba(255,107,74,0.18);
    border-color: var(--accent);
    transform: translateY(-1px);
  }

  .article-link {
    display: block;
    padding: 6px 0;
    text-decoration: none;
    color: var(--link);
    font-size: 12px;
    line-height: 1.5;
    transition: opacity 0.2s;
  }

  .article-link:hover { opacity: 0.8; }

  .article-source {
    color: var(--text-dim);
    font-size: 10px;
    font-family: 'DM Mono', monospace;
  }

  .msg-area {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 14px;
    line-height: 1.8;
  }

  .spinner {
    width: 28px; height: 28px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    margin: 0 auto 14px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-dim);
    font-size: 10px;
    line-height: 1.8;
  }

  .footer a { color: var(--accent); text-decoration: none; }

  @media (max-width: 480px) {
    .container { padding: 20px 14px; }
    h1 { font-size: 18px; }
    .trend-item { grid-template-columns: 36px 1fr auto; gap: 10px; padding: 12px; }
    .fetch-btn { margin-left: 0; width: 100%; margin-top: 6px; }
    .heat-bar { width: 40px; }
  }
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="logo">
      <div class="logo-icon">T</div>
      <div>
        <h1>トレンドウォッチャー</h1>
        <div class="subtitle">Google トレンドから話題のトピックをリアルタイム表示</div>
      </div>
    </div>
  </header>

  <div class="controls">
    <button class="tab active" data-geo="JP">日本</button>
    <button class="tab" data-geo="US">アメリカ</button>
    <button class="tab" data-geo="GB">イギリス</button>
    <button class="tab" data-geo="DE">ドイツ</button>
    <button class="tab" data-geo="FR">フランス</button>
    <button class="fetch-btn" id="fetchBtn">トレンドを取得</button>
  </div>

  <div class="mode-controls">
    <button class="mode-btn active" data-mode="daily">デイリー</button>
    <button class="mode-btn" data-mode="realtime">リアルタイム</button>
  </div>

  <div class="info-bar">
    <div class="status">
      <div class="status-dot" id="statusDot" style="background:var(--accent)"></div>
      <span id="statusText" style="color:var(--accent)">READY</span>
    </div>
    <span class="update-time" id="updateTime"></span>
  </div>

  <div id="trendList" class="trend-list">
    <div class="msg-area">
      <div style="font-size:28px; margin-bottom:10px;">🔍</div>
      「トレンドを取得」を押すと、<br>Google トレンドのデータを表示します。
    </div>
  </div>

  <div class="footer">
    データソース: <a href="https://trends.google.com" target="_blank">Google Trends</a><br><br>
    <strong>このアプリについて</strong><br>
    Google トレンドの「急上昇ワード」を取得し、検索ボリューム順に表示します。<br>
    デイリーモードはその日の急上昇ワード、リアルタイムモードは直近の話題を表示します。<br>
    各トピックをクリックすると、関連キーワードと関連ニュース記事が展開されます。
  </div>
</div>

<script>
let currentGeo = 'JP';
let currentMode = 'daily';

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentGeo = tab.dataset.geo;
  });
});

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentMode = btn.dataset.mode;
  });
});

document.getElementById('fetchBtn').addEventListener('click', fetchTrends);

function updateTime() {
  document.getElementById('updateTime').textContent =
    new Date().toLocaleString('ja-JP', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
}

function setStatus(color, text) {
  document.getElementById('statusDot').style.background = color;
  const st = document.getElementById('statusText');
  st.style.color = color;
  st.textContent = text;
}

function getRankClass(i) {
  return i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : '';
}

function renderTrends(trends) {
  const list = document.getElementById('trendList');
  list.innerHTML = trends.map((t, i) => `
    <div class="trend-item ${getRankClass(i)}" style="animation-delay:${i*0.04}s">
      <div class="rank-num">${String(i+1).padStart(2,'0')}</div>
      <div>
        <div class="trend-keyword">${t.keyword} <span class="expand-hint">▼</span></div>
        <div class="trend-meta">
          ${t.traffic ? `<span class="traffic-badge">${t.traffic} 検索</span>` : ''}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
        <div class="heat-bar"><div class="heat-bar-fill" style="width:${t.heat}%"></div></div>
      </div>
      <div class="detail-panel">
        ${t.related && t.related.length > 0 ? `
          <div class="detail-section">
            <div class="detail-label">関連キーワード</div>
            <div class="related-tags">
              ${t.related.map(r => `<a class="related-tag" href="https://www.google.com/search?q=${encodeURIComponent(r)}" target="_blank" onclick="event.stopPropagation()">${r}</a>`).join('')}
            </div>
          </div>
        ` : ''}
        ${t.articles && t.articles.length > 0 ? `
          <div class="detail-section">
            <div class="detail-label">関連ニュース</div>
            ${t.articles.map(a => `
              <a class="article-link" href="${a.url}" target="_blank" onclick="event.stopPropagation()">
                ${a.title} <span class="article-source">${a.source}</span>
              </a>
            `).join('')}
          </div>
        ` : ''}
      </div>
    </div>
  `).join('');

  document.querySelectorAll('.trend-item').forEach(el => {
    el.addEventListener('click', () => el.classList.toggle('expanded'));
  });
}

async function fetchTrends() {
  const btn = document.getElementById('fetchBtn');
  const list = document.getElementById('trendList');

  btn.disabled = true;
  btn.textContent = '取得中...';
  setStatus('var(--accent)', 'LOADING');
  list.innerHTML = '<div class="msg-area"><div class="spinner"></div>Google トレンドから取得中...</div>';

  try {
    const resp = await fetch(`/api/trends?geo=${currentGeo}&mode=${currentMode}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    if (data.error) throw new Error(data.error);

    if (data.trends && data.trends.length > 0) {
      renderTrends(data.trends);
      setStatus('var(--up)', 'LIVE');
      updateTime();
    } else {
      throw new Error('トレンドが取得できませんでした');
    }
  } catch (err) {
    list.innerHTML = `<div class="msg-area" style="color:var(--accent)">
      取得に失敗しました。<br>
      <span style="font-size:12px;color:var(--text-dim)">${err.message}</span>
    </div>`;
    setStatus('var(--accent)', 'ERROR');
  }

  btn.disabled = false;
  btn.textContent = 'トレンドを取得';
}

updateTime();
setInterval(updateTime, 1000);
fetchTrends();
</script>

</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    print(f"\\n  🔍 トレンドウォッチャー Web版")
    print(f"  http://localhost:{port} でアクセスしてください\\n")
    app.run(host="0.0.0.0", port=port, debug=False)
