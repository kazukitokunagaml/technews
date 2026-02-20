import datetime
import logging
import sys
import time

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class QiitaScraper:
    """Qiitaから昨日の人気記事を取得するスクレイパー（Webスクレイピング版）"""

    BASE_URL = "https://qiita.com"

    def __init__(self, top_n=5, max_pages=3):
        self.top_n = top_n
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.yesterday_str = yesterday.strftime("%Y-%m-%d")
        logging.info(f"Qiita 対象日: {self.yesterday_str}")

    def fetch_articles(self, page=1):
        """Qiitaの記事一覧ページから記事情報を取得"""
        url = f"{self.BASE_URL}/items?page={page}"
        logging.info(f"Qiita Fetching: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            articles = []

            # 記事カードを探す（Qiitaの構造に依存）
            article_items = soup.find_all("article", class_="style-1w7apwp")

            if not article_items:
                # フォールバック: 別のクラス名を試す（古い構造）
                article_items = soup.find_all("article", class_="style-1gr9egx")

            if not article_items:
                # さらにフォールバック
                article_items = soup.find_all("article")

            for item in article_items:
                try:
                    # タイトルとURLを抽出
                    # 最新のHTML構造: h2内のaタグ
                    title_elem = item.find("h2")
                    if not title_elem:
                        # フォールバック: 直接aタグを探す
                        title_elem = item.find("a", class_="style-w8rf03")

                    if not title_elem:
                        continue

                    link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                    if not link_elem or not link_elem.get("href"):
                        continue

                    title = link_elem.get_text(strip=True)
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"{self.BASE_URL}{url}"

                    # 投稿日時を抽出
                    published_date = None
                    time_elem = item.find("time")
                    if time_elem and time_elem.get("datetime"):
                        # datetime属性から日付を抽出（例: "2024-02-14T10:30:00Z"）
                        datetime_str = time_elem["datetime"]
                        try:
                            # ISO形式の日時をパース
                            published_date = datetime_str.split("T")[0]  # YYYY-MM-DD部分のみ
                        except Exception:
                            pass

                    # いいね数を抽出（オプション）
                    likes = 0
                    # 最新のHTML構造
                    like_elem = item.find("span", class_="style-qrq9vy")
                    if not like_elem:
                        # 古いHTML構造のフォールバック
                        like_elem = item.find("span", attrs={"data-hyperlink": "LikeButton"})

                    if like_elem:
                        likes_text = like_elem.get_text(strip=True)
                        try:
                            likes = int(likes_text)
                        except (ValueError, TypeError):
                            likes = 0

                    articles.append({
                        "title": title,
                        "url": url,
                        "likes_count": likes,
                        "published_date": published_date,
                    })

                except Exception as e:
                    logging.warning(f"Qiita 記事パースエラー: {e}")
                    continue

            return articles

        except requests.RequestException as e:
            logging.error(f"Qiita fetch error: {e}")
            return []
        except Exception as e:
            logging.error(f"Qiita parse error: {e}")
            return []

    def run(self):
        """昨日の人気記事を取得"""
        logging.info(f"Qiita: 記事を取得中...")
        all_articles = []

        for page in range(1, self.max_pages + 1):
            articles = self.fetch_articles(page)
            all_articles.extend(articles)
            logging.info(f"Qiita Page {page} 完了 ({len(articles)}件)")

            if len(articles) == 0:
                break

            # レート制限対策
            time.sleep(1)

        # 昨日の記事のみフィルタリング（URLで重複排除）
        seen_urls: set = set()
        yesterday_articles = []
        for a in all_articles:
            if a.get("published_date") == self.yesterday_str and a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                yesterday_articles.append(a)
        logging.info(f"Qiita: {len(all_articles)}件中、昨日の記事は{len(yesterday_articles)}件")

        # いいね数でソートして上位N件を返す
        yesterday_articles.sort(key=lambda x: x["likes_count"], reverse=True)
        top_articles = yesterday_articles[:self.top_n]
        logging.info(f"Qiita: 昨日の記事から上位{self.top_n}件を選出")

        return [
            {"title": a["title"], "url": a["url"], "published_date": a.get("published_date", "")}
            for a in top_articles
        ]
