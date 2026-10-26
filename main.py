import discord
from discord.ext import commands
import os, asyncio
from dotenv import load_dotenv
from aiohttp import web
from utils.database import init_db, get_prefix
from utils.embeds import error_embed

load_dotenv()

async def prefix_callable(bot, message):
    if not message.guild:
        return os.getenv("DEFAULT_PREFIX", "?")
    return await get_prefix(message.guild.id)

# ===== RENDER WEB SERVER - ISSE HI HEALTH CHECK PASS HOGA =====
async def handle(request):
    return web.Response(text="🦋 XENO Bot is Online - Enterprise Security Active")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    # Health check ke liye Render isi ko ping karega
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000)) # Render ka port
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Webserver running on port {port} for Render monitor")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix_callable, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🦋 {bot.user} online - {len(bot.guilds)} guilds")
    await init_db()
    try:
        await bot.tree.sync()
    except: pass
    print("Database + Slash synced")

async def load_cogs():
    for cog in ["cogs.antinuke", "cogs.moderation", "cogs.fun", "cogs.utility"]:
        try:
            await bot.load_extension(cog)
            print(f"Loaded {cog}")
        except Exception as e:
            print(f"Failed {cog}: {e}")

@bot.event
async def setup_hook():
    # Ye line sabse zaruri hai Render ke liye
    asyncio.create_task(start_webserver())
    await load_cogs()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=error_embed("Missing Permissions"))
    elif isinstance(error, commands.CommandNotFound):
        return

bot.run(os.getenv("BOT_TOKEN"))
