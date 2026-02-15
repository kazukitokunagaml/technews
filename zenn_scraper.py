import datetime
import json
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ZennScraper:
    """Zennから昨日の人気記事を取得するスクレイパー"""

    BASE_URL = "https://zenn.dev/api/articles"

    def __init__(self, top_n=5, max_pages=5):
        self.top_n = top_n
        self.max_pages = max_pages
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.yesterday_str = yesterday.strftime("%Y-%m-%d")
        logging.info(f"Zenn 対象日: {self.yesterday_str}")

    def fetch_page(self, page):
        url = f"{self.BASE_URL}?order=latest&page={page}"
        logging.info(f"Zenn Fetching: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechDigest/1.0"})
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode("utf-8"))
            return data.get("articles", [])
        except Exception as e:
            logging.error(f"Zenn fetch error: {e}")
            return []

    def run(self):
        logging.info("Zenn: 昨日の人気記事を取得中...")
        all_articles = []
        for page in range(1, self.max_pages + 1):
            articles = self.fetch_page(page)
            if not articles:
                break

            found_older = False
            for article in articles:
                published = article.get("published_at", "").split("T")[0]
                if published == self.yesterday_str:
                    all_articles.append({
                        "title": article.get("title", ""),
                        "url": f"https://zenn.dev{article.get('path', '')}",
                        "liked_count": article.get("liked_count", 0),
                    })
                elif published < self.yesterday_str:
                    found_older = True

            logging.info(f"Zenn Page {page} 完了 ({len(articles)}件取得)")
            if found_older:
                break

        # いいね数でソートして上位N件を返す
        all_articles.sort(key=lambda x: x["liked_count"], reverse=True)
        top_articles = all_articles[:self.top_n]
        logging.info(f"Zenn: {len(all_articles)}件から上位{self.top_n}件を選出")
        return [{"title": a["title"], "url": a["url"]} for a in top_articles]
