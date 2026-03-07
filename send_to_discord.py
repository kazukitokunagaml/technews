import datetime
import logging

import requests

logger = logging.getLogger(__name__)


class DiscordMessenger:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def post_best_article(
        self,
        article: dict,
        summary: str,
        platform_name: str = "テック",
        emoji: str = "🌟",
    ) -> None:
        """本日の注目記事をDiscordフォーラムスレッドに投稿する"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        thread_name = f"{today} {platform_name} 注目記事"

        header = (
            f"{emoji} **{platform_name} 注目記事** — {today}\n\n"
            f"**{article['title']}**\n"
            f"{article['url']}"
        )
        if len(header) > 2000:
            header = header[:1997] + "..."

        try:
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": header, "thread_name": thread_name},
                timeout=10,
            )
            resp.raise_for_status()
            thread_id = resp.json().get("channel_id")
            if not thread_id:
                logger.error(
                    "thread_id が取得できませんでした。レスポンス: %s", resp.json()
                )
                return
            logger.info(f"フォーラムスレッド作成: {thread_name} (id={thread_id})")
        except Exception as e:
            logger.error(f"フォーラムスレッド作成エラー: {e}")
            return

        detail = f"**解説:**\n{summary}"
        if len(detail) > 2000:
            detail = detail[:1997] + "..."
        try:
            requests.post(
                f"{self.webhook_url}?thread_id={thread_id}",
                json={"content": detail},
                timeout=10,
            ).raise_for_status()
            logger.info(f"解説投稿完了: {article['title']}")
        except Exception as e:
            logger.error(f"解説投稿エラー: {e}")
