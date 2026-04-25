# トレンドウォッチャー 🔍

Google トレンドから急上昇ワードをリアルタイムで取得・表示するWebアプリ。

## 機能

- 国別切り替え（日本・アメリカ・イギリス・ドイツ・フランス）
- デイリー / リアルタイム モード切り替え
- 関連キーワード表示
- 関連ニュース記事へのリンク

## ローカルで実行

```bash
pip install -r requirements.txt
python app.py
```

ブラウザで http://localhost:8081 を開いてください。

## デプロイ（Render）

1. GitHub にプッシュ
2. [Render](https://render.com) で「New Web Service」→ リポジトリ接続
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. 「Create Web Service」をクリック
