# Multi-Platform Scraping Design

**Date**: 2026-03-07
**Status**: Approved

## Overview

Expand the scraping targets from Qiita+Zenn (combined best-of-1) to Qiita, Zenn, note, Reddit (1 article per platform = 4 articles/day).

## Requirements

- Add note.com scraper (trending page, AI selects best tech article)
- Add Reddit r/technology scraper (public JSON API, top posts of the day)
- Each platform posts its own Discord forum thread (4 threads/day)
- Qiita and Zenn each post their own best article (no longer combined)

## Architecture

### New Files
- `note_scraper.py` — scrapes note.com/trending, returns top 10-15 articles
- `reddit_scraper.py` — calls Reddit public JSON API for r/technology top-day posts

### Changed Files
- `main.py` — platform list approach; loop over PLATFORMS tuple
- `summarizer.py` — add `prefer_tech: bool` to `select_best()` for note filtering
- `send_to_discord.py` — pass `platform_name` and `emoji` to thread name

### Platform List in main.py
```python
PLATFORMS = [
    ("Qiita",  "🗾", QiitaScraper(top_n=5)),
    ("Zenn",   "📚", ZennScraper(top_n=5)),
    ("note",   "📝", NoteScraper(top_n=15)),
    ("Reddit", "👽", RedditScraper(top_n=10)),
]
```

## Data Flow

```
for each platform:
  articles = scraper.run()        # list of {title, url, ...}
  idx = summarizer.select_best(articles, prefer_tech=...)
  text = fetch_article_text(url)
  summary = summarizer.summarize(title, text)
  messenger.post_best_article(article, summary, platform_name, emoji)
```

## note Scraper

- Source: `https://note.com/trending`
- Method: BeautifulSoup scraping
- Filter: `select_best(prefer_tech=True)` — Gemini selects the most tech-relevant article

## Reddit Scraper

- Source: `https://www.reddit.com/r/technology/top.json?t=day&limit=10`
- Method: Public JSON API (no auth required)
- Filter: `select_best()` — Gemini selects the most interesting article

## Discord Thread Naming

Format: `{date} {platform_name} 注目記事`
Example: `2026-03-07 Qiita 注目記事`, `2026-03-07 note 注目記事`

## Error Handling

- Each platform processed independently; failure in one does not affect others
- Existing fallback patterns retained (empty article list → skip platform)
