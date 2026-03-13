import logging

import requests

logger = logging.getLogger(__name__)


class NoteScraper:
    """note.com の検索APIを使ってテック系人気記事を取得するスクレイパー"""

    SEARCH_API = "https://note.com/api/v3/searches"
    KEYWORDS = ["AI", "プログラミング", "エンジニア", "Python", "クラウド"]

    def __init__(self, top_n=15):
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

    def run(self) -> list[dict]:
        """複数キーワードで検索し、いいね数上位の記事候補を返す"""
        logger.info("note: APIで記事取得中...")
        seen_keys: set = set()
        candidates: list[dict] = []

        for kw in self.KEYWORDS:
            try:
                resp = self.session.get(
                    self.SEARCH_API,
                    params={"context": "note", "q": kw, "sort": "like", "page": 1},
                    timeout=15,
                )
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"note API error (q={kw}): {e}")
                continue

            notes = resp.json().get("data", {}).get("notes", {}).get("contents", [])
            for note in notes:
                key = note.get("key", "")
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)

                user = note.get("user", {})
                urlname = user.get("urlname", "")
                url = f"https://note.com/{urlname}/n/{key}"
                title = note.get("name", "").strip()
                if not title or len(title) < 5:
                    continue

                candidates.append({
                    "title": title,
                    "url": url,
                    "published_date": note.get("publish_at", ""),
                    "like_count": note.get("like_count", 0),
                })

        # いいね数でソートして上位 top_n を返す
        candidates.sort(key=lambda x: x["like_count"], reverse=True)
        articles = candidates[: self.top_n]
        logger.info(f"note: {len(articles)} 件の記事候補を取得")
        return articles
