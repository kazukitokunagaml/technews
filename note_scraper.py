import logging

import requests

logger = logging.getLogger(__name__)


class NoteScraper:
    """note.comのトレンドから記事候補を取得するスクレイパー"""

    # HTMLスクレイピングではなく公式APIを使用（Next.jsのCSRに対応）
    API_URL = "https://note.com/api/v2/notes/trending"

    def __init__(self, top_n=15):
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })
        logger.info("note スクレイパー初期化完了")

    def run(self) -> list[dict]:
        """トレンドAPIから記事候補を取得する"""
        logger.info(f"note: APIから記事取得中... {self.API_URL}")
        try:
            resp = self.session.get(self.API_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"note fetch/parse error: {e}")
            return []

        notes = data.get("data", {}).get("notes", [])
        articles = []

        for note in notes:
            key = note.get("key", "")
            user = note.get("user", {})
            urlname = user.get("urlname", "")
            title = note.get("name", "").strip()

            if not key or not urlname or not title:
                continue

            url = f"https://note.com/{urlname}/n/{key}"
            articles.append({
                "title": title,
                "url": url,
                "published_date": "",
            })
            if len(articles) >= self.top_n:
                break

        logger.info(f"note: {len(articles)} 件の記事候補を取得")
        return articles
