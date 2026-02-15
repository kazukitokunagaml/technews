import datetime
import http.client
import json
import logging
import os
import sys

from dotenv import load_dotenv

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class QiitaScraper:
    """Qiitaから昨日の人気記事を取得するスクレイパー"""

    def __init__(self, tag_name="LLM", top_n=5, total_page=5, per_page=100):
        load_dotenv()
        self.api_token = os.getenv("QIITA_API_TOKEN")
        if not self.api_token:
            raise ValueError("QIITA_API_TOKEN not found in environment variables.")
        self.tag_name = tag_name
        self.top_n = top_n
        self.total_page = total_page
        self.per_page = per_page
        self.connect = http.client.HTTPSConnection("qiita.com")
        self.url = "/api/v2/items?"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.yesterday_str = yesterday.strftime("%Y-%m-%d")
        logging.info(f"Qiita 対象日: {self.yesterday_str}")

    def fetch_data(self, page):
        query = f"&query=created%3A{self.yesterday_str}"
        page_params = f"page={page}&per_page={self.per_page}"
        url = f"{self.url}{page_params}{query}"
        logging.info(f"Qiita Fetching: {url}")
        try:
            self.connect.request("GET", url, headers=self.headers)
            res = self.connect.getresponse()
            if res.status != 200:
                logging.error(f"Qiita API failed: {res.status} {res.reason}")
                return []
            data = res.read().decode("utf-8")
            items = json.loads(data)
            results = []
            for item in items:
                created = item.get("created_at", "").split("T")[0]
                if created == self.yesterday_str:
                    results.append({
                        "title": item["title"],
                        "url": item["url"],
                        "likes_count": item.get("likes_count", 0),
                    })
            return results
        except Exception as e:
            logging.error(f"Qiita fetch error: {e}")
            return []

    def run(self):
        logging.info(f"Qiita: 昨日の人気記事を取得中...")
        all_articles = []
        for page in range(1, self.total_page + 1):
            data = self.fetch_data(page)
            all_articles.extend(data)
            logging.info(f"Qiita Page {page} 完了 ({len(data)}件)")
            if len(data) < self.per_page:
                break

        # いいね数でソートして上位N件を返す
        all_articles.sort(key=lambda x: x["likes_count"], reverse=True)
        top_articles = all_articles[:self.top_n]
        logging.info(f"Qiita: {len(all_articles)}件から上位{self.top_n}件を選出")
        return [{"title": a["title"], "url": a["url"]} for a in top_articles]
