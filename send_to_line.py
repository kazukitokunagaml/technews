import logging

from linebot import LineBotApi
from linebot.models import TextSendMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class LineMessenger:
    def __init__(self, channel_access_token):
        self.channel_access_token = channel_access_token
        self.line_bot_api = LineBotApi(channel_access_token)

    def _format_section(self, platform_name, articles):
        if not articles:
            return f"【{platform_name}】\n記事が見つかりませんでした"
        lines = [f"【{platform_name}】"]
        for i, article in enumerate(articles, 1):
            lines.append(f"{i}. {article['title']}")
            lines.append(f"   {article['url']}")
        return "\n".join(lines)

    def send_multi_platform(self, qiita_articles, zenn_articles):
        """複数プラットフォームの記事をまとめてLINEに送信"""
        sections = [
            "昨日の人気テック記事まとめ",
            "",
            self._format_section("Qiita", qiita_articles),
            "",
            self._format_section("Zenn", zenn_articles),
        ]
        text = "\n".join(sections)

        # LINEのテキストメッセージ上限は5000文字
        if len(text) > 5000:
            text = text[:4997] + "..."

        messages = [TextSendMessage(text=text)]
        try:
            self.line_bot_api.broadcast(messages=messages)
            logging.info("LINEメッセージを送信しました")
        except Exception as e:
            logging.error(f"LINE送信エラー: {e}")
            logging.error(f"メッセージ内容: {text}")

    def send_message(self, articles):
        """後方互換: 単一リストの記事を送信"""
        if not articles:
            text = "昨日投稿された記事はありませんでした"
        else:
            text = "昨日の生成AI記事:\n" + "\n".join(
                [f"{article['title']}\n{article['url']}" for article in articles],
            )

        messages = [TextSendMessage(text=text)]
        try:
            self.line_bot_api.broadcast(messages=messages)
            logging.info("メッセージが正常に送信されました！")
        except Exception as e:
            logging.error(f"エラーが発生しました: {e}")
            logging.error(f"内容はこちら:{messages}")
