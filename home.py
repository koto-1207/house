# home.py
def register_home(app):
    @app.event("app_home_opened")
    def on_home_opened(event, client, logger):
        user_id = event["user"]
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*シェアハウス共同生活管理アプリ*\nがんばって機能を増やそう",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "マニュアルを見る"},
                                # PDFのURL リンク貼り直せば更新可能
                                "url": "https://drive.google.com/file/d/1t3riT_PCh5vqPKxbQNg82AsrVli2BRkf/view?usp=drive_link",
                                "action_id": "open_manuals",
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "在宅状況"},
                                "action_id": "open_presence",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• 掃除チェック（まだ）\n• あとなにいる？",
                        },
                    },
                ],
            },
        )
