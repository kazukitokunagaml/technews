import datetime
import logging
import os

import feedparser
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class TechFeedScraper:
    """TechFeedからRSSフィードで人気記事を取得するスクレイパー"""

    DEFAULT_FEED_URL = "https://techfeed.io/feeds/categories/all/daily"

    def __init__(self, top_n=5):
        load_dotenv()
        self.feed_url = os.getenv("TECHFEED_RSS_URL", self.DEFAULT_FEED_URL)
        self.top_n = top_n
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.yesterday_str = yesterday.strftime("%Y-%m-%d")
        logging.info(f"TechFeed 対象日: {self.yesterday_str}")
        logging.info(f"TechFeed RSS URL: {self.feed_url}")

    def run(self):
        logging.info("TechFeed: RSSフィードから記事を取得中...")
        try:
            feed = feedparser.parse(self.feed_url)
            if feed.bozo and not feed.entries:
                logging.error(f"TechFeed RSS parse error: {feed.bozo_exception}")
                return []

            articles = []
            for entry in feed.entries:
                # RSSエントリーから記事情報を抽出
                published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime.date(
                        entry.published_parsed.tm_year,
                        entry.published_parsed.tm_mon,
                        entry.published_parsed.tm_mday,
                    ).strftime("%Y-%m-%d")
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime.date(
                        entry.updated_parsed.tm_year,
                        entry.updated_parsed.tm_mon,
                        entry.updated_parsed.tm_mday,
                    ).strftime("%Y-%m-%d")

                articles.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published": published,
                })

            # TechFeedのRSSはランキング順で配信されるため、
            # フィード内の順序をそのまま人気順として扱う
            # 昨日の記事でフィルタリング（日付が取得できない場合はそのまま含める）
            filtered = [
                a for a in articles
                if a["published"] == self.yesterday_str or a["published"] == ""
            ]

            top_articles = filtered[:self.top_n]
            logging.info(f"TechFeed: {len(articles)}件から{len(top_articles)}件を選出")
            return [{"title": a["title"], "url": a["url"]} for a in top_articles]

        except Exception as e:
            logging.error(f"TechFeed error: {e}")
            return []
