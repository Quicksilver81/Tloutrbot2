import os
import logging
from config import Config
import time
from pyrogram.raw.all import layer
import pyrogram
from pyrogram import Client, __version__

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

app = Bot()
app.run()
