import datetime
import logging
import os

import requests

logger = logging.getLogger(__name__)


class RedditScraper:
    """Redditの指定サブレディットからトップ投稿を取得するスクレイパー

    Reddit Data API (OAuth2 client_credentials) を使用。
    必要な環境変数:
        REDDIT_CLIENT_ID     - Reddit app の client ID
        REDDIT_CLIENT_SECRET - Reddit app の client secret
        REDDIT_USERNAME      - Reddit ユーザー名 (User-Agent用)
    """

    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API_BASE = "https://oauth.reddit.com"
    JST = datetime.timezone(datetime.timedelta(hours=9))

    def __init__(self, subreddit="technology", top_n=10):
        self.subreddit = subreddit
        self.top_n = top_n

        self.client_id = os.environ.get("REDDIT_CLIENT_ID", "")
        self.client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
        username = os.environ.get("REDDIT_USERNAME", "technews_bot")

        self.session = requests.Session()
        # Reddit API規約: "<platform>:<app ID>:<version> (by /u/<username>)" 形式
        self.session.headers.update({
            "User-Agent": f"script:technews:v1.0 (by /u/{username})",
        })

        self._access_token: str | None = None
        self._token_expires_at: datetime.datetime | None = None

        today_jst = datetime.datetime.now(self.JST).date()
        self.yesterday_str = (today_jst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"Reddit r/{subreddit} 対象日: {self.yesterday_str}")

    def _get_access_token(self) -> str | None:
        """client_credentials フローでアクセストークンを取得する"""
        if not self.client_id or not self.client_secret:
            logger.error("Reddit: REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET が未設定")
            return None

        # キャッシュされたトークンが有効なら再利用
        if self._access_token and self._token_expires_at:
            if datetime.datetime.now(datetime.timezone.utc) < self._token_expires_at:
                return self._access_token

        try:
            resp = self.session.post(
                self.TOKEN_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                timeout=15,
            )
            resp.raise_for_status()
            token_data = resp.json()

            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in - 60)
            logger.info("Reddit: アクセストークン取得成功")
            return self._access_token
        except Exception as e:
            logger.error(f"Reddit: トークン取得失敗: {e}")
            return None

    def run(self) -> list[dict]:
        """サブレディットの当日トップ投稿を取得する"""
        token = self._get_access_token()
        if not token:
            return []

        url = f"{self.API_BASE}/r/{self.subreddit}/top"
        params = {"t": "day", "limit": self.top_n}
        headers = {"Authorization": f"bearer {token}"}
        logger.info(f"Reddit: {url} から取得中...")

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=30)
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
        except requests.HTTPError as e:
            logger.error(f"Reddit HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Reddit fetch/parse error: {e}")
            return []
