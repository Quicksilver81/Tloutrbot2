import os
import re
import io
import pyrogram
import logging
from functions.forcesub import handle_force_subscribe
import logging
from urllib.parse import quote
import asyncio 
from pyrogram import Client, emoji, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument
from config import Config, temp
from database.database import get_search_results
CACHE_TIME = 300
cache_time = 0 if Config.OWNER_ID or Config.AUTH_CHANNEL else CACHE_TIME
logger = logging.getLogger(__name__)
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from database.filters_helper import(
   add_filter,
   find_filter,
   get_filters,
   delete_filter,
   count_filters, 
   del_all
)
from database.database import db
from pyrogram.enums import ParseMode
from functions.tools import add_user, all_users
from functions.tools import unicode_tr
from functions.tools import parser, split_quotes
work_loads = {}

import re
import time
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine

import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from database.database import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)
LOGGER = logging.getLogger(__name__)

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user),
                               f'Your Submission for indexing {chat} has been decliened by our moderators.',
                               reply_to_message_id=int(lst_msg_id))
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) == Config.OWNER_ID:
        await bot.send_message(int(from_user),
                               f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
                               reply_to_message_id=int(lst_msg_id))
    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text ) & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if message.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.username == Config.OWNER_ID:
        buttons = [
            [
                InlineKeyboardButton('Yes',
                                     callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.username}')
            ],
            [
                InlineKeyboardButton('close', callback_data='close_data'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup)

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [
        [
            InlineKeyboardButton('Accept Index',
                                 callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('Reject Index',
                                 callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(Config.OWNER_ID,
                           f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
                           reply_markup=reply_markup)
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')

async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>")
                    break
                current += 1
                if current % 20 == 0:
                    can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                    reply = InlineKeyboardMarkup(can)
                    await msg.edit_text(
                        text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>",
                        reply_markup=reply)
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.file_type = message.media.value
                media.caption = message.caption
                aynav, vnay = await save_file(media)
                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1
        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')



@Client.on_message(filters.command('log') & filters.user(Config.OWNERS))
async def log_handler(client, message):
    with open('log.txt', 'rb') as f:
        try:
            await client.send_document(document=f,
                                  file_name=f.name, reply_to_message_id=message.id,
                                  chat_id=message.chat.id, caption=f.name)
        except Exception as e:
            await message.reply_text(str(e))

@Client.on_message(filters.command('users') & filters.user(Config.OWNERS))
async def list_users(bot, message):
    # https://t.me/GetTGLink/4184
    total_users = await db.total_users_count()
    raju = await message.reply('Kullanıcıların Listesi Getiriliyor')
    users = await db.get_all_users()
    out = "Users Saved In DB Are:\n\n"
    async for user in users:
        out += f"tg://user?id={user['id']}\n"
    try:
        with open('users.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('users.txt', caption="Bot Kullanıcıları")
        await raju.edit_text(f"Başarıyla Tamamlandı Toplam Kullanıcı Sayısı= {total_users}")
    except Exception as e:
        raju.edit_text(e)

@Client.on_message(filters.command('add') & filters.user(Config.OWNERS))
async def addfilter(client, message):
      
    userid = message.from_user.id
    chat_type = message.chat.type
    args = message.text.html.split(None, 1)
    grp_id = Config.BOT_USERNAME
    chat = await client.get_users(grp_id)
    title = chat.first_name
        

    
    if len(args) < 2:
        await message.reply_text("Komut Eksik :(", quote=True)
        return 
    extracted = split_quotes(args[1])
    text = unicode_tr(extracted[0]).lower()

    if not message.reply_to_message and len(extracted) < 2:
        return await message.reply_text("Add some content to save your filter!", quote=True)

    if (len(extracted) >= 2) and not message.reply_to_message:
        reply_text, btn, alert = parser(extracted[1], text)
        fileid = None
        if not reply_text:
            return await message.reply_text("Butonları yazısız mı yaratayım? Yazı ver onlara çabuk.", quote=True)

    elif message.reply_to_message and message.reply_to_message.reply_markup:
        try:
            rm = message.reply_to_message.reply_markup
            btn = rm.inline_keyboard
            msg = get_file_id(message.reply_to_message)
            if msg:
                fileid = msg.file_id
                reply_text = message.reply_to_message.caption.html
            else:
                reply_text = message.reply_to_message.text.html
                fileid = None
            alert = None
        except Exception:
            reply_text = ""
            btn = "[]"
            fileid = None
            alert = None

    elif message.reply_to_message and message.reply_to_message.media:
        try:
            msg = get_file_id(message.reply_to_message)
            fileid = msg.file_id if msg else None
            reply_text, btn, alert = parser(message.reply_to_message.caption.html, text)
        except Exception:
            reply_text = ""
            btn = "[]"
            alert = None
    elif message.reply_to_message and message.reply_to_message.text:
        try:
            fileid = None
            reply_text, btn, alert = parser(message.reply_to_message.text.html, text)
        except Exception:
            reply_text = ""
            btn = "[]"
            alert = None
    else: return

    await add_filter(grp_id, text, reply_text, btn, fileid, alert)    

    await message.reply_text(
        f"Filtre  `{text}` için  **{title}** botuna eklendi!",
        quote=True,
        parse_mode=ParseMode.MARKDOWN
    )


@Client.on_message(filters.command('viewfilters') & filters.user(Config.OWNERS))
async def get_all(client, message):
    
    chat_type = message.chat.type
    userid = message.from_user.id
    grp_id = Config.BOT_USERNAME
    chat = await client.get_users(grp_id)
    title = chat.first_name

    texts = await get_filters(grp_id)
    count = await count_filters(grp_id)

    if count:
        filterlist = f"**{title}** için tüm filterlar: {count}\n\n"

        for text in texts:
            keywords = " ×  `{}`\n".format(text)
            
            filterlist += keywords

        if len(filterlist) > 4096:
            with io.BytesIO(str.encode(filterlist.replace("`", ""))) as keyword_file:
                keyword_file.name = "keywords.txt"
                await message.reply_document(
                    document=keyword_file,
                    quote=True
                )
            return
    else:
        filterlist = "**{title}** için hiç filter yok!"
    await message.reply_text(
        text=filterlist,
        quote=True,
        parse_mode=ParseMode.MARKDOWN
    )
        
@Client.on_message(filters.command('del') & filters.user(Config.OWNERS))
async def deletefilter(client, message):
    userid = message.from_user.id
    chat_type = message.chat.type

    grp_id = Config.BOT_USERNAME
    chat = await client.get_users(grp_id)
    title = chat.first_name

    try:
        cmd, text = message.text.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Silmek istediğiniz filtre adını belirtin!</i>\n\n"
            "<code>/del filterismi</code>\n\n"
            "Tüm filterları görmek için /viewfilters ı kulan!",
            quote=True
        )
        return

    query = text.lower()

    await delete_filter(message, query, grp_id)
        

@Client.on_message(filters.command('delall') & filters.user(Config.OWNERS))
async def delallconfirm(client, message):
    userid = message.from_user.id
    chat_type = message.chat.type
    group_id = Config.BOT_USERNAME
    chat = await client.get_users(group_id)
    title = chat.first_name
    await del_all(client, message, group_id, title)

@Client.on_message(filters.private & filters.text)
async def give_filter(client,message):
    if Config.AUTH_CHANNEL:
        fsub = await handle_force_subscribe(client, message)
        if fsub == 400:
            return
    group_id = Config.BOT_USERNAME
    name = message.text

    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await message.reply_text(reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await message.reply_text(
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button)
                            )
                    else:
                        if btn == "[]":
                            await message.reply_cached_media(
                                fileid,
                                caption=reply_text or ""
                            )
                        else:
                            button = eval(btn) 
                            await message.reply_cached_media(
                                fileid,
                                caption=reply_text or "",
                                reply_markup=InlineKeyboardMarkup(button)
                            )
                except Exception as e:
                    print(e)
                    pass
                break 
                
    if Config.SAVE_USER == "yes":
        try:
            await add_user(
                str(message.from_user.id),
                str(message.from_user.username),
                str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
                str(message.from_user.dc_id)
            )
        except:
            pass

@Client.on_inline_query(filters.user(Config.OWNER_ID) if Config.OWNER_ID else None)
async def answer(bot, query):
    """Show search results for given inline query"""

    if Config.AUTH_CHANNEL and not await is_subscribed(bot, query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='You have to subscribe channel',
            switch_pm_parameter="subscribe",
        )
        return

    results = []
    if '|' in query.query:
        text, file_type = query.query.split('|', maxsplit=1)
        text = text.strip()
        file_type = file_type.strip().lower()
    else:
        text = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)
    reply_markup = get_reply_markup(bot.username, query=text)
    files, next_offset = await get_search_results(text, file_type=file_type, max_results=10, offset=offset)

    for file in files:
        results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=file.caption or "",
                description=f'Size: {size_formatter(file.file_size)}\nType: {file.file_type}',
                reply_markup=reply_markup
            )
        )

    if results:
        switch_pm_text = f"{emoji.FILE_FOLDER} Results"
        if text:
            switch_pm_text += f" for {text}"

        await query.answer(
            results=results,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start",
            next_offset=str(next_offset)
        )
    else:

        switch_pm_text = f'Sonuç Yok..'
        if text:
            switch_pm_text += f' for "{text}"'

        await query.answer(
            results=[],
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="okay",
        )


def get_reply_markup(username, query):
    buttons = [
        [
            InlineKeyboardButton('Search again', switch_inline_query_current_chat=query)
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def size_formatter(size):
    """Dosya Boyutu Getirici..."""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


async def is_subscribed(bot, query):
    try:
        user = await bot.get_chat_member(Config.AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        if not user.status == 'kicked':
            return True

    return False
