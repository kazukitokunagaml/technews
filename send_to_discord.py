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
        platform_name: str = "",
        emoji: str = "",
    ) -> None:
        """記事をDiscordフォーラムスレッドに投稿する"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        thread_name = f"{today} {platform_name} 注目記事"
        if len(thread_name) > 100:
            thread_name = thread_name[:97] + "..."

        # ティーザー + URL をひとつのメッセージにまとめる
        content = f"{emoji} {summary}\n{article['url']}"
        if len(content) > 2000:
            content = content[:1997] + "..."
        try:
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": content, "thread_name": thread_name},
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
