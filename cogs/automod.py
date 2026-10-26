import discord
from discord.ext import commands
import re, time, os, aiosqlite
from collections import defaultdict, deque
from utils.embeds import base_embed, error_embed, success_embed
from utils.security_checks import mod_only, is_automod_bypass
from typing import Literal

spam_tracker = defaultdict(lambda: deque(maxlen=10))
last_msg = {}

def parse_duration(text: str) -> int:
    if not text: return 5
    text = text.lower().strip()
    try:
        if text[-1] == 's': return max(1, int(text[:-1]) // 60 or 1)
        if text[-1] == 'm': return int(text[:-1])
        if text[-1] == 'h': return int(text[:-1]) * 60
        if text[-1] == 'd': return int(text[:-1]) * 1440
        return int(text)
    except:
        return 5

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/\w+", re.I)
        self.links = re.compile(r"https?://\S+", re.I)
        self.emoji_regex = re.compile(r"<a?:\w+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+")

    async def get_config(self, guild_id):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS automod_config (
                guild_id TEXT PRIMARY KEY,
                anti_invite INTEGER DEFAULT 1, anti_link INTEGER DEFAULT 0,
                anti_spam INTEGER DEFAULT 1, anti_massmention INTEGER DEFAULT 1,
                anti_badwords INTEGER DEFAULT 1, anti_caps INTEGER DEFAULT 0,
                anti_emoji INTEGER DEFAULT 0, anti_zalgo INTEGER DEFAULT 0,
                anti_sticker INTEGER DEFAULT 1, anti_duplicate INTEGER DEFAULT 0,
                anti_mention_spam INTEGER DEFAULT 1, 
                punishment TEXT DEFAULT 'delete',
                punishment_duration INTEGER DEFAULT 5,
                log_channel TEXT, anti_emoji_spam INTEGER DEFAULT 0)""")
            await db.execute("INSERT OR IGNORE INTO automod_config (guild_id) VALUES (?)", (str(guild_id),))
            await db.commit()
            async with db.execute("SELECT * FROM automod_config WHERE guild_id=?", (str(guild_id),)) as cur:
                row = await cur.fetchone()
                if not row: return {}
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))

    async def get_badwords(self, guild_id):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS badwords (guild_id TEXT, word TEXT, PRIMARY KEY (guild_id, word))")
            await db.execute("CREATE TABLE IF NOT EXISTS automod_whitelist_channels (guild_id TEXT, channel_id TEXT, PRIMARY KEY (guild_id, channel_id))")
            await db.execute("CREATE TABLE IF NOT EXISTS automod_whitelist_roles (guild_id TEXT, role_id TEXT, PRIMARY KEY (guild_id, role_id))")
            async with db.execute("SELECT word FROM badwords WHERE guild_id=?", (str(guild_id),)) as cur:
                return [r[0].lower() for r in await cur.fetchall()]

    async def is_whitelisted_channel_role(self, guild_id, channel_id, user_roles):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT 1 FROM automod_whitelist_channels WHERE guild_id=? AND channel_id=?", (str(guild_id), str(channel_id))) as cur:
                if await cur.fetchone(): return True
            for r in user_roles:
                async with db.execute("SELECT 1 FROM automod_whitelist_roles WHERE guild_id=? AND role_id=?", (str(guild_id), str(r.id))) as cur:
                    if await cur.fetchone(): return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        if await is_automod_bypass(message.guild, message.author): return
        if await self.is_whitelisted_channel_role(message.guild.id, message.channel.id, message.author.roles): return
        cfg = await self.get_config(message.guild.id)
        content = message.content
        low = content.lower()
        async def punish(reason):
            try:
                await message.delete()
                p_type = cfg.get("punishment", "delete")
                p_duration = cfg.get("punishment_duration", 5)
                if p_type in ["timeout","mute"]:
                    await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=p_duration), reason=f"AutoMod: {reason}")
                    await message.channel.send(embed=error_embed(f"{message.author.mention} Muted {p_duration}m - {reason}"), delete_after=5)
                elif p_type == "kick":
                    await message.guild.kick(message.author, reason=f"AutoMod: {reason}")
                elif p_type == "ban":
                    await message.guild.ban(message.author, reason=f"AutoMod: {reason}", delete_message_days=1)
                else:
                    await message.channel.send(embed=error_embed(f"{message.author.mention} {reason}"), delete_after=5)
                if cfg.get("log_channel"):
                    ch = message.guild.get_channel(int(cfg["log_channel"]))
                    if ch: 
                        await ch.send(embed=base_embed("AutoMod Log", f"**User:** {message.author.mention}\n**Reason:** {reason}\n**Msg:** {content[:500]}"))
            except Exception as e:
                print(f"AutoMod punish error: {e}")
            return True
        if cfg.get("anti_invite",1) and self.invites.search(content): await punish("No invites!"); return
        if cfg.get("anti_link",0) and self.links.search(content): await punish("No links!"); return
        if cfg.get("anti_badwords",1):
            badwords = await self.get_badwords(message.guild.id)
            if any(w in low for w in badwords): await punish("Bad word!"); return
        if cfg.get("anti_caps",0) and len(content)>=8 and (sum(1 for c in content if c.isupper())/len(content))>0.7: await punish("Caps!"); return
        if cfg.get("anti_emoji",0) and len(self.emoji_regex.findall(content))>=10: await punish("Emoji spam!"); return

    @commands.hybrid_group(name="automod", description="Ultimate AutoMod Control")
    @mod_only()
    async def automod(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=base_embed("🛡️ AutoMod Panel", 
                "**Toggles:** `antiinvite, antilink, antispam, antibadwords`\n"
                "**Merged Commands (NEW):**\n"
                "`/automod whitelist add #channel`\n"
                "`/automod whitelist remove #channel`\n"
                "`/automod whitelist list`\n\n"
                "`/automod badwords add word`\n"
                "`/automod badwords remove word`\n"
                "`/automod badwords list`\n"
                "`/automod badwords clear`\n\n"
                "`/automod punishment timeout 10m`\n"
                "`/automod status`"))

    # TOGGLES (same)
    @automod.command(name="antiinvite")
    async def antiinvite(self, ctx, mode: str = None): await self.toggle(ctx, "anti_invite", mode)
    @automod.command(name="antilink")
    async def antilink(self, ctx, mode: str = None): await self.toggle(ctx, "anti_link", mode)
    @automod.command(name="antispam")
    async def antispam(self, ctx, mode: str = None): await self.toggle(ctx, "anti_spam", mode)
    @automod.command(name="antibadwords")
    async def antibadwords(self, ctx, mode: str = None): await self.toggle(ctx, "anti_badwords", mode)
    @automod.command(name="anticaps")
    async def anticaps(self, ctx, mode: str = None): await self.toggle(ctx, "anti_caps", mode)

    # ===== 1. WHITELIST - 3 in 1 =====
    @automod.command(name="whitelist", description="Manage whitelisted channels")
    async def whitelist(self, ctx, action: Literal["add", "remove", "list"], channel: discord.TextChannel = None):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            if action == "add":
                if not channel: return await ctx.send(embed=error_embed("Channel de! `?automod whitelist add #channel`"))
                await db.execute("INSERT OR IGNORE INTO automod_whitelist_channels VALUES (?,?)", (str(ctx.guild.id), str(channel.id)))
                await db.commit()
                await ctx.send(embed=success_embed(f"{channel.mention} whitelisted"))
            elif action == "remove":
                if not channel: return await ctx.send(embed=error_embed("Channel de! `?automod whitelist remove #channel`"))
                await db.execute("DELETE FROM automod_whitelist_channels WHERE guild_id=? AND channel_id=?", (str(ctx.guild.id), str(channel.id)))
                await db.commit()
                await ctx.send(embed=success_embed(f"{channel.mention} unwhitelisted"))
            elif action == "list":
                async with db.execute("SELECT channel_id FROM automod_whitelist_channels WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    rows = await cur.fetchall()
                if not rows: return await ctx.send(embed=base_embed("Whitelisted", "None"))
                await ctx.send(embed=base_embed("Whitelisted Channels", "\n".join([f"<#{r[0]}>" for r in rows])))

    # ===== 2. WHITELIST ROLE - 3 in 1 =====
    @automod.command(name="whitelistrole", description="Manage whitelisted roles")
    async def whitelistrole(self, ctx, action: Literal["add", "remove", "list"], role: discord.Role = None):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            if action == "add":
                if not role: return await ctx.send(embed=error_embed("Role de!"))
                await db.execute("INSERT OR IGNORE INTO automod_whitelist_roles VALUES (?,?)", (str(ctx.guild.id), str(role.id)))
                await db.commit()
                await ctx.send(embed=success_embed(f"{role.mention} whitelisted"))
            elif action == "remove":
                if not role: return await ctx.send(embed=error_embed("Role de!"))
                await db.execute("DELETE FROM automod_whitelist_roles WHERE guild_id=? AND role_id=?", (str(ctx.guild.id), str(role.id)))
                await db.commit()
                await ctx.send(embed=success_embed(f"{role.mention} unwhitelisted"))
            elif action == "list":
                async with db.execute("SELECT role_id FROM automod_whitelist_roles WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    rows = await cur.fetchall()
                if not rows: return await ctx.send(embed=base_embed("Whitelisted Roles", "None"))
                await ctx.send(embed=base_embed("Whitelisted Roles", "\n".join([f"<@&{r[0]}>" for r in rows])))

    # ===== 3. BADWORDS - 5 in 1 =====
    @automod.command(name="badwords", description="Manage bad words")
    async def badwords(self, ctx, action: Literal["add", "remove", "list", "clear", "import"], word: str = None):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            if action == "add":
                if not word: return await ctx.send(embed=error_embed("Word de! `?automod badwords add gali`"))
                await db.execute("INSERT OR IGNORE INTO badwords VALUES (?,?)", (str(ctx.guild.id), word.lower()))
                await db.commit()
                await ctx.send(embed=success_embed(f"Added: `{word}`"))
            elif action == "remove":
                if not word: return await ctx.send(embed=error_embed("Word de!"))
                await db.execute("DELETE FROM badwords WHERE guild_id=? AND word=?", (str(ctx.guild.id), word.lower()))
                await db.commit()
                await ctx.send(embed=success_embed(f"Removed: `{word}`"))
            elif action == "list":
                async with db.execute("SELECT word FROM badwords WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    rows = await cur.fetchall()
                if not rows: return await ctx.send(embed=base_embed("BadWords", "No words"))
                await ctx.send(embed=base_embed("BadWords", ", ".join([f"`{r[0]}`" for r in rows])[:2000]))
            elif action == "clear":
                await db.execute("DELETE FROM badwords WHERE guild_id=?", (str(ctx.guild.id),))
                await db.commit()
                await ctx.send(embed=success_embed("Cleared all badwords"))
            elif action == "import":
                if not word: return await ctx.send(embed=error_embed("Words comma se de! `?automod badwords import word1, word2`"))
                lst = [w.strip().lower() for w in word.split(",") if w.strip()]
                for w in lst: await db.execute("INSERT OR IGNORE INTO badwords VALUES (?,?)", (str(ctx.guild.id), w))
                await db.commit()
                await ctx.send(embed=success_embed(f"Imported {len(lst)} words"))

    @automod.command(name="punishment")
    async def punishment_cmd(self, ctx, type: str, duration: str = "5m"):
        type = type.lower()
        if type not in ["delete","timeout","mute","kick","ban"]:
            return await ctx.send(embed=error_embed("Use: delete / timeout / mute / kick / ban"))
        mins = parse_duration(duration) if type in ["timeout","mute"] else 0
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("UPDATE automod_config SET punishment=?, punishment_duration=? WHERE guild_id=?", (type, mins, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Punishment: **{type}** {f'({mins}m)' if mins else ''} ✅"))

    @automod.command(name="status")
    async def status(self, ctx):
        cfg = await self.get_config(ctx.guild.id)
        desc = "\n".join([f"**{k}**: {'🟢' if v==1 else '🔴'}" for k,v in cfg.items() if 'anti_' in k])
        await ctx.send(embed=base_embed(f"AutoMod Status - {ctx.guild.name}", desc))
    
    async def toggle(self, ctx, key, mode):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO automod_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            if mode is None:
                async with db.execute(f"SELECT {key} FROM automod_config WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    row=await cur.fetchone(); val=0 if row and row[0]==1 else 1
            else: val=1 if mode.lower() in ["on","enable"] else 0
            await db.execute(f"UPDATE automod_config SET {key}=? WHERE guild_id=?", (val, str(ctx.guild.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{key} {'Enabled ✅' if val else 'Disabled ❌'}"))

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
