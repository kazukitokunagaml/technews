# セットアップ手順：Discord + Pinecone + Vercel

> **実装は完了済み。** このドキュメントはサービスを実際に動かすために必要な外部サービスの設定手順をまとめたもの。

---

## 全体の流れ

```
[1] Pinecone Index 作成
[2] Google API Key 取得
[3] Discord Webhook 作成          ← 日次配信（GitHub Actions）
[4] Discord Application 作成      ← /ask コマンド（Vercel）
[5] Vercel デプロイ & 環境変数設定
[6] Discord に Interactions URL 登録
[7] スラッシュコマンド /ask 登録
[8] GitHub Secrets 設定
```

---

## [1] Pinecone Index を作成する

1. [https://app.pinecone.io](https://app.pinecone.io) にログイン
2. **Create Index** をクリック
3. 以下の設定で作成する

   | 項目 | 値 |
   |---|---|
   | Index Name | `tech-articles`（任意。後で環境変数に使う） |
   | Dimensions | `768` |
   | Metric | `Cosine` |
   | Type | `Serverless` |
   | Cloud / Region | `AWS / us-east-1` |

4. **API Keys** メニューから API Key をコピーして手元に控える

---

## [2] Google API Key（Gemini）を取得する

1. [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) を開く
2. **Create API Key** → プロジェクトを選択してキーを生成
3. 表示された API Key を手元に控える

---

## [3] Discord Webhook を作成する（日次配信用）

GitHub Actions が毎朝記事をこのチャンネルに投稿する。

1. Discord で記事を投稿したいチャンネルを開く
2. チャンネル名を右クリック → **チャンネルの編集**
3. **連携サービス** → **ウェブフック** → **新しいウェブフック**
4. 名前を設定（例: `TechDigest`）して **ウェブフック URL をコピー**
5. コピーした URL を手元に控える

---

## [4] Discord Application を作成する（/ask コマンド用）

Vercel 上の RAG チャットボットをスラッシュコマンドで呼び出す。

1. [https://discord.com/developers/applications](https://discord.com/developers/applications) を開く
2. **New Application** → 名前を入力（例: `TechBot`）して作成
3. **General Information** ページを開き **PUBLIC KEY** をコピー → 手元に控える
4. 左メニュー **Bot** → **Reset Token** → Token をコピー → 手元に控える
   - ※ Token は一度しか表示されないので必ず保存する
5. **OAuth2 → URL Generator** でボットをサーバーに招待する
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`
   - 生成された URL をブラウザで開いてサーバーに追加

---

## [5] Vercel にデプロイして環境変数を設定する

### デプロイ

```bash
# Vercel CLI でデプロイする場合
npm i -g vercel
vercel --prod
```

または GitHub リポジトリを Vercel ダッシュボードからインポートしてデプロイ。

### Vercel の環境変数を設定する

Vercel ダッシュボード → プロジェクト → **Settings → Environment Variables** で以下を追加。

| 変数名 | 値 |
|---|---|
| `DISCORD_PUBLIC_KEY` | [4] で控えた PUBLIC KEY |
| `GOOGLE_API_KEY` | [2] で控えた Google API Key |
| `PINECONE_API_KEY` | [1] で控えた Pinecone API Key |
| `PINECONE_INDEX_NAME` | [1] で作成した Index 名（例: `tech-articles`） |

> `DISCORD_WEBHOOK_URL` と Bot Token は Vercel 側では不要。

---

## [6] Discord に Interactions Endpoint URL を登録する

Vercel デプロイ後に実施する。

1. [https://discord.com/developers/applications](https://discord.com/developers/applications) → 作成した Application を開く
2. **General Information** → **Interactions Endpoint URL** に以下を入力して保存

   ```
   https://<your-vercel-domain>/api/index
   ```

3. Discord 側が疎通確認（PING）を送るので、`vercel.json` と `api/index.py` が正常にデプロイされていれば自動で検証が通る

---

## [7] スラッシュコマンド /ask を登録する

Interactions URL 登録後、以下のコマンドを一度だけ実行してスラッシュコマンドを Discord に登録する。

```bash
# APPLICATION_ID は Discord Developer Portal の General Information で確認
export DISCORD_APPLICATION_ID="<your-application-id>"
export DISCORD_BOT_TOKEN="<your-bot-token>"

curl -X POST \
  "https://discord.com/api/v10/applications/${DISCORD_APPLICATION_ID}/commands" \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ask",
    "description": "テック記事について質問する",
    "options": [
      {
        "name": "question",
        "description": "質問内容",
        "type": 3,
        "required": true
      }
    ]
  }'
```

登録後、Discord サーバーで `/ask question:Rustの最新動向は？` のように使える。

---

## [8] GitHub Secrets を設定する

GitHub リポジトリ → **Settings → Secrets and variables → Actions** で以下を追加。

| Secret 名 | 値 |
|---|---|
| `DISCORD_WEBHOOK_URL` | [3] で控えた Webhook URL |
| `GOOGLE_API_KEY` | [2] で控えた Google API Key |
| `PINECONE_API_KEY` | [1] で控えた Pinecone API Key |
| `PINECONE_INDEX_NAME` | [1] で作成した Index 名 |

---

## 動作確認

### 日次配信（GitHub Actions）

GitHub → Actions → **Daily Tech Digest** → **Run workflow** で手動実行し、Discord チャンネルにメッセージが届くか確認する。

### RAG チャットボット（Vercel）

Discord サーバーで `/ask question:生成AIの最新記事を教えて` を実行し、Pinecone から記事が取得され Gemini が回答を返すか確認する。

> **注意:** `/ask` が機能するには先に GitHub Actions が少なくとも一度実行されて Pinecone に記事が保存されている必要がある。

---

## トラブルシューティング

| 症状 | 確認箇所 |
|---|---|
| Vercel の Interactions 検証が通らない | `DISCORD_PUBLIC_KEY` が正しいか確認 |
| `/ask` が「記事が見つかりません」と返す | GitHub Actions を手動実行して Pinecone にデータを入れる |
| GitHub Actions が失敗する | Actions ログで `PINECONE_API_KEY` / `GOOGLE_API_KEY` のエラーを確認 |
| Vercel が 10 秒でタイムアウトする | `gemini-2.0-flash` を使っているか `api/index.py` を確認 |
