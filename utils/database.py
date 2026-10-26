import aiosqlite, os
from dotenv import load_dotenv
load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id TEXT PRIMARY KEY,
            prefix TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            guild_id TEXT,
            user_id TEXT,
            type TEXT,
            PRIMARY KEY (guild_id, user_id)
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS antinuke_config (
            guild_id TEXT PRIMARY KEY,
            anti_channel INTEGER DEFAULT 1,
            anti_role INTEGER DEFAULT 1,
            anti_ban INTEGER DEFAULT 1,
            anti_kick INTEGER DEFAULT 1,
            anti_bot INTEGER DEFAULT 1,
            anti_webhook INTEGER DEFAULT 1,
            log_channel TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            time INTEGER
        )""")
        await db.commit()

async def get_prefix(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (str(guild_id),)) as cur:
            row = await cur.fetchone()
            if row:
                return row[0]
    return os.getenv("DEFAULT_PREFIX", "?")

async def set_prefix_db(guild_id: int, prefix: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO prefixes VALUES (?,?)", (str(guild_id), prefix))
        await db.commit()

async def is_whitelisted(guild_id: int, user_id: int):
    if guild_id == user_id: return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id))) as cur:
            return await cur.fetchone() is not None