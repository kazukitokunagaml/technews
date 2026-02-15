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
            seen_urls = set()

            # 記事タイトルのリンクを探す
            # class="style-2vm86z" のリンクが記事タイトルのリンク
            article_links = soup.find_all("a", class_="style-2vm86z", href=True)

            for link in article_links:
                try:
                    href = link["href"]
                    # 絶対URLに変換
                    if not href.startswith("http"):
                        href = f"{self.BASE_URL}{href}"

                    # 重複チェック
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link.get_text(strip=True)
                    if not title:
                        continue

                    # いいね数を抽出（オプション）
                    # 記事カード内のLIKEボタンを探す
                    likes = 0
                    parent = link.find_parent("article") or link.find_parent("div")
                    if parent:
                        like_elem = parent.find("span", attrs={"data-hyperlink": "LikeButton"})
                        if like_elem:
                            likes_text = like_elem.get_text(strip=True)
                            try:
                                likes = int(likes_text)
                            except (ValueError, TypeError):
                                likes = 0

                    articles.append({
                        "title": title,
                        "url": href,
                        "likes_count": likes,
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

        # いいね数でソートして上位N件を返す
        all_articles.sort(key=lambda x: x["likes_count"], reverse=True)
        top_articles = all_articles[:self.top_n]
        logging.info(f"Qiita: {len(all_articles)}件から上位{self.top_n}件を選出")

        return [{"title": a["title"], "url": a["url"]} for a in top_articles]
