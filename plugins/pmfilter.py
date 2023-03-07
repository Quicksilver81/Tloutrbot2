import os
import re
import io
import pyrogram
import logging
from functions.forcesub import handle_force_subscribe

from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from config import Config
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

import re
import time
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine


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
                            await client.copy_message(
                                chat_id=message.chat.id,
                                from_chat_id=Config.KANAL,
                                message_id=int(reply_text))
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
