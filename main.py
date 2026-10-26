import discord
from discord.ext import commands
import os, asyncio, traceback
from dotenv import load_dotenv
from aiohttp import web
from utils.database import init_db, get_prefix

load_dotenv()

async def prefix_callable(bot, message):
    if not message.guild:
        return os.getenv("DEFAULT_PREFIX", "?")
    try:
        return await get_prefix(message.guild.id)
    except:
        return os.getenv("DEFAULT_PREFIX", "?")

async def handle(request):
    return web.Response(text="🦋 XENO Online - Security Active")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Webserver running on {port}")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix_callable, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🦋 {bot.user} | Guilds: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash synced: {len(synced)}")
    except Exception as e:
        print(f"Slash sync failed: {e}")

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: cogs.{filename[:-3]}")
            except Exception as e:
                print(f"❌ Failed cogs.{filename[:-3]}: {e}")
                traceback.print_exception(type(e), e, e.__traceback__)

async def main():
    async with bot:
        # SABSE IMPORTANT - Pehle DB banao
        print("🗃️ Initializing Database...")
        await init_db()
        print("✅ Database Ready - All tables created")
        
        await load_cogs()
        asyncio.create_task(start_webserver())
        
        token = os.getenv("BOT_TOKEN")
        if not token:
            print("❌ BOT_TOKEN missing!")
            return
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
