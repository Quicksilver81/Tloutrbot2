import pyrogram
import logging
from pyrogram import Client, filters
from config import Config
logger = logging.getLogger(__name__)

@Client.on_message(filters.command('log') & filters.user(Config.OWNERS))
async def log_handler(client, message):
    with open('log.txt', 'rb') as f:
        try:
            await client.send_document(document=f,
                                  file_name=f.name, reply_to_message_id=message.id,
                                  chat_id=message.chat.id, caption=f.name)
        except Exception as e:
            await message.reply_text(str(e))
