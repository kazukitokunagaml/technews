import datetime
import logging
import re

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class NoteScraper:
    """note.comのトレンドから記事候補を取得するスクレイパー"""

    TRENDING_URL = "https://note.com/trending"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=15):
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        today_jst = datetime.datetime.now(self.JST).date()
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"note 対象日: {self.yesterday_str}")

    def run(self) -> list[dict]:
        """トレンドページから記事候補を取得する"""
        logging.info(f"note: トレンドページから記事取得中... {self.TRENDING_URL}")
        try:
            resp = self.session.get(self.TRENDING_URL, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logging.error(f"note fetch error: {e}")
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        articles = []
        seen_urls: set = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not re.search(r"/[^/]+/n/[a-zA-Z0-9]+", href):
                continue
            url = href if href.startswith("http") else f"https://note.com{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            articles.append({
                "title": title,
                "url": url,
                "published_date": "",
            })
            if len(articles) >= self.top_n:
                break

        logging.info(f"note: {len(articles)} 件の記事候補を取得")
        return articles
