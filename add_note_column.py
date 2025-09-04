import sqlite3

def add_note_column():
    conn = sqlite3.connect("shared_house.db")
    cursor = conn.cursor()

    # note カラムがすでにあるか確認（簡易チェック）
    cursor.execute("PRAGMA table_info(cleaning_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if "note" not in columns:
        cursor.execute("ALTER TABLE cleaning_logs ADD COLUMN note TEXT;")
        print("note カラムを追加しました！")
    else:
        print("note カラムはすでに存在しています。")

    conn.commit()
    conn.close()

add_note_column()
