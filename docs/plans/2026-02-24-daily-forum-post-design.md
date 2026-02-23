# Design: 1日1フォーラムスレッド構成

Date: 2026-02-24

## 概要

現在は記事ごとに個別フォーラムスレッドを作成しているが、
1日1スレッドにまとめて10記事 + 各要約をスレッド内に投稿する構成に変更する。

## 新しいフロー

```
1. Qiita 5件 + Zenn 5件 = 10件取得・要約 (既存通り)
2. フォーラムに日次スレッド作成
   - thread_name: "YYYY-MM-DD テックニュース"
   - 最初のメッセージ: 10記事の番号付きリスト (タイトル + URL)
3. 各記事の要約を順番にスレッドへ投稿 (×10)
   - 📌 タイトル\n URL\n **要約:**\n - ポイント...
```

## 変更ファイル

### send_to_discord.py

- `send_article_with_summary()` を削除
- `create_daily_forum_post(articles: list[dict], summaries: list[str]) -> None` を追加
  1. `thread_name` 付きで forum webhook に POST → `channel_id` (thread_id) 取得
  2. 10件の要約を `thread_id` 付き webhook に順番に POST

### main.py

- ループ内で1件ずつ Discord 送信する処理を削除
- 全件処理後に `messenger.create_daily_forum_post(all_articles, summaries)` を呼ぶ

## データフロー

```
main.py
  ├─ articles: list[dict]  (title, url, published_date)
  ├─ summaries: list[str]  (articles と同じ順序)
  └─ messenger.create_daily_forum_post(articles, summaries)
       ├─ POST /webhook?wait=true  { content: 一覧, thread_name: "YYYY-MM-DD テックニュース" }
       │   └─ → thread_id
       └─ for each (article, summary):
            POST /webhook?thread_id=...  { content: 📌 タイトル\nURL\n要約 }
```
