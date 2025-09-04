# DB初期化はこのファイルでできます
# SQLiteデータベースの初期化スクリプト
# shared_house.db に必要なテーブル（tasks, members, cleaning_logsなど）を作成します。
# 初回セットアップやDB構造の確認・再生成に使用します。


import sqlite3

def create_tables():
    conn = sqlite3.connect('shared_house.db')
    c = conn.cursor()

    # 掃除タスクのテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    task_name TEXT,
                    is_done BOOLEAN,
                    assigned_to TEXT)''')

    # 在宅メンバーのテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    is_home BOOLEAN)''')

    # 掃除ログのテーブル ← ここを追加！
    c.execute('''CREATE TABLE IF NOT EXISTS cleaning_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slack_user_id TEXT,
                    location TEXT,
                    note TEXT,
                    timestamp DATETIME)''')

    conn.commit()
    conn.close()

# 関数を実行
create_tables()
