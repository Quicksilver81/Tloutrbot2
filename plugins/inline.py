import logging
from urllib.parse import quote
from pyrogram import Client, emoji, filters
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import CallbackQuery
from database.inlineyardimcisi import get_search_results
from utils import is_subscribed, get_size
from config import Config
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument

logger = logging.getLogger(__name__)
cache_time = 0 if Config.OWNER_ID or Config.AUTH_CHANNEL else Config.CACHE_TIME


def get_reply_markup(username, query):
    buttons = [[
        InlineKeyboardButton('Tekrar Ara', switch_inline_query_current_chat=query)
        ]]
    return InlineKeyboardMarkup(buttons)


@Client.on_inline_query(filters.user(Config.OWNER_ID) if Config.OWNER_ID else None)
async def answer(bot:Client, query:CallbackQuery):
    # kanala katıldı mı?
    if Config.AUTH_CHANNEL and not await is_subscribed(bot, query):
        if Config.JOIN_CHANNEL_WARNING:
            await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text='Botu kullanmak için kanalıma abone olmalısınız.',
                           switch_pm_parameter="subscribe")
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
    files, next_offset, total = await get_search_results(text,
                                                         file_type=file_type,
                                                         max_results=Config.BUTTON_COUNT,
                                                         offset=offset)

    for file in files:
        f_caption = file.caption
        if not f_caption: f_caption = str(file.file_name)
        
        altmetin = f'Boyut: {get_size(file.file_size)}, Tür: {file.file_type}'
        inlinecaption = file.caption
        
        results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=f_caption,
                description=altmetin,
                reply_markup=reply_markup))

    if results:
        switch_pm_text = f"{total} Sonuç Bulundu"
        if text:
            switch_pm_text += f": {text}"
        try:
            await query.answer(results=results,
                               is_personal=True,
                               cache_time=cache_time,
                               switch_pm_text=switch_pm_text,
                               switch_pm_parameter="start",
                               next_offset=str(next_offset))
        except QueryIdInvalid:
            pass
        except Exception as e:
            logging.exception(str(e))
            await query.answer(results=[], is_personal=True,
                               cache_time=cache_time,
                               switch_pm_text=str(e)[:63],
                               switch_pm_parameter="error")
    else:
        switch_pm_text = f'Sonuç yok'
        if text:
            switch_pm_text += f': "{text}"'

        await query.answer(results=[],
                           is_personal=True,
                           cache_time=cache_time,
                           switch_pm_text=switch_pm_text,
                           switch_pm_parameter="okay")
