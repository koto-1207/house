# database_manager.py

import sqlite3

DATABASE_FILE = "manuals.db"


def init_db():
    """
    データベースファイルを初期化し、マニュアルテーブルを作成します。
    """
    conn = None
    try:
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
    except sqlite3.Error as e:
        print(f"データベース初期化エラー: {e}")
    finally:
        if conn:
            conn.close()


def insert_initial_data():
    """
    初期マニュアルデータをデータベースに挿入します。
    重複を防ぐため、存在しない場合のみ挿入します。
    """
    manuals_data = [
        {
            "title": "使用料",
            "body": "志業シェアハウスの使用料は、月額9,000円です。ただし、使用開始日や退去日の属する月については「月額×使用日数/その月の日数」で算出します。",
            "keywords": "使用料,月額,,部屋,退去日,",
        },
        {
            "title": "宿泊",
            "body": "スパルタキャンプ前日から終了日の翌日の宿泊まで、町への申請により「平泉町志業シェアハウス使用許可決定通知書の交付を受けた方のみ、宿泊可能です。使用開始時にシェアハウス玄関と個室の鍵をお渡ししますので、退去まで紛失することのないよう各自で責任をもって管理してください。使用許可者以外の方で無断で施設内に入れることは固く禁止します。スパルタキャンプ受講生で、宿泊以外で学習のため使用したいという方も町への申請が必要となります。(※講座開催期間中に開催される対面サポートは除く) 各部屋の使用後は、戸締まりやエアコン・電灯等を十分に確認し、防犯・節電・節水に努めてください。",
            "keywords": "宿泊,使用許可,宿泊可,",
        },
        {
            "title": "施錠について",
            "body": "貴重品を管理する金庫等はありませんので、個室を離れる際は必ず施錠するなど防犯に努めて下さい。また、外出の際には必ず玄関を施錠するように心がけて下さい。帰舎時も同様です。 ",
            "keywords": "施錠,防犯,外出,帰舎,玄関",
        },
        {
            "title": "アメニティ",
            "body": "必要最低限の生活用品は準備しておりますが、アメニティ類はありませんので、必要なものは各自で用意してください。",
            "keywords": "アメニティ,生活用品,用意,必要,最低限",
        },
        {
            "title": "シェアハウスで準備していない主な物品",
            "body": "歯磨き用品、入浴用品(洗面器、浴室イス以外)、タオル(バスタオル含む)、ドライヤー、屋内用スリッパ(旅館時代のものがありますが数にかぎりがありますので常時使用不可とします)、ティッシュペーパー、座布団等",
            "keywords": "生活用品,歯磨き,入浴,タオル,ドライヤー,屋内用スリッパ,ティッシュペーパー,座布団",
        },
        {
            "title": "お金に関すること",
            "body": "シェアハウスでは「自分のことは自分で」が基本ルールとなりますが、食費をはじめ、費用を出し合って負担する場合は、例外なく必ず均等に負担してください。年齢や職業などそれぞれ違いはありますが、受講生として立場は同じであることをしっかりと認識し、十分な生活費の準備をお願いします",
            "keywords": "生活費,均等,負担,お金",
        },
        {
            "title": "ゴミ出しルール",
            "body": "燃えるゴミは月/木の朝8:00までに玄関前のカゴへ。ラベル貼付＆袋口を結ぶこと。",
            "keywords": "ゴミ出し,ルール,燃えるゴミ,ごみ,だ,し",
        },
        {
            "title": "静音タイム",
            "body": "22:00〜7:00は通話・音楽・ドアの開閉音に配慮。共用部での打合せは避ける。",
            "keywords": "静音,時間,ルール,夜",
        },
        {
            "title": "共有キッチン",
            "body": "調理後は5分以内に片付け。シンク洗浄・コンロ拭き・生ゴミは密封廃棄。",
            "keywords": "キッチン,共有,ルール,清掃,台所",
        },
        {
            "title": "施設概要",
            "body": "平泉町志業シェアハウスは岩手県西磐井郡平泉町にあります。個室5室と共用部（キッチン、リビングなど）が利用可能です。",
            "keywords": "概要,場所,アクセス,部屋,設備,平泉町",
        },
        {
            "title": "アクセス",
            "body": "自動車は平泉前沢ICまたは平泉スマートICから5分、電車はJR平泉駅から徒歩10分です。",
            "keywords": "アクセス,交通,自動車,電車,平泉駅",
        },
    ]

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        for manual in manuals_data:
            c.execute(
                "INSERT OR IGNORE INTO manuals (title, body, keywords) VALUES (?, ?, ?)",
                (manual["title"], manual["body"], manual["keywords"]),
            )
        conn.commit()
    except sqlite3.Error as e:
        print(f"データ挿入エラー: {e}")
    finally:
        if conn:
            conn.close()


def search_manuals_by_keyword(keyword: str):
    """
    キーワードに基づいてマニュアルを検索します。
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT title, body FROM manuals WHERE keywords LIKE ?",
            (f"%{keyword}%",),
        )
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"検索エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_all_manuals():
    """
    すべてのマニュアルをデータベースから取得します。
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT title, body FROM manuals")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"データ取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()
