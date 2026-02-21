import logging
import requests

logger = logging.getLogger(__name__)

class DiscordMessenger:
    def __init__(self, webhook_url: str, bot_token: str = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token

    def send_article_with_summary(self, article: dict, summary: str) -> None:
        """記事のタイトル・リンクを送信し、要約を投稿する"""
        
        # フォーラムチャンネルの場合、webhook に thread_name を指定すると新規投稿（スレッド作成）ができる
        # それ以外の場合は通常のメッセージとして投稿する
        try:
            # 1. 親メッセージの投稿
            content = f"### {article['title']}\n{article['url']}"
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": content},
                timeout=10,
            )
            resp.raise_for_status()
            message_data = resp.json()
            message_id = message_data.get("id")
            channel_id = message_data.get("channel_id")

            # 2. スレッド作成と要約投稿
            if self.bot_token and message_id and channel_id:
                # Bot トークンがある場合：メッセージからスレッドを作成
                thread_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/threads"
                headers = {
                    "Authorization": f"Bot {self.bot_token}",
                    "Content-Type": "application/json"
                }
                thread_resp = requests.post(
                    thread_url,
                    json={"name": f"要約: {article['title'][:50]}"},
                    headers=headers,
                    timeout=10
                )
                if thread_resp.status_code == 201:
                    thread_id = thread_resp.json().get("id")
                    # 作成したスレッドに要約を投稿
                    requests.post(
                        f"{self.webhook_url}?thread_id={thread_id}",
                        json={"content": f"**詳細要約:**\n{summary}"},
                        timeout=10
                    ).raise_for_status()
                    logger.info(f"スレッドに要約を投稿しました: {article['title']}")
                    return

            # Bot トークンがない、またはスレッド作成失敗時のフォールバック：同一メッセージに追記投稿
            # または要約を別のメッセージとして投稿
            requests.post(
                self.webhook_url,
                json={"content": f"**詳細要約:**\n{summary}"},
                timeout=10
            ).raise_for_status()
            logger.info(f"要約をメッセージとして投稿しました: {article['title']}")

        except Exception as e:
            logger.error(f"Discord 送信エラー ({article['title']}): {e}")
