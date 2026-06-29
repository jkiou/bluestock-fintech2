"""
src/nlp/sentiment.py
NLP Sentiment Analysis Engine for Nifty 100 Financial Platform.

Provides:
  • analyse_text()         — VADER + keyword sentiment scoring
  • classify_headline()    — Bullish / Bearish / Neutral label
  • analyse_batch()        — process a list of texts with company tagging
  • score_company()        — aggregate sentiment score for a given ticker
"""
import re
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger("nlp.sentiment")

# ---------------------------------------------------------------------------
# Try VADER (nltk); fall back to a lexicon-only approach if not available
# ---------------------------------------------------------------------------
try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
    try:
        _sia = SentimentIntensityAnalyzer()
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
        _sia = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except Exception:
    _sia = None
    VADER_AVAILABLE = False
    logger.warning("VADER not available — using keyword-only sentiment")

# ---------------------------------------------------------------------------
# Finance-domain keyword lexicon (augments VADER)
# ---------------------------------------------------------------------------
BULLISH_WORDS = {
    "profit", "revenue", "growth", "expansion", "dividend", "buyback",
    "record", "beat", "surge", "rally", "upgrade", "outperform", "strong",
    "positive", "recovery", "gain", "boost", "innovation", "partnership",
    "award", "acquisition", "synergy", "upside", "margin", "guidance",
}
BEARISH_WORDS = {
    "loss", "debt", "default", "downgrade", "underperform", "miss", "weak",
    "decline", "slump", "fraud", "penalty", "investigation", "writeoff",
    "impairment", "layoff", "restructure", "bankruptcy", "warning", "risk",
    "slowdown", "headwind", "recall", "lawsuit", "fine",
}
NEGATIVE_MODIFIERS = {"not", "no", "never", "despite", "fail", "failed"}


def _keyword_score(text: str) -> float:
    """Simple keyword-based sentiment score in [-1, 1]."""
    tokens = re.findall(r"\b[a-z]+\b", text.lower())
    bull  = sum(1 for t in tokens if t in BULLISH_WORDS)
    bear  = sum(1 for t in tokens if t in BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return 0.0
    return (bull - bear) / total


def analyse_text(text: str) -> dict:
    """
    Analyse a single text string.

    Returns
    -------
    dict with keys:
      compound  float  [-1, 1]   overall score
      positive  float  [0, 1]
      negative  float  [0, 1]
      neutral   float  [0, 1]
      label     str    Bullish | Bearish | Neutral
      keyword_score  float  [-1, 1]
      method    str    vader | keyword
    """
    kw_score = _keyword_score(text)

    if VADER_AVAILABLE:
        scores = _sia.polarity_scores(text)
        compound  = scores["compound"]
        positive  = scores["pos"]
        negative  = scores["neg"]
        neutral   = scores["neu"]
        # Blend VADER compound with keyword score (70% / 30%)
        blended = 0.7 * compound + 0.3 * kw_score
        method = "vader"
    else:
        blended  = kw_score
        compound = kw_score
        positive = max(0.0, kw_score)
        negative = max(0.0, -kw_score)
        neutral  = 1.0 - abs(kw_score)
        method = "keyword"

    # Classify
    if blended >= 0.05:
        label = "Bullish"
    elif blended <= -0.05:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "compound":      round(blended, 4),
        "positive":      round(positive, 4),
        "negative":      round(negative, 4),
        "neutral":       round(neutral, 4),
        "label":         label,
        "keyword_score": round(kw_score, 4),
        "method":        method,
    }


def classify_headline(headline: str) -> str:
    """Quick single-line API: returns 'Bullish', 'Bearish', or 'Neutral'."""
    return analyse_text(headline)["label"]


def analyse_batch(
    texts: list,
    tickers: Optional[list] = None,
    companies: Optional[list] = None,
) -> pd.DataFrame:
    """
    Analyse a batch of texts.

    Parameters
    ----------
    texts    : list of str — input headlines / paragraphs
    tickers  : optional list of str — ticker associated with each text
    companies: optional list of str — company name associated with each text

    Returns
    -------
    pd.DataFrame with columns: text, ticker, company, compound, label, ...
    """
    results = []
    for i, text in enumerate(texts):
        row = analyse_text(text)
        row["text"] = text[:200]
        row["ticker"]  = tickers[i]  if tickers  and i < len(tickers)  else None
        row["company"] = companies[i] if companies and i < len(companies) else None
        results.append(row)
    return pd.DataFrame(results)


def score_company(
    ticker: str,
    headlines: list,
    window_weights: Optional[list] = None,
) -> dict:
    """
    Aggregate sentiment score for a company from multiple headlines.

    Parameters
    ----------
    ticker         : str — company ticker
    headlines      : list of str — news headlines / blurbs
    window_weights : optional list of floats (most-recent=higher weight)

    Returns
    -------
    dict with keys: ticker, avg_compound, dominant_label, num_articles, distribution
    """
    if not headlines:
        return {"ticker": ticker, "avg_compound": 0.0, "dominant_label": "Neutral",
                "num_articles": 0, "distribution": {}}
    df = analyse_batch(headlines, tickers=[ticker] * len(headlines))
    if window_weights and len(window_weights) == len(df):
        weights = pd.Series(window_weights, dtype=float)
        weights /= weights.sum()
        avg_compound = (df["compound"] * weights).sum()
    else:
        avg_compound = df["compound"].mean()

    dist = df["label"].value_counts().to_dict()
    dominant = df["label"].mode().iloc[0] if not df.empty else "Neutral"
    return {
        "ticker":          ticker,
        "avg_compound":    round(float(avg_compound), 4),
        "dominant_label":  dominant,
        "num_articles":    len(df),
        "distribution":    dist,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-8s | %(message)s")
    # Demo
    sample_headlines = [
        "Reliance Industries reports record quarterly profit driven by Jio and Retail growth",
        "HDFC Bank misses earnings estimates amid rising bad loans",
        "TCS wins $500 million deal with European banking consortium",
        "Infosys downgrades revenue guidance for fiscal year",
        "Wipro announces share buyback programme worth ₹12,000 crore",
    ]
    df = analyse_batch(sample_headlines, tickers=["RELIANCE", "HDFCBANK", "TCS", "INFY", "WIPRO"])
    print(df[["ticker", "text", "label", "compound"]].to_string(index=False))
