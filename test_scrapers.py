import os
import logging
import sys
import datetime
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from main import fetch_article_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_scraping():
    load_dotenv()
    
    # テスト用に、昨日と今日の日付で記事取得を試みる
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"=== Testing Qiita Scraper (Target: {today_str} or {yesterday_str}) ===")
    qiita = QiitaScraper(top_n=1)
    
    # 取得できるまで今日、昨日の順に試行
    qiita_articles = []
    for target_date in [today_str, yesterday_str]:
        print(f"Checking Qiita articles for {target_date}...")
        qiita.yesterday_str = target_date
        qiita_articles = qiita.run()
        if qiita_articles:
            break

    if qiita_articles:
        article = qiita_articles[0]
        print(f"Success: Found {len(qiita_articles)} Qiita articles.")
        print(f"Article: {article['title']} ({article['url']})")
        
        text = fetch_article_text(article['url'])
        print(f"Extracted text length: {len(text)} characters.")
        if text:
            print(f"Preview (first 100 chars): {text[:100].replace('\\n', ' ')}...")
    else:
        print("Failed: No Qiita articles found.")

    print("\n=== Testing Zenn Scraper (Target: {today_str} or {yesterday_str}) ===")
    zenn = ZennScraper(top_n=1)
    
    zenn_articles = []
    for target_date in [today_str, yesterday_str]:
        print(f"Checking Zenn articles for {target_date}...")
        zenn.yesterday_str = target_date
        zenn_articles = zenn.run()
        if zenn_articles:
            break

    if zenn_articles:
        article = zenn_articles[0]
        print(f"Success: Found {len(zenn_articles)} Zenn articles.")
        print(f"Article: {article['title']} ({article['url']})")
        
        text = fetch_article_text(article['url'])
        print(f"Extracted text length: {len(text)} characters.")
        if text:
            print(f"Preview (first 100 chars): {text[:100].replace('\\n', ' ')}...")
    else:
        print("Failed: No Zenn articles found.")

if __name__ == "__main__":
    test_scraping()
