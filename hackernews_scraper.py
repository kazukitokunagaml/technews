import datetime
import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


class HackerNewsScraper:
    """Algolia HN Search APIを使って昨日のHacker News人気記事を取得する"""

    ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=5, min_score=10, days_back: int = 1):
        self.top_n = top_n
        self.min_score = min_score
        today_jst = datetime.datetime.now(self.JST).date()
        self.target_dates = {
            (today_jst - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, days_back + 1)
        }
        # days_back日前の0時(JST)以降の記事を取得
        cutoff_date = today_jst - datetime.timedelta(days=days_back)
        cutoff_dt = datetime.datetime.combine(cutoff_date, datetime.time.min, tzinfo=self.JST)
        self.created_at_start = int(cutoff_dt.timestamp())
        logger.info(f"HackerNews 対象期間: {days_back}日分 (min_score={min_score})")

    def run(self) -> list[dict]:
        params = urllib.parse.urlencode({
            "tags": "story",
            "numericFilters": f"created_at_i>{self.created_at_start}",
            "hitsPerPage": "100",
        })
        url = f"{self.ALGOLIA_URL}?{params}"
        logger.info(f"HackerNews Fetching: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechDigest/1.0"})
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"HackerNews fetch error: {e}")
            return []

        articles = []
        for hit in data.get("hits", []):
            score = hit.get("points") or 0
            if score < self.min_score:
                continue

            created_at_i = hit.get("created_at_i", 0)
            published_date = datetime.datetime.fromtimestamp(
                created_at_i, tz=self.JST
            ).strftime("%Y-%m-%d")
            if published_date not in self.target_dates:
                continue

            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            title = hit.get("title", "").strip()
            if not title:
                continue

            articles.append({
                "title": title,
                "url": story_url,
                "score": score,
                "published_date": published_date,
            })

        articles.sort(key=lambda x: x["score"], reverse=True)
        top = articles[: self.top_n]
        logger.info(f"HackerNews: {len(articles)}件中上位{len(top)}件を選出")
        return [
            {"title": a["title"], "url": a["url"], "published_date": a["published_date"]}
            for a in top
        ]
