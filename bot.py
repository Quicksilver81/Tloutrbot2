import os
import logging
from config import Config
import time
from pyrogram.raw.all import layer
import pyrogram
from pyrogram import Client, __version__
from typing import Union, Optional, AsyncGenerator

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
LOGGER = logging.getLogger(__name__)

plugins = dict(root='plugins')

class Bot(Client):

    def __init__(self):
        super().__init__(
            name='TlouBot2',
            api_id=Config.APP_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=343,
            plugins=plugins,
            sleep_threshold=5,
        )

    async def start(self):
        await super().start()
        owner = await self.get_chat(Config.OWNER_ID)
        print(owner)
        me = await self.get_me()
        self.username = '@' + me.username
        LOGGER.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}. Premium.")
        if Config.OWNER_ID != 0:
            try:
                await self.send_message(text="Karanlığın küllerinden yeniden doğdum.",
                    chat_id=Config.OWNER_ID)
            except Exception as t:
                LOGGER.error(str(t))

    async def stop(self, *args):
        if Config.OWNER_ID != 0:
            texto = f"Son nefesimi verdim."
            try:
                await self.send_document(document='log.txt', caption=texto, chat_id=Config.OWNER_ID)
            except Exception as t:
                LOGGER.warning(str(t))
        await super().stop()
        LOGGER.info(msg="App Stopped.")
        exit()
        async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()
