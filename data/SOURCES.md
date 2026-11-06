# SIP Insight Lab — Data Sources & ToS Compliance

> **Owner:** Growth PM, Groww  
> **Last Updated:** 2026-10-31  
> **Purpose:** Documents the data sources used by SIP Insight Lab, the
> legal/ToS basis for collecting from each, and the operational rules
> that enforce compliance.

---

## Collection Principle

> Public feedback is treated as a source of **hypotheses only**.  
> It is NOT used as a measure of retention or proof of causality.  
> All collected data is anonymised before any analysis or storage.

---

## Source 1 — Google Play Store

| Field | Detail |
|---|---|
| **Target App** | Groww — Stocks & Mutual Fund (`com.nextbillion.groww`) |
| **Method** | Public review scraper (no login required) |
| **ToS Reference** | Google Play reviews are publicly visible; collection for academic/research purposes is widely accepted. No rate-limiting violation if requests are spaced ≥ 2 seconds. |
| **Data Collected** | Star rating, review text, reviewer pseudonym (discarded), app version, review date |
| **PII Risk** | Low — reviewer display names are discarded; text is PII-scrubbed before storage |
| **Request Delay** | 2 seconds between requests |
| **Compliance Status** | ✅ Approved |

---

## Source 2 — Apple App Store

| Field | Detail |
|---|---|
| **Target App** | Groww — Invest, Stocks & SIP (App ID: `1404457431`) |
| **Method** | iTunes RSS API (`itunes.apple.com/in/rss/customerreviews/`) — public, official endpoint |
| **ToS Reference** | Apple's public RSS feeds are designed for third-party consumption. |
| **Data Collected** | Star rating, review text, reviewer pseudonym (discarded), country, date |
| **PII Risk** | Low — reviewer display names discarded; text PII-scrubbed |
| **Request Delay** | 1 second between requests |
| **Compliance Status** | ✅ Approved |

---

## Source 3 — Reddit

| Field | Detail |
|---|---|
| **Target Subreddits** | r/IndiaInvestments, r/mutualfunds, r/Groww, r/personalfinanceindia |
| **Method** | Reddit Public API via PRAW (OAuth, read-only scope) |
| **ToS Reference** | Reddit Developer Terms of Service allow API access for research. Read-only scope. Rate limit: 100 requests/minute (PRAW handles automatically). |
| **Data Collected** | Post/comment text, post score, subreddit name, created UTC timestamp |
| **PII Risk** | Medium — usernames visible; discarded before storage; text PII-scrubbed |
| **Request Delay** | PRAW rate-limiter (automatic) |
| **Compliance Status** | ✅ Approved — requires valid OAuth credentials in `.env` |

> ⚠️ **Note:** Reddit's API terms changed in 2023. Academic/non-commercial research use is permitted. Re-verify before any commercial deployment.

---

## Source 4 — TradingQ&A

| Field | Detail |
|---|---|
| **Target URL** | `https://tradingqna.com` |
| **Method** | HTTP scraper (Requests + BeautifulSoup); respects `robots.txt` |
| **ToS Reference** | TradingQ&A content is publicly accessible without login. Scraping for research is permitted provided `robots.txt` is respected and rate limits are honoured. |
| **Data Collected** | Question/answer text, tags, vote count, post date |
| **PII Risk** | Low — usernames discarded; text PII-scrubbed |
| **Request Delay** | 3 seconds between requests |
| **Compliance Status** | ✅ Approved — verify `robots.txt` before each collection run |

---

## Source 5 — YouTube

| Field | Detail |
|---|---|
| **Target Videos** | Top Groww and personal-finance SIP-related videos (via search API) |
| **Method** | YouTube Data API v3 (official Google API, API key required) |
| **ToS Reference** | YouTube API Services Terms of Service permit comment retrieval for non-commercial research. Quota: 10,000 units/day (free tier). |
| **Data Collected** | Comment text, video ID, comment like count, published date |
| **PII Risk** | Low — commenter display names discarded; text PII-scrubbed |
| **Request Delay** | 1 second between requests; quota monitored |
| **Compliance Status** | ✅ Approved — requires YouTube Data API v3 key in `.env` |

---

## Global Compliance Rules (apply to all sources)

1. **No private data** — Only publicly visible content is collected. No authenticated sessions beyond approved API OAuth.
2. **No personal identifiers stored** — Usernames, display names, and profile links are discarded at ingestion time, before DB write.
3. **robots.txt respected** — All HTTP scrapers check `robots.txt` before each collection run.
4. **Rate limits honoured** — Per-source delays are configured in `config.yaml` and enforced in the ingestion queue.
5. **Deduplication** — SHA-256 hash prevents the same item from being stored twice.
6. **Research purpose only** — Data is used solely to generate anonymised product hypotheses for Groww's Growth team. No data is sold, shared, or used for advertising.
7. **PII scrub before any downstream use** — Raw text is only used to populate `raw_item`. All analysis uses `cleaned_item` which has been PII-scrubbed.

---

## Compliance Review Schedule

| Action | Frequency |
|---|---|
| Re-verify `robots.txt` for TradingQ&A | Before each collection run |
| Re-verify Reddit API ToS | Monthly |
| Check YouTube API quota usage | Weekly |
| Full ToS review for all sources | Every 6 months |

---

*Approved by: [PM Name] — [Date]*  
*Next review: [Date + 6 months]*
