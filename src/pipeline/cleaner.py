"""
Groww SIP Insight Lab — Data Cleaner & Normalizer
=================================================
Combines, cleans, and normalizes raw feedback across all sources:
- Google Play Store
- Apple App Store
- Reddit
- YouTube

Operations:
1. Normalizes source names and dates (ISO-8601 UTC).
2. Removes empty, whitespace-only, and trivial spam records (<10 chars).
3. Deduplicates via content hashing while preserving original raw text.
4. Produces unified combined schema:
   [record_id, source_id, source, date, rating, raw_text, cleaned_text, reference, url, char_length, word_count]
5. Saves to sip_feedback_combined.csv (root) and data/sip_feedback_combined.csv.
"""

import os
import sys
import re
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import dateutil.parser

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline.cleaner")

RAW_SOURCES = [
    {"name": "play_store", "path": RAW_DIR / "raw_play_store.csv"},
    {"name": "app_store", "path": RAW_DIR / "raw_app_store.csv"},
    {"name": "reddit", "path": RAW_DIR / "raw_reddit.csv"},
    {"name": "youtube", "path": RAW_DIR / "raw_youtube.csv"},
]


def normalize_source_name(source: str) -> str:
    """Normalizes source name to canonical identifier."""
    s = str(source).lower().strip()
    if "play" in s or "google" in s:
        return "play_store"
    if "app" in s or "apple" in s or "ios" in s:
        return "app_store"
    if "reddit" in s:
        return "reddit"
    if "you" in s or "yt" in s:
        return "youtube"
    return s


def normalize_timestamp(val) -> str:
    """Parses various date representations and returns ISO-8601 UTC string."""
    if val is None or pd.isna(val):
        return datetime.now(timezone.utc).isoformat()

    s = str(val).strip()
    if not s:
        return datetime.now(timezone.utc).isoformat()

    try:
        # Check if numeric timestamp
        if s.replace(".", "", 1).isdigit():
            ts = float(s)
            if ts > 1e11:  # ms
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.isoformat()

        dt = dateutil.parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except Exception:
        # Fallback to current UTC time if unparseable
        return datetime.now(timezone.utc).isoformat()


def clean_text_content(text: str) -> str:
    """Produces a clean normalized version of text while preserving semantics."""
    if not text:
        return ""
    # Normalize whitespaces and carriage returns
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def compute_content_hash(text: str, source: str) -> str:
    """Generates a stable 16-character SHA-256 fingerprint."""
    norm = re.sub(r"\W+", "", text.lower())
    payload = f"{source}:{norm}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def clean_and_combine_data() -> tuple[pd.DataFrame, dict]:
    """
    Loads all raw CSV files, applies cleaning and deduplication, and creates
    the combined dataset sip_feedback_combined.csv.
    """
    logger.info("Beginning data cleaning and normalization across raw sources...")
    all_dfs = []
    source_stats = {}

    for src in RAW_SOURCES:
        name = src["name"]
        path = src["path"]
        if not path.exists():
            logger.warning("Raw file missing for %s at %s. Skipping.", name, path)
            source_stats[name] = {"raw_count": 0, "cleaned_count": 0, "dropped_count": 0}
            continue

        try:
            df_raw = pd.read_csv(path, encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read %s: %s", path, e)
            source_stats[name] = {"raw_count": 0, "cleaned_count": 0, "dropped_count": 0}
            continue

        raw_count = len(df_raw)
        logger.info("Loaded raw %s with %d records.", name, raw_count)

        if raw_count == 0:
            source_stats[name] = {"raw_count": 0, "cleaned_count": 0, "dropped_count": 0}
            continue

        # Standardize columns
        for col in ["source_id", "source", "date", "rating", "raw_text", "reference", "url"]:
            if col not in df_raw.columns:
                df_raw[col] = None

        df_raw["source"] = name

        # Drop empty or invalid text
        df_clean = df_raw.dropna(subset=["raw_text"]).copy()
        df_clean["raw_text"] = df_clean["raw_text"].astype(str)
        df_clean = df_clean[df_clean["raw_text"].str.strip().str.len() >= 10]

        # Normalize date
        df_clean["date"] = df_clean["date"].apply(normalize_timestamp)

        # Normalize rating
        def parse_rating(r):
            if pd.isna(r) or r is None:
                return None
            try:
                val = float(r)
                return int(val) if val.is_integer() else val
            except (ValueError, TypeError):
                return None

        df_clean["rating"] = df_clean["rating"].apply(parse_rating)

        # Cleaned text and word metrics
        df_clean["cleaned_text"] = df_clean["raw_text"].apply(clean_text_content)
        df_clean["char_length"] = df_clean["cleaned_text"].str.len()
        df_clean["word_count"] = df_clean["cleaned_text"].apply(lambda t: len(t.split()))

        # Internal source deduplication
        before_dedup = len(df_clean)
        df_clean["_norm_text"] = df_clean["cleaned_text"].str.lower().str.replace(r"\W+", "", regex=True)
        df_clean = df_clean.drop_duplicates(subset=["_norm_text"]).drop(columns=["_norm_text"])
        cleaned_count = len(df_clean)

        source_stats[name] = {
            "raw_count": raw_count,
            "cleaned_count": cleaned_count,
            "dropped_count": raw_count - cleaned_count,
        }
        all_dfs.append(df_clean)

    if not all_dfs:
        logger.error("No valid data found in raw sources.")
        return pd.DataFrame(), source_stats

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info("Combined dataset has %d total records across %d sources before global dedup.", len(combined), len(all_dfs))

    # Cross-source deduplication (if identical text appears in multiple sources)
    combined["_global_norm"] = combined["cleaned_text"].str.lower().str.replace(r"\W+", "", regex=True)
    combined = combined.drop_duplicates(subset=["_global_norm"]).drop(columns=["_global_norm"])

    # Generate unique ID: e.g. GROWW_FEEDBACK_0001 or hash-based ID
    combined["record_id"] = [
        f"GFB_{compute_content_hash(row['cleaned_text'], row['source'])}"
        for _, row in combined.iterrows()
    ]

    # Reorder columns
    ordered_cols = [
        "record_id",
        "source_id",
        "source",
        "date",
        "rating",
        "raw_text",
        "cleaned_text",
        "reference",
        "url",
        "char_length",
        "word_count",
    ]
    combined = combined[ordered_cols]

    # Save to both project root and data directory
    combined_root_path = PROJECT_ROOT / "sip_feedback_combined.csv"
    combined_data_path = DATA_DIR / "sip_feedback_combined.csv"

    combined.to_csv(combined_root_path, index=False, encoding="utf-8")
    combined.to_csv(combined_data_path, index=False, encoding="utf-8")

    logger.info("Saved %d cleaned records to %s and %s", len(combined), combined_root_path, combined_data_path)
    return combined, source_stats


if __name__ == "__main__":
    df, stats = clean_and_combine_data()
    print(f"Cleaning complete. Total cleaned: {len(df)}")
    for s, st in stats.items():
        print(f"  - {s}: raw={st['raw_count']} -> clean={st['cleaned_count']} (dropped {st['dropped_count']})")

