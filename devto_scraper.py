import datetime
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


class DevToScraper:
    """dev.to公開APIを使って昨日の人気記事を取得する"""

    API_URL = "https://dev.to/api/articles"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=5, min_reactions=5, days_back: int = 1):
        self.top_n = top_n
        self.min_reactions = min_reactions
        today_jst = datetime.datetime.now(self.JST).date()
        self.target_dates = {
            (today_jst - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, days_back + 1)
        }
        logger.info(f"dev.to 対象期間: {days_back}日分 (min_reactions={min_reactions})")

    def _parse_date_jst(self, published_at: str) -> str:
        if not published_at:
            return ""
        try:
            dt = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            return dt.astimezone(self.JST).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return published_at[:10]

    def run(self) -> list[dict]:
        # top=N: 直近N日間のトップ記事を返す
        days_back = len(self.target_dates)
        url = f"{self.API_URL}?top={days_back}&per_page=50"
        logger.info(f"dev.to Fetching: {url}")
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TechDigest/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"dev.to fetch error: {e}")
            return []

        articles = []
        for item in data:
            reactions = item.get("public_reactions_count") or 0
            if reactions < self.min_reactions:
                continue

            published_date = self._parse_date_jst(item.get("published_at", ""))
            if published_date not in self.target_dates:
                continue

            title = item.get("title", "").strip()
            url_article = item.get("url", "")
            if not title or not url_article:
                continue

            articles.append({
                "title": title,
                "url": url_article,
                "reactions": reactions,
                "published_date": published_date,
            })

        articles.sort(key=lambda x: x["reactions"], reverse=True)
        top = articles[: self.top_n]
        logger.info(f"dev.to: {len(articles)}件中上位{len(top)}件を選出")
        return [
            {"title": a["title"], "url": a["url"], "published_date": a["published_date"]}
            for a in top
        ]
