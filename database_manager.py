# database_manager.py
from __future__ import annotations
from typing import List, Tuple
from manuals_data import MANUALS_DATA


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def search_manuals_by_keyword(query: str) -> List[Tuple[str, str]]:
    """
    入力キーワード（空白区切り AND）で、title/body/keywords を横断検索。
    返り値: [(title, body), ...]
    """
    q = _norm(query)
    if not q:
        # 空ならタイトル昇順で全件
        items = sorted(MANUALS_DATA, key=lambda x: _norm(x.get("title", "")))
        return [(it.get("title", ""), it.get("body", "")) for it in items]

    tokens = [t for t in q.split() if t]
    hits = []
    for it in MANUALS_DATA:
        hay = "\n".join(
            [
                it.get("title", ""),
                it.get("body", ""),
                it.get("keywords", ""),
            ]
        ).lower()
        # AND マッチ
        if all(tok in hay for tok in tokens):
            hits.append(it)

    # タイトル昇順で整列
    hits.sort(key=lambda x: _norm(x.get("title", "")))
    return [(it.get("title", ""), it.get("body", "")) for it in hits]
