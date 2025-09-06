# manuals.py
from typing import List, Dict, Any
from slack_bolt import App
from slack_sdk.web.client import WebClient
from database_manager import search_manuals_by_keyword


def _build_manuals_modal(query: str = "") -> Dict[str, Any]:
    results = search_manuals_by_keyword(query)
    blocks: List[Dict[str, Any]] = []

    # 検索フィールド
    blocks.append(
        {
            "type": "input",
            "block_id": "manuals_search",
            "element": {
                "type": "plain_text_input",
                "action_id": "query",
                "initial_value": query or "",
                "placeholder": {"type": "plain_text", "text": "キーワード（例：ごみ、Wi-Fi、宿泊 など）"},
            },
            "label": {"type": "plain_text", "text": "マニュアル検索"},
        }
    )
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "検索する"},
                    "action_id": "manuals_submit",
                    "style": "primary",
                    "value": "search",
                }
            ],
        }
    )

    # 検索結果
    if results:
        blocks.append({"type": "divider"})
        for idx, (title, _body) in enumerate(results[:40]):
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{title or '（無題）'}*"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "開く"},
                        "action_id": "manuals_open_item",
                        "value": f"{idx}|{query}",
                    },
                }
            )
    else:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "一致する項目がありませんでした。"}}
        )

    return {
        "type": "modal",
        "callback_id": "manuals_modal",
        "title": {"type": "plain_text", "text": "シェアハウスマニュアル"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": blocks,
    }


def _build_manual_detail_modal(title: str, body: str) -> Dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "manual_detail_modal",
        "title": {"type": "plain_text", "text": title[:24] or "詳細"},
        "close": {"type": "plain_text", "text": "戻る"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": body or ""}},
        ],
    }


def register_manuals(app: App):
    # Homeのボタン（action_id: "manuals_open"）で開く
    @app.action("manuals_open")
    def _open_from_home(ack, body, client: WebClient, logger):
        ack()
        try:
            client.views_open(trigger_id=body["trigger_id"], view=_build_manuals_modal())
        except Exception as e:
            logger.exception(e)

    # 互換: 既存の「マニュアルを見る」ボタン（action_id: "open_manuals"）にも対応
    @app.action("open_manuals")
    def _open_from_legacy(ack, body, client: WebClient, logger):
        ack()
        try:
            client.views_open(trigger_id=body["trigger_id"], view=_build_manuals_modal())
        except Exception as e:
            logger.exception(e)

    # グローバルショートカット
    @app.shortcut("open_manuals")
    def _open_from_shortcut(ack, body, client: WebClient, logger):
        ack()
        client.views_open(trigger_id=body["trigger_id"], view=_build_manuals_modal())

    # スラッシュコマンド /manuals
    @app.command("/manuals")
    def _open_from_command(ack, body, client: WebClient, logger):
        ack()
        client.views_open(trigger_id=body["trigger_id"], view=_build_manuals_modal())

    # 検索実行
    @app.action("manuals_submit")
    def _do_search(ack, body, client: WebClient, logger):
        ack()
        view_id = body["view"]["id"]
        state = body["view"]["state"]["values"]
        query = state["manuals_search"]["query"].get("value", "")
        client.views_update(view_id=view_id, view=_build_manuals_modal(query=query))

    # アイテムを開く
    @app.action("manuals_open_item")
    def _open_item(ack, body, client: WebClient, logger):
        ack()
        idx_str, query = (body["actions"][0]["value"] or "0|").split("|", 1)
        idx = int(idx_str or "0")
        results = search_manuals_by_keyword(query)
        if not results or idx >= len(results):
            return
        title, body_text = results[idx]
        client.views_push(trigger_id=body["trigger_id"], view=_build_manual_detail_modal(title, body_text))
