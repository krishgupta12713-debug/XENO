import discord
from discord.ext import commands
import re, asyncio
from collections import defaultdict, deque
import time
from utils.embeds import base_embed, error_embed, success_embed
import aiosqlite, os

# Spam tracker
spam_tracker = defaultdict(lambda: deque(maxlen=10))

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/\w+")
        self.links = re.compile(r"https?://\S+")
        self.emoji_spam = re.compile(r"(<a?:\w+:\d+>|\p{Emoji}){10,}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        if message.author.guild_permissions.administrator: return

        guild_id = str(message.guild.id)
        content = message.content

        # DB se config lo
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT anti_invite, anti_link, anti_spam, anti_massmention FROM automod_config WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
                if not row: 
                    # default on
                    anti_invite, anti_link, anti_spam, anti_massmention = 1,0,1,1
                else:
                    anti_invite, anti_link, anti_spam, anti_massmention = row

        # 1. ANTI INVITE
        if anti_invite and self.invites.search(content):
            try:
                await message.delete()
                await message.channel.send(embed=error_embed(f"{message.author.mention} No invites allowed!"), delete_after=5)
                return
            except: pass

        # 2. ANTI LINK
        if anti_link and self.links.search(content):
            try:
                await message.delete()
                await message.channel.send(embed=error_embed(f"{message.author.mention} No links allowed!"), delete_after=5)
                return
            except: pass

        # 3. ANTI SPAM (5 msg in 3 sec)
        if anti_spam:
            now = time.time()
            tracker = spam_tracker[message.author.id]
            tracker.append(now)
            # last 5 msg in 4 sec
            if len(tracker) >= 5 and (now - tracker[0]) < 4:
                try:
                    await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=5), reason="AutoMod: Spam")
                    await message.channel.send(embed=base_embed("AutoMod", f"{message.author.mention} muted for 5m - Spamming"), delete_after=10)
                    tracker.clear()
                except: pass

        # 4. ANTI MASS MENTION (5+ mentions)
        if anti_massmention and len(message.mentions) >= 5:
            try:
                await message.delete()
                await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10), reason="AutoMod: Mass Mention")
            except: pass

    # ===== AUTOMOD COMMANDS =====
    @commands.hybrid_group(name="automod", description="AutoMod settings")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx): pass

    @automod.command(name="antilink", description="Toggle anti-link")
    async def antilink(self, ctx, mode: str = None):
        await self.toggle_config(ctx, "anti_link", mode)

    @automod.command(name="antiinvite", description="Toggle anti-invite")
    async def antiinvite(self, ctx, mode: str = None):
        await self.toggle_config(ctx, "anti_invite", mode)

    @automod.command(name="antispam", description="Toggle anti-spam")
    async def antispam(self, ctx, mode: str = None):
        await self.toggle_config(ctx, "anti_spam", mode)

    @automod.command(name="antimassmention", description="Toggle anti-mass-mention")
    async def antimassmention(self, ctx, mode: str = None):
        await self.toggle_config(ctx, "anti_massmention", mode)

    async def toggle_config(self, ctx, key, mode):
        guild_id = str(ctx.guild.id)
        val = 1 if (mode and mode.lower() in ["on","enable","yes"]) else 0
        if mode is None:
            # toggle
            async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
                await db.execute(f"INSERT OR IGNORE INTO automod_config (guild_id) VALUES (?)", (guild_id,))
                async with db.execute(f"SELECT {key} FROM automod_config WHERE guild_id=?", (guild_id,)) as cur:
                    row = await cur.fetchone()
                    val = 0 if row and row[0]==1 else 1
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute(f"INSERT OR IGNORE INTO automod_config (guild_id) VALUES (?)", (guild_id,))
            await db.execute(f"UPDATE automod_config SET {key}=? WHERE guild_id=?", (val, guild_id))
            await db.commit()
        status = "Enabled ✅" if val==1 else "Disabled ❌"
        await ctx.send(embed=success_embed(f"{key.replace('_',' ').title()} {status}"))

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
