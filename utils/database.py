import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "database.db")

# ===== ALL TABLES SCHEMA =====
TABLES = {
    "prefixes": """
        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id TEXT PRIMARY KEY,
            prefix TEXT NOT NULL
        )
    """,
    "whitelist": """
        CREATE TABLE IF NOT EXISTS whitelist (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            type TEXT DEFAULT 'user',
            PRIMARY KEY (guild_id, user_id)
        )
    """,
    "antinuke_config": """
        CREATE TABLE IF NOT EXISTS antinuke_config (
            guild_id TEXT PRIMARY KEY,
            anti_channel INTEGER DEFAULT 0,
            anti_role INTEGER DEFAULT 0,
            anti_ban INTEGER DEFAULT 0,
            anti_kick INTEGER DEFAULT 0,
            anti_bot INTEGER DEFAULT 0,
            anti_webhook INTEGER DEFAULT 0,
            log_channel TEXT
        )
    """,
    "warns": """
        CREATE TABLE IF NOT EXISTS warns (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            reason TEXT,
            time INTEGER
        )
    """,
    "automod_config": """
        CREATE TABLE IF NOT EXISTS automod_config (
            guild_id TEXT PRIMARY KEY,
            anti_invite INTEGER DEFAULT 1,
            anti_link INTEGER DEFAULT 0,
            anti_spam INTEGER DEFAULT 1,
            anti_massmention INTEGER DEFAULT 1,
            anti_emoji_spam INTEGER DEFAULT 0
        )
    """,
    "greet_config": """
        CREATE TABLE IF NOT EXISTS greet_config (
            guild_id TEXT PRIMARY KEY,
            welcome_channel TEXT,
            welcome_msg TEXT,
            welcome_embed TEXT DEFAULT '0',
            goodbye_channel TEXT,
            goodbye_msg TEXT,
            booster_channel TEXT,
            booster_msg TEXT
        )
    """,
    "autorespond": """
        CREATE TABLE IF NOT EXISTS autorespond (
            guild_id TEXT NOT NULL,
            trigger TEXT NOT NULL,
            response TEXT NOT NULL,
            PRIMARY KEY (guild_id, trigger)
        )
    """,
    "afk": """
        CREATE TABLE IF NOT EXISTS afk (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            reason TEXT,
            time INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
    """,
    "autorole": """
        CREATE TABLE IF NOT EXISTS autorole (
            guild_id TEXT PRIMARY KEY,
            role_id TEXT
        )
    """,
    "logging": """
        CREATE TABLE IF NOT EXISTS logging (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT
        )
    """
}

async def init_db():
    """Initialize all tables + auto migration"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Create all tables
        for table_name, query in TABLES.items():
            await db.execute(query)

        # 2. Auto Migration - Agar purana DB hai toh columns add kar de
        migrations = [
            ("greet_config", "welcome_embed", "TEXT DEFAULT '0'"),
            ("automod_config", "anti_emoji_spam", "INTEGER DEFAULT 0"),
            ("antinuke_config", "log_channel", "TEXT"),
        ]
        for table, column, col_type in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except aiosqlite.OperationalError:
                pass  # Column already exists

        await db.commit()
    
    print(f"✅ Database Loaded | Path: {DB_PATH} | Tables: {len(TABLES)}")
    print("🛡️  AntiNuke System: OFF by default (Enable with ?antinuke enable)")

# ================= PREFIX SYSTEM =================
async def get_prefix(guild_id: int):
    """Guild ka prefix lao, nahi toh default ?"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (str(guild_id),)) as cur:
                row = await cur.fetchone()
                if row and row[0]:
                    return row[0]
    except:
        pass
    return os.getenv("DEFAULT_PREFIX", "?")

async def set_prefix_db(guild_id: int, prefix: str):
    """Prefix set karo"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO prefixes (guild_id, prefix) VALUES (?,?)", (str(guild_id), prefix))
        await db.commit()

# ================= WHITELIST SYSTEM =================
async def is_whitelisted(guild_id: int, user_id: int) -> bool:
    """Check if user is whitelisted (AutoMod bypass)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id))) as cur:
            return await cur.fetchone() is not None

async def add_whitelist(guild_id: int, user_id: int, type: str = "user"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO whitelist (guild_id, user_id, type) VALUES (?,?,?)", (str(guild_id), str(user_id), type))
        await db.commit()
        return True

async def remove_whitelist(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id)))
        await db.commit()
        return True

async def get_whitelisted(guild_id: int):
    """Saare whitelisted users lao"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, type FROM whitelist WHERE guild_id=?", (str(guild_id),)) as cur:
            rows = await cur.fetchall()
            return rows  # [(user_id, type), ...]

async def clear_whitelist(guild_id: int):
    """Pura whitelist clear"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelist WHERE guild_id=?", (str(guild_id),))
        await db.commit()
