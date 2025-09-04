import sqlite3

def create_tables():
    # shared_house.dbという名前のデータベースファイルを作成または接続
    conn = sqlite3.connect('shared_house.db')
    c = conn.cursor()

    # 掃除タスクのテーブルを作成
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    task_name TEXT,
                    is_done BOOLEAN,
                    assigned_to TEXT)''')

    # 在宅メンバーのテーブルを作成
    c.execute('''CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    is_home BOOLEAN)''')

    # コミットして変更を保存
    conn.commit()

    # データベース接続を閉じる
    conn.close()

# テーブルを作成
create_tables()
