import datetime
import logging
import time

import requests

logger = logging.getLogger(__name__)


class DiscordMessenger:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def create_daily_forum_post(
        self, articles: list[dict], summaries: list[str]
    ) -> None:
        """1日分の記事一覧と各要約を1つのフォーラムスレッドに投稿する"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        thread_name = f"{today} テックニュース"

        # 記事一覧メッセージを組み立てる
        lines = [f"📰 本日のテックニュース ({len(articles)}件)"]
        for i, article in enumerate(articles, 1):
            lines.append(f"{i}. [{article['title']}](<{article['url']}>)")
        # 2000文字制限内に収まるよう行単位でトリミング
        index_lines = []
        total = 0
        for line in lines:
            if total + len(line) + 1 > 2000:
                logger.warning("記事一覧が2000文字を超えるため一部省略しました")
                break
            index_lines.append(line)
            total += len(line) + 1
        index_content = "\n".join(index_lines)

        # フォーラムへ投稿してスレッドを作成
        try:
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": index_content, "thread_name": thread_name},
                timeout=10,
            )
            resp.raise_for_status()
            thread_id = resp.json().get("channel_id")
            if not thread_id:
                logger.error("thread_id が取得できませんでした。レスポンス: %s", resp.json())
                return
            logger.info(f"フォーラムスレッド作成: {thread_name} (id={thread_id})")
        except Exception as e:
            logger.error(f"フォーラムスレッド作成エラー: {e}")
            return

        # 各記事の要約をスレッドに投稿
        for article, summary in zip(articles, summaries):
            content = (
                f"📌 **{article['title']}**\n"
                f"{article['url']}\n\n"
                f"**要約:**\n{summary}"
            )
            if len(content) > 2000:
                content = content[:1997] + "..."
            try:
                requests.post(
                    f"{self.webhook_url}?thread_id={thread_id}",
                    json={"content": content},
                    timeout=10,
                ).raise_for_status()
                logger.info(f"要約投稿完了: {article['title']}")
            except Exception as e:
                logger.error(f"要約投稿エラー ({article['title']}): {e}")
            time.sleep(1)  # レート制限対策
