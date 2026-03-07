import datetime
import logging

import requests

logger = logging.getLogger(__name__)


class RedditScraper:
    """Redditの指定サブレディットからトップ投稿を取得するスクレイパー"""

    BASE_URL = "https://www.reddit.com/r/{subreddit}/top.json"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, subreddit="technology", top_n=10):
        self.subreddit = subreddit
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TechDigest/1.0 (automated digest bot)"
        })
        today_jst = datetime.datetime.now(self.JST).date()
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"Reddit r/{subreddit} 対象日: {self.yesterday_str}")

    def run(self) -> list[dict]:
        """サブレディットの当日トップ投稿を取得する"""
        url = self.BASE_URL.format(subreddit=self.subreddit)
        params = {"t": "day", "limit": self.top_n}
        logger.info(f"Reddit: {url} から取得中...")

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            articles = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "")
                post_url = post.get("url", "")
                permalink = post.get("permalink", "")
                if not post_url and permalink:
                    post_url = f"https://www.reddit.com{permalink}"
                if not post_url:
                    continue

                articles.append({
                    "title": title,
                    "url": post_url,
                    "score": post.get("score", 0),
                    "published_date": self.yesterday_str,
                })

            articles.sort(key=lambda x: x["score"], reverse=True)
            logger.info(f"Reddit r/{self.subreddit}: {len(articles)} 件取得")
            return articles
        except Exception as e:
            logger.error(f"Reddit fetch/parse error: {e}")
            return []
