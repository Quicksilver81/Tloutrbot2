import datetime
import motor.motor_asyncio
from config import Config

import re
import logging

from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = AsyncIOMotorClient(Config.DATABASE_URL)
database = client[Config.SESSION_NAME]
instance = Instance.from_db(database)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = "Telegram_files"




async def save_file(media):
    """Save file in database"""

    file_id, file_ref = unpack_new_file_id(media.file_id)

    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=media.file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(media.file_name + " is already saved in database")
        else:
            logger.info(media.file_name + " is saved in database")


async def get_search_results(query, file_type=None, max_results=10, offset=0):
    """For given query return (results, next_offset)"""

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_\(\)\[\]]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], ''

    if 1 == 1:
        filter = {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ''

    cursor = Media.find(filter)

    # Sort by recent
    cursor.sort('$natural', -1)

    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)

    # Get list of files
    files = await cursor.to_list(length=max_results)

    return files, next_offset

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            upload_as_doc=False,
            thumbnail=None,
            notif=True,
            caption=False,
            generate_ss=False,
            generate_sample_video=False,
            blocked_exts=["webm", "3gp", "m4a", "mp4"],
        )

    async def add_user(self, id):
        user = self.new_user(id)
        await self.col.insert_one(user)

    async def add_user_pass(self, id, ag_pass):
        await self.add_user(int(id))
        await self.col.update_one({'id': int(id)}, {'$set': {'ag_p': ag_pass}})

    async def get_user_pass(self, id):
        user_pass = await self.col.find_one({'id': int(id)})
        return user_pass.get("ag_p", None) if user_pass else None

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return True if user else False

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': user_id})

    async def set_upload_as_doc(self, id, upload_as_doc):
        await self.col.update_one({'id': id}, {'$set': {'upload_as_doc': upload_as_doc}})

    async def get_upload_as_doc(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('upload_as_doc', False)

    async def set_aria2(self, id, aria2):
        await self.col.update_one({'id': id}, {'$set': {'aria2': aria2}})

    async def get_aria2(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('aria2', False)

    async def set_thumbnail(self, id, thumbnail):
        await self.col.update_one({'id': id}, {'$set': {'thumbnail': thumbnail}})

    async def get_thumbnail(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('thumbnail', None)

    async def set_caption(self, id, thumbnail):
        await self.col.update_one({'id': id}, {'$set': {'caption': thumbnail}})

    async def get_caption(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('caption', None)

    async def set_generate_ss(self, id, generate_ss):
        await self.col.update_one({'id': id}, {'$set': {'generate_ss': generate_ss}})

    async def get_generate_ss(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('generate_ss', False)

    async def set_generate_sample_video(self, id, generate_sample_video):
        await self.col.update_one({'id': id}, {'$set': {'generate_sample_video': generate_sample_video}})

    async def get_generate_sample_video(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('generate_sample_video', False)

    async def set_notif(self, id, notif):
        await self.col.update_one({"id": id}, {"$set": {"notif": notif}})

    async def get_notif(self, id):
        user = await self.col.find_one({"id": int(id)})
        return user.get("notif", False)

    async def get_all_notif_user(self):
        notif_users = self.col.find({"notif": True})
        return notif_users

    async def get_user_data(self, id) -> dict:
        user = await self.col.find_one({'id': int(id)})
        return user or None

    async def get_blocked_exts(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('blocked_exts', ["webm", "mhtml", "3gp", "m4a", "mp4"])

    async def set_blocked_exts(self, id, blocked_exts):
        await self.col.update_one({'id': id}, {'$set': {'blocked_exts': blocked_exts}})


db = Database(Config.DATABASE_URL, Config.SESSION_NAME) 
