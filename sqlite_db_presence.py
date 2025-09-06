import datetime
import logging
import os
import sys
from dotenv import load_dotenv
from peewee import Model, CharField, TextField, DateTimeField, DateField, IntegerField, ForeignKeyField, Check
from playhouse.db_url import connect

# .envの読み込み
load_dotenv(override=True)

# 実行したSQLをログで出力する設定
logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

# データベースへの接続設定
DATABASE_URL = os.getenv("DATABASE", "sqlite:///peewee_db_presence.sqlite")
db = connect(DATABASE_URL)  # 環境変数に合わせて変更する場合


# BaseModel（全モデルの共通: database を束ねる）
class BaseModel(Model):
    class Meta:
        database = db


# Slackのユーザーのアクション
class User(BaseModel):
    slack_user_id = CharField(unique=True)  # 例: "U0123456"
    name = CharField(null=True)
    room_no = CharField(null=True)
    role = CharField(default="member")  # "member" / "admin"
    created_at = DateTimeField(default=datetime.datetime.utcnow)  # ()は付けない

    class Meta:
        table_name = "users"


# presence_logs（在宅状況：1ユーザー×1日×1レコード想定）
class PresenceLog(BaseModel):
    # 外部キーを user の slack_user_id に合わせる設計（通常のFKは id に張る）
    user = ForeignKeyField(User, to_field="slack_user_id", backref="presence_logs", on_delete="CASCADE")
    date = DateField()  # 例: 2025-09-01（Asia/Tokyoで切る想定）
    status = CharField(constraints=[Check("status IN ('home','away')")])
    note = TextField(null=True)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = "presence_logs"
        # (user, date) をユニークに（UPSERT前提）
        indexes = ((("user", "date"), True),)


# events（共有予定：時間はDBではUTC保存）
class Event(BaseModel):
    title = CharField()
    start_at = DateTimeField()  # UTCで保存
    end_at = DateTimeField()  # UTCで保存
    created_by = ForeignKeyField(
        User, to_field="slack_user_id", backref="events", on_delete="SET NULL", null=True
    )
    location = CharField(null=True)
    memo = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = "events"
        indexes = ((("start_at",), False),)  # 検索用に時刻へインデックス


# cleaning_logs（掃除の記録）
class CleaningLog(BaseModel):
    # PresenceLog と同じ方針で、User の主キーではなく slack_user_id に外部キーを張る
    user = ForeignKeyField(
        User,
        to_field="slack_user_id",
        backref="cleaning_logs",
        on_delete="CASCADE",
        column_name="user_id"
    )

    location = CharField()  # 掃除箇所
    note = TextField(null=True)  # 任意メモ
    timestamp = DateTimeField(default=datetime.datetime.utcnow)  # 生成時刻（UTC naive）

    class Meta:
        table_name = "cleaning_logs"
        indexes = (
            (("timestamp",), False),
            (("location",), False),
        )


def init_db():
    db.connect(reuse_if_open=True)
    # SQLiteの外部キーを有効化（念のため）
    try:
        db.execute_sql("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
    db.create_tables([User, PresenceLog, Event, CleaningLog])
