# database_manager.py

import sqlite3
from rapidfuzz import fuzz
import re
from manuals_data import manuals_data  # 分割したデータをインポート

DATABASE_FILE = "manuals.db"

KEYWORD_MAP = {
    "捨": "ごみ",
    "棄": "ごみ",
    "不燃": "燃やせないごみ",
    "可燃": "燃えるごみ",
    "生ごみ": "燃えるごみ",
    "燃える": "燃えるごみ",
    "燃やせない": "燃やせないごみ",
    "ロック": "施錠",
    "閉める": "施錠",
    "鍵忘れ": "鍵",
    "インロック": "鍵",
    "費用": "料金",
    "支払い": "料金",
    "お金": "料金",
    "家賃": "料金",
    "泊まる": "宿泊",
    "宿泊可": "宿泊",
    "ゲスト": "宿泊",
    "掃除": "清掃",
    "ゴミ出し": "ごみ出し",
    "Wi-Fi": "ネット",
    "インターネット": "ネット",
}


# データベース初期化
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS manuals (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            keywords TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def insert_initial_data():
    # 初期データ挿入
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    data_to_insert = [(m["title"], m["body"], m["keywords"]) for m in manuals_data]
    c.executemany("INSERT OR IGNORE INTO manuals (title, body, keywords) VALUES (?, ?, ?)", data_to_insert)
    conn.commit()
    conn.close()


def get_all_manuals():
    # 全マニュアル取得
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT title, body, keywords FROM manuals")
    rows = c.fetchall()
    conn.close()
    return rows


def preprocess_query(query: str):
    # 自然文から検索用キーワードを抽出
    query = re.sub(r"(について|教えて|知りたい|どうすれば)", "", query)
    query = re.sub(r"[ぁ-んァ-ヶー！？。、\s]+", "", query)
    for key, value in KEYWORD_MAP.items():
        if key in query:
            query = query.replace(key, value)
    return query


def search_manuals_by_keyword(query: str, threshold=75, max_results=5):
    """
    fuzzy検索でマニュアルを取得
    - タイトル＋キーワードを優先、本文は補助的に使用
    - 類似度 threshold 以上の上位 max_results 件を返す
    """
    query = preprocess_query(query)
    if not query:
        return []

    results = []
    for title, body, keywords in get_all_manuals():
        main_texts = [title, keywords]
        body_texts = [body]

        main_score = max(fuzz.partial_ratio(query, text) for text in main_texts)
        body_score = max(fuzz.partial_ratio(query, text) for text in body_texts)
        score = max(main_score, body_score * 0.7)

        if score >= threshold:
            results.append((title, body, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return [(title, body) for title, body, _ in results[:max_results]]
