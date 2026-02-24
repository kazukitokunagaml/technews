import logging
import requests

logger = logging.getLogger(__name__)

class DiscordMessenger:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_article_with_summary(self, article: dict, summary: str) -> None:
        """記事をフォーラムチャンネルに投稿し、要約をスレッドに送る"""
        try:
            # 1. フォーラム投稿（thread_name がスレッドタイトルになる）
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={
                    "content": f"{article['url']}"[:2000],
                    "thread_name": article['title'][:100],
                },
                timeout=10,
            )
            resp.raise_for_status()

            # 応答の channel_id が新規作成されたスレッドのID
            thread_id = resp.json().get("channel_id")

            # 2. 要約をスレッドに投稿
            content_summary = f"**詳細要約:**\n{summary}"
            if len(content_summary) > 2000:
                content_summary = content_summary[:1997] + "..."

            requests.post(
                f"{self.webhook_url}?thread_id={thread_id}",
                json={"content": content_summary},
                timeout=10,
            ).raise_for_status()

            logger.info(f"投稿完了: {article['title']}")

        except Exception as e:
            logger.error(f"Discord 送信エラー ({article['title']}): {e}")
