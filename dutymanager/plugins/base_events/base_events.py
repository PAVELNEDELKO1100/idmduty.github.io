from module import Blueprint
from module import VKError, types
from module.utils import logger
from dutymanager.db.methods import AsyncDatabase
from dutymanager.units.vk_script import msg_send
from dutymanager.units.utils import *
from dutymanager.units.vk_script import get_chat, msg_edit
from dutymanager.units.const import errors
from tortoise.exceptions import BaseORMException

bot = Blueprint(name="Base")
db = AsyncDatabase.get_current()


@bot.error_handler(Exception)
async def error_handler(e: Exception):
    print(e.__class__.__name__)


@bot.event.print_bookmark()
async def print_bookmark(event: types.PrintBookmark):
    peer_id = db.chats(event.object.chat)
    local_id = event.object.conversation_message_id
    description = event.object.description
    try:
        await msg_send(
            peer_id,
            f"🔼 Перейти к закладке «{description}»",
            local_id
        )
    except (IndexError, VKError) as e:
        e = list(e.args)[0][0]
        await send_msg(peer_id, errors.get(e, "❗ Произошла неизвестная ошибка."))


@bot.event.ban_get_reason()
async def ban_get_reason(event: types.BanGetReason):
    peer_id = db.chats(event.object.chat)
    local_id = event.object.local_id
    try:
        await msg_send(peer_id, "🔼 Перейти к месту бана", local_id)
    except (IndexError, VKError) as e:
        e = list(e.args)[0][0]
        await send_msg(peer_id, errors.get(e, "❗ Произошла неизвестная ошибка."))


async def abstract_bind(
    uid: str, text: str, date: int, local_id: int
):
    if uid not in db.chats:
        chat_id, title = await get_chat(date, text)
        return await db.chats.create(uid, chat_id, title[:250])
    await msg_edit(
        db.chats(uid),
        f"✅ Беседа «{db.chats(uid, 'title')}» распознана!",
        local_id
    )


@bot.event.bind_chat()
async def bind_chat(event: types.BindChat):
    return await abstract_bind(
        event.object.chat,
        "!связать",
        event.message.date,
        event.message.conversation_message_id
    )


@bot.event.subscribe_signals()
async def subscribe_signals(event: types.SubscribeSignals):
    uid = event.object.chat
    try:
        await abstract_bind(
            uid,
            event.object.text,
            event.message.date,
            event.message.conversation_message_id
        )
        await db.chats.change(uid, is_duty=True)
    except (BaseORMException, Exception) as e:
        logger.error(e)
        return {"response": "error", **errors[10]}