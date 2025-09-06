# event_handlers.py
from __future__ import annotations
from database_manager import search_manuals_by_keyword


def register_event_handlers(app):
    # 起動時に Bot User ID をキャッシュ
    _auth = app.client.auth_test()
    BOT_USER_ID = _auth.get("user_id")

    @app.event("app_mention")
    def on_mention(event, say, logger):
        text = event.get("text", "") or ""
        # メンション部分を除去
        query = text.replace(f"<@{BOT_USER_ID}>", "").strip()

        # 追加：掃除チェックはクエリから取り除く
        if "掃除チェック" in query:
            query = query.replace("掃除チェック", "").strip()

        if not query:
            say("こんにちは！ 検索したいキーワードをメンション付きで送ってください（例：`@bot ごみ出し`）。")
            return

        results = search_manuals_by_keyword(query)
        if not results:
            say(text=f"'{query}' に一致するマニュアルは見つかりませんでした。")
            return

        title, body_text = results[0]
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{body_text}"}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "次の結果"},
                        "action_id": "next_manual",
                        "value": f"0|{query}",
                    }
                ],
            },
        ]
        say(text=f"{title} - {body_text}", blocks=blocks)

    @app.action("next_manual")
    def handle_next_manual(ack, body, client, logger):
        ack()
        try:
            value = body["actions"][0]["value"]
            index_str, query = value.split("|", 1)
            index = int(index_str) + 1

            results = search_manuals_by_keyword(query)
            # payload から channel/ts を安全に取得
            channel_id = (body.get("channel") or {}).get("id") or (body.get("container") or {}).get(
                "channel_id"
            )
            message_ts = (body.get("message") or {}).get("ts") or (body.get("container") or {}).get(
                "message_ts"
            )

            if not channel_id or not message_ts:
                logger.warning("next_manual: channel_id/message_ts が取得できませんでした")
                return

            if index >= len(results):
                client.chat_update(
                    channel=channel_id, ts=message_ts, text="これ以上の検索結果はありません。", blocks=[]
                )
                return

            title, body_text = results[index]
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{body_text}"}},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "次の結果"},
                            "action_id": "next_manual",
                            "value": f"{index}|{query}",
                        }
                    ],
                },
            ]
            client.chat_update(
                channel=channel_id, ts=message_ts, text=f"{title} - {body_text}", blocks=blocks
            )
        except Exception as e:
            logger.exception(e)
