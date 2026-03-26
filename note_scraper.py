import datetime
import logging

import requests

logger = logging.getLogger(__name__)


class NoteScraper:
    """note.com の検索APIを使ってテック系人気記事を取得するスクレイパー"""

    HASHTAG_API = "https://note.com/api/v3/hashtags/{hashtag}/notes"
    KEYWORDS = ["個人開発", "個人開発者", "副業", "サービス開発", "アプリ開発", "プロダクト開発", "プロダクトマネジメント", "開発プロセス"]
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, top_n=15, days_back: int = 1):
        self.top_n = top_n
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
        )
        # GitHub Actions (UTC) で実行されるため、JST基準で昨日を計算する
        today_jst = datetime.datetime.now(self.JST).date()
        self.target_dates = {
            (today_jst - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, days_back + 1)
        }
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"note 対象期間: {days_back}日分")

    def _parse_date_jst(self, publish_at: str) -> str:
        """publish_atをJST日付文字列(YYYY-MM-DD)に変換する"""
        if not publish_at:
            return ""
        try:
            dt = datetime.datetime.fromisoformat(publish_at)
            return dt.astimezone(self.JST).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return publish_at.split("T")[0]

    def run(self) -> list[dict]:
        """複数キーワードで検索し、昨日公開されたいいね数上位の記事候補を返す"""
        logger.info("note: APIで記事取得中...")
        seen_keys: set = set()
        candidates: list[dict] = []

        for kw in self.KEYWORDS:
            try:
                resp = self.session.get(
                    self.HASHTAG_API.format(hashtag=kw),
                    timeout=15,
                )
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"note API error (q={kw}): {e}")
                continue

            notes = resp.json().get("data", {}).get("notes", [])
            for note in notes:
                key = note.get("key", "")
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)

                published = self._parse_date_jst(note.get("publish_at", ""))
                if published not in self.target_dates:
                    continue

                user = note.get("user", {})
                urlname = user.get("urlname", "")
                title = note.get("name", "").strip()
                if not title or len(title) < 5:
                    continue

                candidates.append({
                    "title": title,
                    "url": f"https://note.com/{urlname}/n/{key}",
                    "published_date": published,
                    "like_count": note.get("like_count", 0),
                })

        # いいね数でソートして上位 top_n を返す
        candidates.sort(key=lambda x: x["like_count"], reverse=True)
        articles = candidates[: self.top_n]
        logger.info(f"note: {len(articles)} 件の記事候補を取得")
        return articles
