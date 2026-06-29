"""
src/nlp/__init__.py
NLP package — sentiment analysis for financial news.
"""
from .sentiment import analyse_text, classify_headline, analyse_batch, score_company

__all__ = ["analyse_text", "classify_headline", "analyse_batch", "score_company"]
