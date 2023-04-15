import logging
from urllib.parse import quote
from pyrogram import Client, emoji, filters
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import CallbackQuery, Message
from database.inlineyardimcisi import get_search_results, unpack_new_file_id
from utils import is_subscribed, get_size
from config import Config
from pyrogram.enums import ParseMode, ChatType, MessageMediaType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument
from database.inlineyardimcisi import Media
logger = logging.getLogger(__name__)
cache_time = 0 if Config.OWNER_ID or Config.AUTH_CHANNEL else Config.CACHE_TIME

async def delete_all_files(message: Message):
    try:
        await Media.collection.drop()
        await message.edit_text(f"Tüm dosyalar silindi.\n\nŞimdi mutlu musun?")
    except Exception as e:
        await message.edit_text(message.from_user.id, e)


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
        f_caption = f"{file.caption}\n\nOwner of This Magic: @MarvelTrRobot"
        if not f_caption: f_caption = str(file.file_name)
        
        altmetin = f'Boyut: {get_size(file.file_size)}, Tür: {file.file_type}'
        inlinecaption = file.caption
        
        results.append(
            InlineQueryResultCachedDocument(
                title=file.caption,
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


@Client.on_message(filters.command('deleteinline') & filters.user(Config.OWNER_ID))
async def inlinedosyasil(bot, message):
    tayp = 'Dosyalar'
    await message.reply_text(
        f'Tüm {tayp.lower()} silinecek.\nDevam etmek istiyor musunuz?',
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text=f"Tüm {tayp}ı Sil", callback_data=f"delete#{tayp}")]
            ]
        ),
        quote=True,
    )

@Client.on_callback_query(filters.regex(r'^delete+.*$'))
async def delete_all_confirm(bot, query:CallbackQuery):
    nesilincek = query.data.split("#")[1]
    if nesilincek == 'Dosyalar':
        await delete_all_files(query.message)
    else:
        return query.message.edit(f'deleteall yaparken sorun çıktı ?')
    
@Client.on_message(~filters.channel & filters.command('sil') & filters.user(Config.OWNER_ID))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if not (reply and reply.media):
        return await message.reply_text('Silmek istediğiniz dosyayı /sil ile yanıtlayın', quote=True)
    msg = await message.reply_text("İşleniyor...⏳", quote=True)
    for file_type in (MessageMediaType.DOCUMENT, MessageMediaType.VIDEO, MessageMediaType.AUDIO):
        media = getattr(reply, file_type.value, None)
        if media is not None:
            break
    else:
        return await msg.edit('Bu desteklenen bir dosya biçimi değil.')

    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('Dosya veritabanından başarıyla silindi.')
    else:
        # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39
        # have original file name.
        result = await Media.collection.delete_one({
            'file_name': media.file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
        })
        if result.deleted_count:
            await msg.edit('Dosya veritabanından başarıyla silindi.')
        else:
            await msg.edit('Veritabanında dosya bulunamadı.')
