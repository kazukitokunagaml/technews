import datetime
import json
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ZennScraper:
    """Zennから昨日の人気記事を取得するスクレイパー"""

    BASE_URL = "https://zenn.dev/api/articles"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=5, max_pages=20, days_back: int = 1, min_likes: int = 1):
        self.top_n = top_n
        self.max_pages = max_pages
        # GitHub Actions (UTC) で実行されるため、JST基準で昨日を計算する
        today_jst = datetime.datetime.now(self.JST).date()
        self.target_dates = {
            (today_jst - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, days_back + 1)
        }
        self.cutoff_date = (today_jst - datetime.timedelta(days=days_back + 1)).strftime("%Y-%m-%d")
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.min_likes = min_likes
        logging.info(f"Zenn 対象期間: {days_back}日分 (max_pages={self.max_pages})")

    def _parse_date_jst(self, published_at):
        """published_atをJST日付文字列(YYYY-MM-DD)に変換する"""
        if not published_at:
            return ""
        try:
            dt = datetime.datetime.fromisoformat(published_at)
            return dt.astimezone(self.JST).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return published_at.split("T")[0]

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
        seen_urls = set()
        for page in range(1, self.max_pages + 1):
            articles = self.fetch_page(page)
            if not articles:
                break

            found_older = False
            for article in articles:
                published = self._parse_date_jst(article.get("published_at", ""))
                url = f"https://zenn.dev{article.get('path', '')}"
                liked_count = article.get("liked_count", 0) or 0
                if published in self.target_dates and url not in seen_urls and liked_count >= self.min_likes:
                    seen_urls.add(url)
                    all_articles.append({
                        "title": article.get("title", ""),
                        "url": url,
                        "liked_count": liked_count,
                        "published_date": published,
                    })
                elif published <= self.cutoff_date:
                    found_older = True

            logging.info(f"Zenn Page {page} 完了 ({len(articles)}件取得)")
            if found_older:
                break

        # いいね数でソートして上位N件を返す
        all_articles.sort(key=lambda x: x["liked_count"], reverse=True)
        top_articles = all_articles[:self.top_n]
        logging.info(f"Zenn: {len(all_articles)}件から上位{self.top_n}件を選出")
        return [
            {"title": a["title"], "url": a["url"], "published_date": a.get("published_date", "")}
            for a in top_articles
        ]
