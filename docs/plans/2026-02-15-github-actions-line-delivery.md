# GitHub Actions LINE Delivery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate tech article delivery to LINE via GitHub Actions, replacing Qiita API with web scraping

**Architecture:** GitHub Actions runs daily at 8am JST, scraping Qiita/Zenn/TechFeed for articles, then broadcasts via LINE Messaging API. Qiita scraper migrated from API to BeautifulSoup scraping.

**Tech Stack:** Python, BeautifulSoup4, requests, LINE Messaging API SDK, GitHub Actions

---

## Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add BeautifulSoup4 to requirements**

Update `requirements.txt`:
```
python-dotenv
line-bot-sdk
requests
feedparser
beautifulsoup4
```

**Step 2: Verify requirements format**

Run: `cat requirements.txt`
Expected: All 5 packages listed, one per line

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add beautifulsoup4 dependency for Qiita scraping"
```

---

## Task 2: Implement Qiita Scraper with Web Scraping

**Files:**
- Modify: `qiita_scraper.py`

**Step 1: Write test for Qiita scraper**

Create: `test_qiita_scraper.py`

```python
import datetime
from qiita_scraper import QiitaScraper

def test_qiita_scraper_returns_articles():
    """Test that Qiita scraper returns list of articles"""
    scraper = QiitaScraper(top_n=5)
    articles = scraper.run()

    assert isinstance(articles, list)
    # May be empty if no articles found, but should be a list
    if articles:
        assert "title" in articles[0]
        assert "url" in articles[0]
        assert articles[0]["url"].startswith("https://qiita.com/")
```

**Step 2: Run test to verify current implementation**

Run: `python -m pytest test_qiita_scraper.py -v`
Expected: PASS (current API-based implementation should work if token exists, or FAIL if token missing)

**Step 3: Rewrite QiitaScraper to use web scraping**

Replace entire content of `qiita_scraper.py`:

```python
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
            article_items = soup.find_all("article", class_="style-1gr9egx")

            if not article_items:
                # フォールバック: 別のクラス名を試す
                article_items = soup.find_all("div", attrs={"data-hyperlink-target": "ArticleList"})

            for item in article_items:
                try:
                    # タイトルとURLを抽出
                    title_elem = item.find("h2") or item.find("a", class_="style-w8rf03")
                    if not title_elem:
                        continue

                    link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                    if not link_elem or not link_elem.get("href"):
                        continue

                    title = link_elem.get_text(strip=True)
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"{self.BASE_URL}{url}"

                    # いいね数を抽出（オプション）
                    likes = 0
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
```

**Step 4: Run test to verify scraping works**

Run: `python -m pytest test_qiita_scraper.py -v`
Expected: PASS (scraper returns list of articles)

**Step 5: Manual verification**

Run: `python -c "from qiita_scraper import QiitaScraper; s = QiitaScraper(top_n=3); print(s.run())"`
Expected: List of 3 articles with titles and URLs printed

**Step 6: Commit**

```bash
git add qiita_scraper.py test_qiita_scraper.py
git commit -m "Migrate Qiita scraper from API to web scraping

- Replace API calls with BeautifulSoup scraping
- Remove QIITA_API_TOKEN dependency
- Add rate limiting with time.sleep()
- Maintain same interface (run() method)"
```

---

## Task 3: Update main.py to Remove Qiita API Token

**Files:**
- Modify: `main.py:20-21`

**Step 1: Remove dotenv loading for Qiita token**

Current `main.py` line 20:
```python
def main():
    load_dotenv()
```

No changes needed here - `load_dotenv()` is still used for LINE token.

**Step 2: Verify main.py still works**

The main.py file already doesn't explicitly check for QIITA_API_TOKEN, so no changes needed.

**Step 3: Test full pipeline locally**

Create `.env` file with:
```
CHANNEL_ACCESS_TOKEN=your_line_token_here
```

Run: `python main.py`
Expected: Scrapes articles from all 3 sources and attempts LINE delivery

**Step 4: Commit (if any changes made)**

If no changes were needed, skip this step.

---

## Task 4: Update GitHub Actions Workflow

**Files:**
- Modify: `.github/workflows/daily_tech_digest.yml`

**Step 1: Update cron schedule to 8am JST**

Modify `.github/workflows/daily_tech_digest.yml` line 8:

Before:
```yaml
    - cron: "0 0 * * *"  # 9am JST
```

After:
```yaml
    - cron: "0 23 * * *"  # 8am JST (23:00 UTC previous day)
```

**Step 2: Remove QIITA_API_TOKEN from env**

Modify `.github/workflows/daily_tech_digest.yml` line 27-29:

Before:
```yaml
        env:
          QIITA_API_TOKEN: ${{ secrets.QIITA_API_TOKEN }}
          CHANNEL_ACCESS_TOKEN: ${{ secrets.CHANNEL_ACCESS_TOKEN }}
```

After:
```yaml
        env:
          CHANNEL_ACCESS_TOKEN: ${{ secrets.CHANNEL_ACCESS_TOKEN }}
```

**Step 3: Verify workflow syntax**

Run: `cat .github/workflows/daily_tech_digest.yml`
Expected: Valid YAML with updated cron and env vars

**Step 4: Commit**

```bash
git add .github/workflows/daily_tech_digest.yml
git commit -m "Update GitHub Actions workflow

- Change schedule to 8am JST (23:00 UTC)
- Remove QIITA_API_TOKEN (no longer needed)
- Keep CHANNEL_ACCESS_TOKEN for LINE delivery"
```

---

## Task 5: Update README with Setup Instructions

**Files:**
- Modify: `README.md`

**Step 1: Write comprehensive README**

Replace `README.md` content:

```markdown
# 技術記事配信用リポジトリ

GitHub Actions経由で技術記事を自動収集し、LINE Messaging APIでブロードキャスト配信するシステム。

## 機能

- **記事収集**: Qiita、Zenn、TechFeedから人気記事を取得
- **自動実行**: GitHub Actionsで毎日8時（JST）に自動実行
- **LINE配信**: LINE Messaging APIでブロードキャスト配信

## セットアップ

### 1. LINE Messaging APIの設定

1. [LINE Developers](https://developers.line.biz/console/) にアクセス
2. 新規プロバイダーとMessaging APIチャネルを作成
3. チャネルアクセストークン（長期）を発行
4. トークンをコピーして保存

### 2. GitHub Secretsの設定

1. GitHubリポジトリの **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. 以下のシークレットを追加：
   - Name: `CHANNEL_ACCESS_TOKEN`
   - Value: LINE Messaging APIのチャネルアクセストークン

### 3. ローカル実行（オプション）

ローカルでテストする場合：

1. 依存関係をインストール：
   ```bash
   pip install -r requirements.txt
   ```

2. `.env` ファイルを作成：
   ```
   CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   ```

3. 実行：
   ```bash
   python main.py
   ```

## 動作仕様

### 実行スケジュール
- **自動実行**: 毎日8時（JST）
- **手動実行**: GitHub Actionsの「Run workflow」ボタンから
- **プッシュ時**: mainブランチへのpush時（テスト用）

### 記事取得
- **Qiita**: Webスクレイピング（BeautifulSoup）
- **Zenn**: 公開API
- **TechFeed**: RSSフィード

各サービスから上位5件の記事を取得し、LINEで配信します。

### LINE配信方式
- **ブロードキャスト**: 公式アカウントの全フォロワーに配信
- **メッセージ形式**: テキストメッセージ（最大5000文字）

## トラブルシューティング

### GitHub Actionsが実行されない

1. **Actionsタブ**でワークフローの実行履歴を確認
2. cron設定を確認（`.github/workflows/daily_tech_digest.yml`）
3. 手動実行で動作確認

### LINE配信が失敗する

1. `CHANNEL_ACCESS_TOKEN` が正しく設定されているか確認
2. LINEチャネルが有効化されているか確認
3. GitHub Actionsのログでエラー内容を確認

### 記事が取得できない

- 各サービスのHTML構造が変更された可能性
- エラーログを確認してスクレイパーを更新

### よくあるエラー

**`CHANNEL_ACCESS_TOKEN が設定されていません`**
- GitHub Secretsに `CHANNEL_ACCESS_TOKEN` を追加

**`LINE送信エラー`**
- トークンが正しいか確認
- LINEチャネルの設定を確認

## ログ確認

GitHub Actionsのログ：
1. リポジトリの **Actions** タブ
2. 該当のワークフロー実行をクリック
3. **Run daily digest** ステップで詳細ログを確認

## 技術スタック

- **Python 3.11**
- **BeautifulSoup4**: Qiitaスクレイピング
- **requests**: HTTP通信
- **feedparser**: TechFeed RSS解析
- **line-bot-sdk**: LINE Messaging API
- **GitHub Actions**: 自動実行

## ライセンス

MIT License
```

**Step 2: Verify README formatting**

Run: `cat README.md | head -20`
Expected: Well-formatted markdown with correct header

**Step 3: Commit**

```bash
git add README.md
git commit -m "Update README with comprehensive setup instructions

- Add LINE Messaging API setup guide
- Add GitHub Secrets configuration
- Add troubleshooting section
- Document execution schedule and behavior"
```

---

## Task 6: Clean Up Test Files

**Files:**
- Delete: `test_qiita_scraper.py` (if created in project root)

**Step 1: Remove test file from project root**

Run: `rm -f test_qiita_scraper.py`
Expected: File removed (tests are for development only)

**Step 2: Commit**

```bash
git add -A
git commit -m "Remove temporary test file"
```

---

## Task 7: Final Verification and Push

**Files:**
- N/A (verification only)

**Step 1: Run full pipeline locally**

Ensure `.env` has `CHANNEL_ACCESS_TOKEN`:
```bash
python main.py
```

Expected output:
```
=== 記事取得開始 ===
Qiita 対象日: 2026-02-14
Qiita: 記事を取得中...
Qiita Page 1 完了 (20件)
...
取得結果: Qiita=5件, Zenn=5件, TechFeed=5件
LINEメッセージを送信しました
=== 完了 ===
```

**Step 2: Verify git status**

Run: `git status`
Expected: "nothing to commit, working tree clean" OR only .env file untracked

**Step 3: Review commit history**

Run: `git log --oneline -10`
Expected: All commits from this plan visible

**Step 4: Push to GitHub**

```bash
git push origin main
```

Expected: All commits pushed successfully

**Step 5: Verify GitHub Actions**

1. Go to GitHub repository → Actions tab
2. Verify workflow file appears
3. Click "Run workflow" button to test manually
4. Wait for execution and check logs

Expected: Workflow runs successfully, articles scraped, LINE message sent

---

## Post-Implementation Checklist

- [ ] All dependencies in `requirements.txt`
- [ ] Qiita scraper uses BeautifulSoup (no API token)
- [ ] GitHub Actions runs at 8am JST
- [ ] `CHANNEL_ACCESS_TOKEN` configured in GitHub Secrets
- [ ] README has complete setup instructions
- [ ] Local execution works
- [ ] GitHub Actions execution works
- [ ] LINE message delivered successfully

---

## Notes for Engineer

**Testing Strategy:**
- Test each scraper individually before running full pipeline
- Use manual GitHub Actions execution before relying on cron
- Monitor first few automated runs to catch issues

**Error Handling:**
- Each scraper returns `[]` on failure
- Pipeline continues even if one scraper fails
- All errors logged to stdout for GitHub Actions

**Maintenance:**
- Qiita HTML structure may change - update selectors in `qiita_scraper.py`
- Monitor GitHub Actions execution logs weekly
- Update dependencies periodically

**Rate Limiting:**
- Qiita scraper includes 1-second delay between pages
- No authentication = no rate limit tracking
- If blocked, increase delay in `time.sleep()`

**Security:**
- Never commit `.env` file (in `.gitignore`)
- Keep `CHANNEL_ACCESS_TOKEN` in GitHub Secrets only
- Rotate LINE token if compromised
