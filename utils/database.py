import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Prefix
        await db.execute("""
        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id TEXT PRIMARY KEY,
            prefix TEXT
        )""")

        # 2. Whitelist
        await db.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            guild_id TEXT,
            user_id TEXT,
            type TEXT,
            PRIMARY KEY (guild_id, user_id)
        )""")

        # 3. Antinuke Config
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

        # 4. Warns
        await db.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            time INTEGER
        )""")

        # 5. AutoMod Config - NEW
        await db.execute("""
        CREATE TABLE IF NOT EXISTS automod_config (
            guild_id TEXT PRIMARY KEY,
            anti_invite INTEGER DEFAULT 1,
            anti_link INTEGER DEFAULT 0,
            anti_spam INTEGER DEFAULT 1,
            anti_massmention INTEGER DEFAULT 1
        )""")

        # 6. Greet Config (Welcome/Goodbye/Booster) - NEW
        await db.execute("""
        CREATE TABLE IF NOT EXISTS greet_config (
            guild_id TEXT PRIMARY KEY,
            welcome_channel TEXT,
            welcome_msg TEXT,
            goodbye_channel TEXT,
            goodbye_msg TEXT,
            booster_channel TEXT,
            booster_msg TEXT
        )""")

        # 7. Auto Respond - NEW
        await db.execute("""
        CREATE TABLE IF NOT EXISTS autorespond (
            guild_id TEXT,
            trigger TEXT,
            response TEXT
        )""")

        # 8. AFK System - NEW
        await db.execute("""
        CREATE TABLE IF NOT EXISTS afk (
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            time INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )""")

        # 9. Autorole - EXTRA
        await db.execute("""
        CREATE TABLE IF NOT EXISTS autorole (
            guild_id TEXT PRIMARY KEY,
            role_id TEXT
        )""")

        await db.commit()
        print("✅ Database initialized with all tables")

# ===== PREFIX FUNCTIONS =====
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

# ===== WHITELIST FUNCTIONS =====
async def is_whitelisted(guild_id: int, user_id: int):
    # Bot owner check (optional)
    if guild_id == user_id: 
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id))) as cur:
            return await cur.fetchone() is not None

async def add_whitelist(guild_id: int, user_id: int, type: str = "user"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO whitelist VALUES (?,?,?)", (str(guild_id), str(user_id), type))
        await db.commit()

async def remove_whitelist(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id)))
        await db.commit()

async def get_whitelisted(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM whitelist WHERE guild_id=?", (str(guild_id),)) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]
