import logging
import requests
import time

logger = logging.getLogger(__name__)

class DiscordMessenger:
    def __init__(self, webhook_url: str, bot_token: str = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token

    def send_article_with_summary(self, article: dict, summary: str) -> None:
        """記事のタイトル・リンクを送信し、要約をスレッドに投稿する"""
        
        try:
            # 1. 親メッセージの投稿
            # フォーラムチャンネルの場合、thread_name を含めると新規スレッド（投稿）として作成される
            payload = {
                "content": f"### {article['title']}\n{article['url']}",
                "thread_name": f"要約: {article['title'][:50]}" # フォーラム用
            }
            
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            message_data = resp.json()
            
            # メッセージID、チャンネルID、スレッドID（フォーラムの場合）を取得
            message_id = message_data.get("id")
            channel_id = message_data.get("channel_id")
            # フォーラムチャンネルの場合、message_data 自体がスレッド情報を含んでいることがある
            thread_id = message_data.get("id") if "thread_name" in payload and message_data.get("type") == 11 else None

            # 2. スレッド作成（通常のテキストチャンネルの場合）
            if not thread_id and self.bot_token and message_id and channel_id:
                # Bot トークンを使用してメッセージからスレッドを開始
                thread_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/threads"
                headers = {
                    "Authorization": f"Bot {self.bot_token}",
                    "Content-Type": "application/json"
                }
                # 既存のスレッドがある可能性も考慮
                thread_resp = requests.post(
                    thread_url,
                    json={"name": f"要約: {article['title'][:50]}", "auto_archive_duration": 60},
                    headers=headers,
                    timeout=10
                )
                
                if thread_resp.status_code in [200, 201]:
                    thread_id = thread_resp.json().get("id")
                    logger.info(f"スレッドを作成しました: {thread_id}")
                elif thread_resp.status_code == 400:
                    # すでにスレッドが存在する場合などのエラーハンドリング（簡易）
                    logger.warning(f"スレッド作成に失敗しました (400): {thread_resp.text}")

            # 3. 要約を投稿
            if thread_id:
                # スレッド ID が取得できている場合、そのスレッド内に投稿
                summary_url = f"{self.webhook_url}?thread_id={thread_id}"
                requests.post(
                    summary_url,
                    json={"content": f"**詳細要約:**\n{summary}"},
                    timeout=10
                ).raise_for_status()
                logger.info(f"スレッドに要約を投稿しました: {article['title']}")
            else:
                # スレッドが作成できなかった場合のフォールバック（通常のメッセージとして連投）
                requests.post(
                    self.webhook_url,
                    json={"content": f"**詳細要約:**\n{summary}"},
                    timeout=10
                ).raise_for_status()
                logger.info(f"スレッドなしで要約を投稿しました: {article['title']}")

        except Exception as e:
            logger.error(f"Discord 送信エラー ({article['title']}): {e}")
