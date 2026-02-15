# GitHub Actions経由でのLINE配信システム設計書

**作成日**: 2026-02-15
**ステータス**: 承認済み

## 概要

技術記事配信サービスをGitHub Actions経由で自動化し、LINE Messaging APIでブロードキャスト配信するシステムの設計。

## 目的

- GitHub Actionsで毎日8時（JST）に自動実行
- Qiita、Zenn、TechFeedから人気記事を取得
- LINE Messaging APIでブロードキャスト配信
- Qiita APIを使用せず、スクレイピングで取得

## アーキテクチャ

### 全体フロー

```
GitHub Actions (毎日8時JST)
  ↓
1. Python環境セットアップ
  ↓
2. 記事取得
   - Qiita（スクレイピング - BeautifulSoup）
   - Zenn（既存API）
   - TechFeed（既存RSS）
  ↓
3. LINE Messaging API
   - ブロードキャスト配信
   - 全フォロワーに送信
```

### 主要コンポーネント

| ファイル | 変更 | 説明 |
|---------|------|------|
| `qiita_scraper.py` | **大** | APIからスクレイピングへ変更 |
| `zenn_scraper.py` | なし | 既存実装を維持 |
| `techfeed_scraper.py` | なし | 既存実装を維持 |
| `send_to_line.py` | なし | 既存実装を維持 |
| `main.py` | 小 | Qiita APIトークン削除 |
| `.github/workflows/daily_tech_digest.yml` | **中** | 時刻とSecrets変更 |
| `requirements.txt` | 小 | BeautifulSoup4追加 |
| `README.md` | **中** | セットアップ手順追加 |

### 環境変数

| 変数名 | 用途 | 設定場所 |
|--------|------|----------|
| `CHANNEL_ACCESS_TOKEN` | LINE Messaging API | GitHub Secrets |
| ~~`QIITA_API_TOKEN`~~ | ~~Qiita API~~（削除） | - |

## 詳細設計

### 1. Qiitaスクレイパーの変更

#### 現状
- Qiita API (`/api/v2/items`) を使用
- `QIITA_API_TOKEN` が必要
- 昨日の記事をいいね数でソート

#### 変更後
- HTMLスクレイピング方式
- BeautifulSoup4 + requests を使用
- ターゲットURL: `https://qiita.com/popular-items` または `https://qiita.com/items`

#### 実装方針
1. requests + BeautifulSoupでHTMLを取得・解析
2. 記事タイトル、URL、いいね数を抽出
3. 日付フィルタリング（昨日の記事のみ）
4. いいね数でソート、上位5件を返す
5. エラー時は空リスト `[]` を返す

#### 互換性
- 既存のインターフェース (`run()` メソッド、戻り値の形式) を維持
- `main.py` の変更は最小限

### 2. GitHub Actionsワークフロー

#### 実行スケジュール

```yaml
schedule:
  # 毎朝8時(JST) = 23時(UTC 前日)に実行
  - cron: "0 23 * * *"
```

#### トリガー
- スケジュール実行（毎日8時JST）
- 手動実行（`workflow_dispatch`）
- mainブランチへのpush（テスト用）

#### Secrets設定
1. リポジトリの Settings → Secrets and variables → Actions
2. `CHANNEL_ACCESS_TOKEN` を追加
3. 値にLINE Messaging APIのChannel Access Tokenを設定

#### 環境変数の変更
- `QIITA_API_TOKEN` を削除
- `CHANNEL_ACCESS_TOKEN` のみ使用

### 3. 動作確認とテスト

#### ローカルテスト
1. `.env` ファイルに `CHANNEL_ACCESS_TOKEN` を設定
2. `python main.py` で全体動作確認
3. 各スクレイパーの個別動作確認

#### 検証ポイント
- ✅ 各スクレイパーが記事を取得できるか
- ✅ LINE配信が正常に動作するか
- ✅ エラーハンドリングが適切か

### 4. エラーハンドリング

#### 基本方針
- 各スクレイパーでエラーが発生しても処理を継続
- 1つのサービスが失敗しても他のサービスの記事は配信
- 全て失敗した場合でも、エラーメッセージをログに記録して正常終了

#### 実装
- 各スクレイパーで `try-except` を実装
- 失敗時は空リスト `[]` を返す
- `main.py` で全て空の場合は警告ログを出力
- スクレイピング失敗時の詳細なエラー情報をログに記録

### 5. ドキュメント

#### README.mdに追加する内容

**セットアップ手順**
- LINE Messaging APIの設定方法
- GitHub Secretsの設定手順
- ローカル実行方法

**動作仕様**
- 実行スケジュール（毎日8時JST）
- 各サービスから取得する記事数
- LINE配信方式（ブロードキャスト）

**トラブルシューティング**
- GitHub Actionsのログ確認方法
- よくあるエラーと対処法

## 依存関係の変更

### requirements.txt
```
python-dotenv
line-bot-sdk
requests
feedparser
beautifulsoup4  # 追加
```

## 実装順序

1. ✅ 設計ドキュメント作成
2. Qiitaスクレイパーのスクレイピング実装
3. requirements.txtの更新
4. main.pyの軽微な修正
5. GitHub Actionsワークフローの更新
6. ローカルでの動作確認
7. README.mdの更新
8. GitHub Secretsの設定
9. GitHub Actionsでの動作確認

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| QiitaのHTML構造変更 | スクレイピング失敗 | エラー時は空リストを返し、他のサービスは継続 |
| スクレイピングのレート制限 | 一時的な取得失敗 | リトライロジック（将来的に実装） |
| LINE API制限 | 配信失敗 | エラーログを記録、次回実行で再試行 |
| GitHub Actions制限 | 実行失敗 | 手動実行で対応可能 |

## 成功基準

- ✅ GitHub Actionsが毎日8時JSTに自動実行される
- ✅ Qiita、Zenn、TechFeedから記事を取得できる
- ✅ LINEブロードキャスト配信が成功する
- ✅ エラー時も他のサービスの記事は配信される
- ✅ セットアップ手順が明確で再現可能

## 参考資料

- [LINE Messaging API ドキュメント](https://developers.line.biz/ja/docs/messaging-api/)
- [GitHub Actions ドキュメント](https://docs.github.com/ja/actions)
- [BeautifulSoup4 ドキュメント](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
