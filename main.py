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
    return await get_prefix(message.guild.id)

async def handle(request):
    return web.Response(text="🦋 XENO Online")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Webserver {port}")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix_callable, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🦋 {bot.user} | Guilds: {len(bot.guilds)}")
    await init_db()
    await bot.tree.sync()
    print("✅ SLASH + DB DONE - All commands loaded")

async def load_cogs():
    count = 0
    # SIRF cogs folder ko scan karega
    for root, dirs, files in os.walk("./cogs"):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                # ./cogs/fun/rps.py -> cogs.fun.rps
                cog = os.path.join(root, f)[2:-3].replace(os.sep, ".").replace("/", ".")
                try:
                    await bot.load_extension(cog)
                    print(f"✅ Loaded Category: {cog}")
                    count += 1
                except Exception as e:
                    print(f"❌ FAIL {cog}: {e}")
                    traceback.print_exc()
    print(f"--- Total {count} cogs loaded ---")

@bot.event
async def setup_hook():
    asyncio.create_task(start_webserver())
    await load_cogs()

bot.run(os.getenv("BOT_TOKEN"))
