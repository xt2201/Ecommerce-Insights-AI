"""Utility helpers for data normalization, scoring, and formatting."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

Number = Optional[float]

_PRICE_PATTERN = re.compile(r"[\d,.]+")


def parse_price(value: object) -> Number:
    """Attempt to coerce a price-like value into a float.

    Accepts strings containing currency characters and standard decimal separators.
    Returns ``None`` when parsing fails.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        match = _PRICE_PATTERN.search(value.replace(" ", ""))
        if not match:
            return None
        normalized = match.group().replace(",", "")
        try:
            return float(normalized)
        except ValueError:
            return None

    return None


def deduplicate_by_key(items: Iterable[dict], key: str) -> List[dict]:
    """Deduplicate dictionaries by a specific key while preserving order."""

    seen = set()
    unique: List[dict] = []
    for item in items:
        marker = item.get(key)
        if marker and marker in seen:
            continue
        if marker:
            seen.add(marker)
        unique.append(item)
    return unique


def compute_value_score(price: Number, rating: Number, review_count: Number) -> Number:
    """Compute a heuristic value score combining price, rating, and review count."""

    if price is None or price <= 0:
        price_component = 0.0
    else:
        price_component = min(1.0, 500.0 / price)

    rating_component = (rating or 0.0) / 5.0
    reviews_component = min(1.0, (review_count or 0.0) / 1000.0)

    score = (0.4 * rating_component) + (0.4 * reviews_component) + (0.2 * price_component)
    return round(score, 4)
