# Homeタブの描画だけを担当
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
                            "text": "*シェアハウス共同生活管理アプリ*\n最小構成が動いています！",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "マニュアルを見る"},
                                "action_id": "open_manuals",
                            }
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• 在宅トグル（近日）\n• 掃除チェック（近日）\n• マニュアル閲覧（今ここ）",
                        },
                    },
                ],
            },
        )
