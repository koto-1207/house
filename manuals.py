# 「マニュアルを見る」ボタン→モーダルを開く
def register_manuals(app):
    @app.action("open_manuals")
    def open_manuals(ack, body, client, logger):
        ack()
        trigger_id = body["trigger_id"]

        manuals = [
            {
                "title": "ゴミ出しルール",
                "body": "燃えるゴミは *月/木の朝8:00* までに玄関前のカゴへ。ラベル貼付＆袋口を結ぶこと。",
            },
            {
                "title": "静音タイム",
                "body": "*22:00〜7:00* は通話・音楽・ドアの開閉音に配慮。共用部での打合せは避ける。",
            },
            {
                "title": "共有キッチン",
                "body": "調理後は*5分以内*に片付け。シンク洗浄・コンロ拭き・生ゴミは密封廃棄。",
            },
        ]

        blocks = []
        for m in manuals:
            blocks.extend(
                [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*{m['title']}*\n{m['body']}"}},
                    {"type": "divider"},
                ]
            )
        if blocks:
            blocks.pop()  # 最後のdividerを削除

        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "マニュアル"},
                "close": {"type": "plain_text", "text": "閉じる"},
                "blocks": blocks
                or [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "まだマニュアルが登録されていません。"},
                    }
                ],
            },
        )
