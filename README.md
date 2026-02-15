# 技術記事配信用リポジトリ

GitHub Actions経由で技術記事を自動収集し、LINE Messaging APIでブロードキャスト配信するシステム。

## 機能

- **記事収集**: Qiita、Zennから人気記事を取得
- **自動実行**: GitHub Actionsで毎日8時（JST）に自動実行
- **LINE配信**: LINE Messaging APIでブロードキャスト配信

## セットアップ

### 1. LINE Messaging APIの設定

1. [LINE Developers](https://developers.line.biz/console/) にアクセス
2. 新規プロバイダーとMessaging APIチャネルを作成
3. チャネルアクセストークン（長期）を発行
4. トークンをコピーして保存

### 2. GitHub Secretsの設定

1. GitHubリポジトリの **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. 以下のシークレットを追加：
   - Name: `CHANNEL_ACCESS_TOKEN`
   - Value: LINE Messaging APIのチャネルアクセストークン

### 3. ローカル実行（オプション）

ローカルでテストする場合：

1. 依存関係をインストール：
   ```bash
   pip install -r requirements.txt
   ```

2. `.env` ファイルを作成：
   ```
   CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   ```

3. 実行：
   ```bash
   python main.py
   ```

## 動作仕様

### 実行スケジュール
- **自動実行**: 毎日8時（JST）
- **手動実行**: GitHub Actionsの「Run workflow」ボタンから
- **プッシュ時**: mainブランチへのpush時（テスト用）

### 記事取得
- **Qiita**: Webスクレイピング（BeautifulSoup）
- **Zenn**: 公開API

各サービスから上位5件の記事を取得し、LINEで配信します。

### LINE配信方式
- **ブロードキャスト**: 公式アカウントの全フォロワーに配信
- **メッセージ形式**: テキストメッセージ（最大5000文字）

## トラブルシューティング

### GitHub Actionsが実行されない

1. **Actionsタブ**でワークフローの実行履歴を確認
2. cron設定を確認（`.github/workflows/daily_tech_digest.yml`）
3. 手動実行で動作確認

### LINE配信が失敗する

1. `CHANNEL_ACCESS_TOKEN` が正しく設定されているか確認
2. LINEチャネルが有効化されているか確認
3. GitHub Actionsのログでエラー内容を確認

### 記事が取得できない

- 各サービスのHTML構造が変更された可能性
- エラーログを確認してスクレイパーを更新

### よくあるエラー

**`CHANNEL_ACCESS_TOKEN が設定されていません`**
- GitHub Secretsに `CHANNEL_ACCESS_TOKEN` を追加

**`LINE送信エラー`**
- トークンが正しいか確認
- LINEチャネルの設定を確認

## ログ確認

GitHub Actionsのログ：
1. リポジトリの **Actions** タブ
2. 該当のワークフロー実行をクリック
3. **Run daily digest** ステップで詳細ログを確認

## 技術スタック

- **Python 3.11**
- **BeautifulSoup4**: Qiitaスクレイピング
- **requests**: HTTP通信
- **line-bot-sdk**: LINE Messaging API
- **GitHub Actions**: 自動実行

## ライセンス

MIT License
