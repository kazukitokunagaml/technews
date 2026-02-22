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
            # 通常のテキストチャンネルでは thread_name を含めると 400 Bad Request になるため
            # Webhook URL 自体に thread_id が含まれているか、スレッド作成が可能か判断する
            payload = {
                "content": f"### {article['title']}\n{article['url']}"[:2000]
            }
            
            # フォーラムチャンネルへの投稿をサポートしたい場合は、
            # 別途判定フラグなどを用意するのが望ましいですが、
            # 一旦 400 エラー回避のために thread_name は削除します。
            
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json=payload,
                timeout=10,
            )
            
            if resp.status_code != 200 and resp.status_code != 201:
                logger.error(f"Discord Webhook 親メッセージ投稿失敗 ({resp.status_code}): {resp.text}")
                resp.raise_for_status()
                
            message_data = resp.json()
            
            # メッセージID、チャンネルIDを取得
            message_id = message_data.get("id")
            channel_id = message_data.get("channel_id")
            thread_id = None

            # 2. スレッド作成（Botトークンがある場合のみ試行）
            if self.bot_token and message_id and channel_id:
                # Bot トークンを使用してメッセージからスレッドを開始
                thread_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/threads"
                headers = {
                    "Authorization": f"Bot {self.bot_token}",
                    "Content-Type": "application/json"
                }
                thread_resp = requests.post(
                    thread_url,
                    json={"name": f"要約: {article['title'][:50]}", "auto_archive_duration": 60},
                    headers=headers,
                    timeout=10
                )
                
                if thread_resp.status_code in [200, 201]:
                    thread_id = thread_resp.json().get("id")
                    logger.info(f"スレッドを作成しました: {thread_id}")
                else:
                    logger.warning(f"スレッド作成に失敗しました ({thread_resp.status_code}): {thread_resp.text}")

            # 3. 要約を投稿
            # Discord のメッセージ上限は 2000 文字なので、安全のために切り詰める
            content_summary = f"**詳細要約:**\n{summary}"
            if len(content_summary) > 2000:
                content_summary = content_summary[:1997] + "..."

            if thread_id:
                summary_url = f"{self.webhook_url}?thread_id={thread_id}"
                requests.post(
                    summary_url,
                    json={"content": content_summary},
                    timeout=10
                ).raise_for_status()
                logger.info(f"スレッドに要約を投稿しました: {article['title']}")
            else:
                # スレッドが作成できなかった場合、あるいは Bot トークンがない場合は通常のメッセージとして送信
                requests.post(
                    self.webhook_url,
                    json={"content": content_summary},
                    timeout=10
                ).raise_for_status()
                logger.info(f"通常のメッセージとして要約を投稿しました: {article['title']}")

        except Exception as e:
            logger.error(f"Discord 送信エラー ({article['title']}): {e}")
