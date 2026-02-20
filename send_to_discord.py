import logging

import requests

logger = logging.getLogger(__name__)

# Discord message character limit
_MAX_LENGTH = 2000


class DiscordMessenger:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _format_section(self, platform_name: str, articles: list) -> str:
        if not articles:
            return f"**【{platform_name}】**\n記事が見つかりませんでした"
        lines = [f"**【{platform_name}】**"]
        for i, article in enumerate(articles, 1):
            lines.append(f"{i}. {article['title']}")
            lines.append(f"   {article['url']}")
        return "\n".join(lines)

    def send_multi_platform(self, qiita_articles: list, zenn_articles: list) -> None:
        """Qiita・Zennの記事まとめを Discord Webhook で送信する"""
        sections = [
            "**昨日の人気テック記事まとめ**",
            "",
            self._format_section("Qiita", qiita_articles),
            "",
            self._format_section("Zenn", zenn_articles),
        ]
        content = "\n".join(sections)

        if len(content) > _MAX_LENGTH:
            content = content[:_MAX_LENGTH - 3] + "..."

        try:
            resp = requests.post(
                self.webhook_url,
                json={"content": content},
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Discord にメッセージを送信しました")
        except Exception as e:
            logger.error(f"Discord 送信エラー: {e}")
