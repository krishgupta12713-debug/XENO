import discord
from discord.ext import commands
import os, asyncio, traceback
from dotenv import load_dotenv
from aiohttp import web
from utils.database import init_db, get_prefix
from utils.embeds import perm_error_embed, error_embed

load_dotenv()

async def prefix_callable(bot, message):
    if not message.guild:
        return os.getenv("DEFAULT_PREFIX", "?")
    return await get_prefix(message.guild.id)

async def handle(request):
    return web.Response(text="🦋 Dhadkhan Online - Security Active")

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

# ===== STATUS TASK =====
async def status_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers | ?help"))
            await asyncio.sleep(60)
            await bot.change_presence(activity=discord.Game(name="Dhadkhan Security • ?antinuke"))
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(10)

@bot.event
async def on_ready():
    print(f"🦋 {bot.user} | Guilds: {len(bot.guilds)}")
    await init_db()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Slash sync fail: {e}")
    print("✅ DB + SLASH DONE")

async def load_cogs():
    count = 0
    for root, dirs, files in os.walk("./cogs"):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                cog = os.path.join(root, f)[2:-3].replace(os.sep, ".").replace("/", ".")
                try:
                    await bot.load_extension(cog)
                    print(f"✅ Loaded: {cog}")
                    count += 1
                except Exception as e:
                    print(f"❌ FAIL {cog}: {e}")
                    traceback.print_exc()
    print(f"--- Total {count} cogs loaded ---")

@bot.event
async def setup_hook():
    asyncio.create_task(start_webserver())
    await load_cogs()
    bot.loop.create_task(status_task())

# ===== ERROR HANDLER =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, (commands.CheckFailure, commands.MissingPermissions)):
        try:
            await ctx.send(embed=perm_error_embed(), delete_after=6)
        except: pass
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=error_embed(f"Missing: `{error.param.name}`\nUse `?help {ctx.command}`"), delete_after=8)
        return
    print(f"Error in {ctx.command}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

@bot.event
async def on_message(message):
    if message.author.bot: return
    await bot.process_commands(message)

bot.run(os.getenv("BOT_TOKEN"))
