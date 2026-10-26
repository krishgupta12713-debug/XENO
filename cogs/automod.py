import discord
from discord.ext import commands
import re, time, os, aiosqlite
from collections import defaultdict, deque
from utils.embeds import base_embed, error_embed, success_embed
from utils.security_checks import mod_only, is_automod_bypass

spam_tracker = defaultdict(lambda: deque(maxlen=10))
last_msg = {}

def parse_duration(text: str) -> int:
    """ 10s, 5m, 2h, 1d -> minutes me return """
    if not text: return 5
    text = text.lower().strip()
    try:
        if text[-1] == 's': return max(1, int(text[:-1]) // 60 or 1)
        if text[-1] == 'm': return int(text[:-1])
        if text[-1] == 'h': return int(text[:-1]) * 60
        if text[-1] == 'd': return int(text[:-1]) * 1440
        return int(text) # direct number = minutes
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
            for col in [("anti_badwords","INTEGER DEFAULT 1"),("anti_caps","INTEGER DEFAULT 0"),("anti_emoji","INTEGER DEFAULT 0"),("anti_zalgo","INTEGER DEFAULT 0"),("anti_duplicate","INTEGER DEFAULT 0"),("punishment","TEXT DEFAULT 'delete'"),("punishment_duration","INTEGER DEFAULT 5"),("log_channel","TEXT")]:
                try: await db.execute(f"ALTER TABLE automod_config ADD COLUMN {col[0]} {col[1]}")
                except: pass
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

                if p_type == "timeout" or p_type == "mute":
                    await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=p_duration), reason=f"AutoMod: {reason}")
                    await message.channel.send(embed=error_embed(f"{message.author.mention} Muted {p_duration}m - {reason}"), delete_after=5)
                elif p_type == "kick":
                    await message.guild.kick(message.author, reason=f"AutoMod: {reason}")
                    await message.channel.send(embed=error_embed(f"{message.author.mention} Kicked - {reason}"), delete_after=5)
                elif p_type == "ban":
                    await message.guild.ban(message.author, reason=f"AutoMod: {reason}", delete_message_days=1)
                    await message.channel.send(embed=error_embed(f"{message.author.mention} Banned - {reason}"), delete_after=5)
                else: # delete
                    await message.channel.send(embed=error_embed(f"{message.author.mention} {reason}"), delete_after=5)

                if cfg.get("log_channel"):
                    ch = message.guild.get_channel(int(cfg["log_channel"]))
                    if ch: 
                        await ch.send(embed=base_embed("AutoMod Log", f"**User:** {message.author.mention} (`{message.author.id}`)\n**Reason:** {reason}\n**Punishment:** {p_type} {p_duration}m\n**Msg:** {content[:500]}\n**Channel:** {message.channel.mention}"))
            except Exception as e:
                print(f"AutoMod punish error: {e}")
            return True

        if cfg.get("anti_invite",1) and self.invites.search(content):
            await punish("No invites allowed!"); return
        if cfg.get("anti_link",0) and self.links.search(content):
            await punish("No links allowed!"); return
        if cfg.get("anti_badwords",1):
            badwords = await self.get_badwords(message.guild.id)
            if any(w in low for w in badwords):
                await punish("Bad word not allowed!"); return
        if cfg.get("anti_caps",0) and len(content)>=8 and (sum(1 for c in content if c.isupper())/len(content))>0.7:
            await punish("Too many caps!"); return
        if (cfg.get("anti_emoji",0) or cfg.get("anti_emoji_spam",0)) and len(self.emoji_regex.findall(content))>=10:
            await punish("Emoji spam!"); return
        if cfg.get("anti_zalgo",0) and re.search(r'[\u0300-\u036f]{3,}', content):
            await punish("Weird text not allowed!"); return
        if cfg.get("anti_duplicate",0):
            key = f"{message.guild.id}_{message.author.id}"
            if last_msg.get(key) == content and len(content)>5:
                await punish("No duplicate messages!"); return
            last_msg[key] = content
        if cfg.get("anti_spam",1):
            now=time.time(); tr=spam_tracker[message.author.id]; tr.append(now)
            if len(tr)>=5 and (now-tr[0])<4:
                try: 
                    dur = cfg.get("punishment_duration",5)
                    await message.author.timeout(discord.utils.utcnow()+discord.timedelta(minutes=dur), reason="Spam")
                    tr.clear()
                except: pass
        if cfg.get("anti_massmention",1) and len(message.mentions)>=5:
            await punish("Mass mention not allowed!"); return

    @commands.hybrid_group(name="automod", description="Ultimate AutoMod Control")
    @mod_only()
    async def automod(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=base_embed("🛡️ AutoMod GOD PANEL - Custom Punishment", 
                "**Toggles:**\n`antiinvite, antilink, antispam, antimassmention, antibadwords, anticaps, antiemoji, antizalgo, antiduplicate, antisticker`\n\n"
                "**Badwords:**\n`addword, removeword, badwords, clearbadwords, importwords`\n\n"
                "**Whitelist:**\n`whitelist #ch, unwhitelist #ch, whitelistrole @role`\n\n"
                "**Punishment Setup (NEW):**\n"
                "`punishment delete` - Only delete msg\n"
                "`punishment timeout 10m` - Timeout 10 min\n"
                "`punishment mute 30m` - Mute 30 min\n"
                "`punishment kick` - Kick user\n"
                "`punishment ban` - Ban user\n\n"
                "Time format: `10s, 5m, 2h, 1d`\n\n"
                "**Other:**\n`log #channel, status, reset`"))

    @automod.command(name="antiinvite")
    async def antiinvite(self, ctx, mode: str = None): await self.toggle(ctx, "anti_invite", mode)
    @automod.command(name="antilink")
    async def antilink(self, ctx, mode: str = None): await self.toggle(ctx, "anti_link", mode)
    @automod.command(name="antispam")
    async def antispam(self, ctx, mode: str = None): await self.toggle(ctx, "anti_spam", mode)
    @automod.command(name="antimassmention")
    async def antimassmention(self, ctx, mode: str = None): await self.toggle(ctx, "anti_massmention", mode)
    @automod.command(name="antibadwords")
    async def antibadwords(self, ctx, mode: str = None): await self.toggle(ctx, "anti_badwords", mode)
    @automod.command(name="anticaps")
    async def anticaps(self, ctx, mode: str = None): await self.toggle(ctx, "anti_caps", mode)
    @automod.command(name="antiemoji")
    async def antiemoji(self, ctx, mode: str = None): await self.toggle(ctx, "anti_emoji", mode)
    @automod.command(name="antizalgo")
    async def antizalgo(self, ctx, mode: str = None): await self.toggle(ctx, "anti_zalgo", mode)
    @automod.command(name="antiduplicate")
    async def antiduplicate(self, ctx, mode: str = None): await self.toggle(ctx, "anti_duplicate", mode)
    @automod.command(name="antisticker")
    async def antisticker(self, ctx, mode: str = None): await self.toggle(ctx, "anti_sticker", mode)

    @automod.command(name="addword")
    async def addword(self, ctx, *, word: str):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO badwords VALUES (?,?)", (str(ctx.guild.id), word.lower())); await db.commit()
        await ctx.send(embed=success_embed(f"Added: `{word}`"))
    @automod.command(name="removeword")
    async def removeword(self, ctx, *, word: str):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM badwords WHERE guild_id=? AND word=?", (str(ctx.guild.id), word.lower())); await db.commit()
        await ctx.send(embed=success_embed(f"Removed: `{word}`"))
    @automod.command(name="badwords")
    async def badwords_list(self, ctx):
        words = await self.get_badwords(ctx.guild.id)
        if not words: return await ctx.send(embed=base_embed("BadWords", "No words"))
        await ctx.send(embed=base_embed("BadWords", ", ".join([f"`{w}`" for w in words])[:2000]))
    @automod.command(name="clearbadwords")
    async def clearbadwords(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM badwords WHERE guild_id=?", (str(ctx.guild.id),)); await db.commit()
        await ctx.send(embed=success_embed("Cleared all"))
    @automod.command(name="importwords")
    async def importwords(self, ctx, *, words: str):
        lst = [w.strip().lower() for w in words.split(",") if w.strip()]
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            for w in lst: await db.execute("INSERT OR IGNORE INTO badwords VALUES (?,?)", (str(ctx.guild.id), w))
            await db.commit()
        await ctx.send(embed=success_embed(f"Imported {len(lst)} words"))

    @automod.command(name="whitelist")
    async def whitelist_ch(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO automod_whitelist_channels VALUES (?,?)", (str(ctx.guild.id), str(channel.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{channel.mention} whitelisted"))
    @automod.command(name="unwhitelist")
    async def unwhitelist_ch(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM automod_whitelist_channels WHERE guild_id=? AND channel_id=?", (str(ctx.guild.id), str(channel.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{channel.mention} unwhitelisted"))
    @automod.command(name="whitelisted")
    async def whitelisted_list(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT channel_id FROM automod_whitelist_channels WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                rows = await cur.fetchall()
        if not rows: return await ctx.send(embed=base_embed("Whitelisted", "None"))
        await ctx.send(embed=base_embed("Whitelisted Channels", "\n".join([f"<#{r[0]}>" for r in rows])))
    @automod.command(name="whitelistrole")
    async def whitelist_role(self, ctx, role: discord.Role):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO automod_whitelist_roles VALUES (?,?)", (str(ctx.guild.id), str(role.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{role.mention} whitelisted"))
    @automod.command(name="unwhitelistrole")
    async def unwhitelist_role(self, ctx, role: discord.Role):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM automod_whitelist_roles WHERE guild_id=? AND role_id=?", (str(ctx.guild.id), str(role.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{role.mention} unwhitelisted"))

    # ===== NEW CUSTOM PUNISHMENT COMMAND =====
    @automod.command(name="punishment")
    async def punishment_cmd(self, ctx, type: str, duration: str = "5m"):
        type = type.lower()
        if type not in ["delete","timeout","mute","kick","ban"]:
            return await ctx.send(embed=error_embed("Use: `delete / timeout / mute / kick / ban`\nExample: `?automod punishment timeout 10m`"))

        mins = parse_duration(duration) if type in ["timeout","mute"] else 0
        
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("UPDATE automod_config SET punishment=?, punishment_duration=? WHERE guild_id=?", (type, mins, str(ctx.guild.id)))
            await db.commit()
        
        if type in ["timeout","mute"]:
            await ctx.send(embed=success_embed(f"Punishment set to: **{type}** for **{mins} minutes** ({duration}) ✅"))
        elif type in ["kick","ban"]:
            await ctx.send(embed=success_embed(f"Punishment set to: **{type}** ✅"))
        else:
            await ctx.send(embed=success_embed(f"Punishment set to: **Only Delete** ✅"))

    @automod.command(name="log")
    async def log_ch(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("UPDATE automod_config SET log_channel=? WHERE guild_id=?", (str(channel.id), str(ctx.guild.id))); await db.commit()
        await ctx.send(embed=success_embed(f"AutoMod log: {channel.mention}"))
    @automod.command(name="status")
    async def status(self, ctx):
        cfg = await self.get_config(ctx.guild.id)
        desc = "\n".join([f"**{k.replace('anti_','').title()}**: {'🟢 ON' if v==1 else '🔴 OFF' if v==0 else f'`{v}`'}" for k,v in cfg.items() if k not in ['guild_id','log_channel','punishment','punishment_duration']])
        p_type = cfg.get('punishment','delete')
        p_dur = cfg.get('punishment_duration',5)
        desc+=f"\n\n**Punishment:** `{p_type}`" + (f" ({p_dur}m)" if p_type in ['timeout','mute'] else "")
        desc+=f"\n**Log:** <#{cfg.get('log_channel')}>" if cfg.get('log_channel') else "\n**Log:** Not set"
        await ctx.send(embed=base_embed(f"AutoMod Status - {ctx.guild.name}", desc))
    @automod.command(name="reset")
    async def reset(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM automod_config WHERE guild_id=?", (str(ctx.guild.id),))
            await db.execute("DELETE FROM badwords WHERE guild_id=?", (str(ctx.guild.id),))
            await db.execute("DELETE FROM automod_whitelist_channels WHERE guild_id=?", (str(ctx.guild.id),))
            await db.execute("DELETE FROM automod_whitelist_roles WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        await ctx.send(embed=success_embed("AutoMod fully reset!"))

    async def toggle(self, ctx, key, mode):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO automod_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            if mode is None:
                async with db.execute(f"SELECT {key} FROM automod_config WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    row=await cur.fetchone(); val=0 if row and row[0]==1 else 1
            else: val=1 if mode.lower() in ["on","enable","yes","true"] else 0
            await db.execute(f"UPDATE automod_config SET {key}=? WHERE guild_id=?", (val, str(ctx.guild.id))); await db.commit()
        await ctx.send(embed=success_embed(f"{key.replace('anti_','').title()} {'Enabled ✅' if val else 'Disabled ❌'}"))

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
