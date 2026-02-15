# 技術記事配信システム

技術記事の最新情報を自動取得してLINEで配信するシステムです。

## 機能

- Qiita, Zenn, GitHub Trendingから最新の技術記事を自動取得
- 毎日決まった時間にLINEで配信
- GitHub Actionsによる自動実行
- ローカル実行にも対応

## セットアップ

### 1. LINE Messaging API の設定

1. [LINE Developers](https://developers.line.biz/)にアクセス
2. 新しいプロバイダーを作成（または既存のものを選択）
3. Messaging APIチャネルを作成
4. チャネル設定から以下を取得:
   - `Channel Access Token` (長期トークンを発行)
   - `User ID` (LINE公式アカウントと友だちになり、ユーザーIDを確認)

### 2. GitHub Secrets の設定

リポジトリの Settings > Secrets and variables > Actions から以下を追加:

- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging APIのアクセストークン
- `LINE_USER_ID`: 配信先のLINE User ID

### 3. ローカル実行の場合

#### 環境変数の設定

`.env`ファイルを作成:

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_USER_ID=your_user_id
```

#### 依存関係のインストール

```bash
pip install -r requirements.txt
```

#### 実行

```bash
python main.py
```

## 動作仕様

### 実行スケジュール

- GitHub Actions: 毎日 21:00 (JST) に自動実行
- 手動実行: GitHub Actionsの "Run workflow" から実行可能

### 取得する記事

1. **Qiita**: デイリートレンド上位5件
2. **Zenn**: トレンド記事上位5件
3. **GitHub Trending**: 日次トレンドリポジトリ上位5件

### 配信方法

LINE Messaging APIを使用してプッシュメッセージで配信します。
各記事は以下の形式で送信されます:

```
【Qiita】
1. 記事タイトル
   URL
2. 記事タイトル
   URL
...
```

## トラブルシューティング

### LINE配信が届かない

1. `LINE_CHANNEL_ACCESS_TOKEN`が正しく設定されているか確認
2. `LINE_USER_ID`が正しく設定されているか確認
3. LINE公式アカウントとブロックしていないか確認
4. GitHub Actionsのログでエラーメッセージを確認

### 記事が取得できない

1. インターネット接続を確認
2. 各サイトのHTMLフォーマットが変更されていないか確認
3. `requirements.txt`の依存関係が正しくインストールされているか確認

### GitHub Actionsが実行されない

1. リポジトリの Actions が有効になっているか確認
2. `.github/workflows/daily-news.yml`が正しく配置されているか確認
3. cron設定が正しいか確認（UTC時刻で設定されています）

## 技術スタック

- Python 3.9+
- beautifulsoup4: Webスクレイピング
- requests: HTTP通信
- python-dotenv: 環境変数管理
- LINE Messaging API: メッセージ配信
- GitHub Actions: 自動実行

## ライセンス

MIT License
