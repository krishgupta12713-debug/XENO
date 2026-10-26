import discord
from discord.ext import commands
from utils.security_checks import get_audit_actor, is_nuke_trusted, quarantine_user, mod_only
from utils.embeds import security_embed, base_embed, success_embed, error_embed
import aiosqlite, os, asyncio

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_config(self, guild_id: int):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT * FROM antinuke_config WHERE guild_id=?", (str(guild_id),)) as cur:
                row = await cur.fetchone()
                if not row:
                    await db.execute("INSERT INTO antinuke_config (guild_id) VALUES (?)", (str(guild_id),))
                    await db.commit()
                    return {"anti_channel":0,"anti_role":0,"anti_ban":0,"anti_kick":0,"anti_bot":0,"anti_webhook":0,"log_channel":None}
                return {
                    "anti_channel": row[1], "anti_role": row[2], "anti_ban": row[3],
                    "anti_kick": row[4], "anti_bot": row[5], "anti_webhook": row[6],
                    "log_channel": row[7]
                }

    async def send_log(self, guild, action, actor, target):
        config = await self.get_config(guild.id)
        if config["log_channel"]:
            ch = guild.get_channel(int(config["log_channel"]))
            if ch:
                try: await ch.send(embed=security_embed(action, actor, target))
                except: pass

    # ===== LISTENERS - SIRF OWNER SAFE, WHITELIST BHI BAN HOGA =====
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        config = await self.get_config(channel.guild.id)
        if not config["anti_channel"]: return
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.channel_delete)
        if not actor or actor.bot: return
        if await is_nuke_trusted(guild, actor): return # Whitelist yaha check nahi hoga
        try:
            new_ch = await channel.clone(reason="Anti-Channel Recovery")
            await new_ch.edit(position=channel.position)
        except: pass
        member = guild.get_member(actor.id)
        if member:
            await quarantine_user(guild, member, "Anti-Channel Delete")
            await self.send_log(guild, "Channel Delete", actor, channel.name)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        config = await self.get_config(channel.guild.id)
        if not config["anti_channel"]: return
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.channel_create)
        if not actor or await is_nuke_trusted(guild, actor): return
        try:
            await channel.delete(reason="Anti-Channel Create")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Channel Create")
        except: pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        config = await self.get_config(role.guild.id)
        if not config["anti_role"]: return
        guild = role.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.role_delete)
        if not actor or await is_nuke_trusted(guild, actor): return
        try:
            await guild.create_role(name=role.name, color=role.color, permissions=role.permissions, hoist=role.hoist, mentionable=role.mentionable, reason="Anti-Role Recovery")
        except: pass
        m = guild.get_member(actor.id)
        if m: await quarantine_user(guild, m, "Anti-Role Delete")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        config = await self.get_config(role.guild.id)
        if not config["anti_role"]: return
        actor = await get_audit_actor(role.guild, discord.AuditLogAction.role_create)
        if not actor or await is_nuke_trusted(role.guild, actor): return
        try:
            if role.permissions.administrator or role.permissions.ban_members:
                await role.delete(reason="Anti-Role Dangerous Perms")
                m = role.guild.get_member(actor.id)
                if m: await quarantine_user(role.guild, m, "Dangerous Role Create")
        except: pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        config = await self.get_config(guild.id)
        if not config["anti_ban"]: return
        actor = await get_audit_actor(guild, discord.AuditLogAction.ban)
        if not actor or await is_nuke_trusted(guild, actor): return
        try:
            await guild.unban(user, reason="Anti-Ban Recovery")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Ban")
        except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = await self.get_config(member.guild.id)
        if not config["anti_kick"]: return
        guild = member.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.kick)
        if not actor or await is_nuke_trusted(guild, actor): return
        m = guild.get_member(actor.id)
        if m: await quarantine_user(guild, m, "Anti-Kick")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot: return
        config = await self.get_config(member.guild.id)
        if not config["anti_bot"]: return
        guild = member.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.bot_add)
        if not actor or await is_nuke_trusted(guild, actor): return
        try:
            await member.ban(reason="Anti-Bot Unauthorized")
            mod = guild.get_member(actor.id)
            if mod: await quarantine_user(guild, mod, "Unauthorized Bot Add")
        except: pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        config = await self.get_config(channel.guild.id)
        if not config["anti_webhook"]: return
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.webhook_create)
        if not actor or await is_nuke_trusted(guild, actor): return
        try:
            wbs = await channel.webhooks()
            for wh in wbs:
                if wh.user and wh.user.id == actor.id:
                    await wh.delete(reason="Anti-Webhook")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Webhook")
        except: pass

    # ===== MANUAL COMMANDS - SIRF MOD/ADMIN/OWNER =====
    @commands.hybrid_group(name="antinuke", description="AntiNuke setup")
    @mod_only()
    async def antinuke(self, ctx):
        if ctx.invoked_subcommand is None:
            config = await self.get_config(ctx.guild.id)
            e = base_embed("🛡️ AntiNuke Config")
            e.add_field(name="Channel", value="ON ✅" if config["anti_channel"] else "OFF ❌", inline=True)
            e.add_field(name="Role", value="ON ✅" if config["anti_role"] else "OFF ❌", inline=True)
            e.add_field(name="Ban", value="ON ✅" if config["anti_ban"] else "OFF ❌", inline=True)
            e.add_field(name="Kick", value="ON ✅" if config["anti_kick"] else "OFF ❌", inline=True)
            e.add_field(name="Bot", value="ON ✅" if config["anti_bot"] else "OFF ❌", inline=True)
            e.add_field(name="Webhook", value="ON ✅" if config["anti_webhook"] else "OFF ❌", inline=True)
            e.add_field(name="Log", value=f"<#{config['log_channel']}>" if config["log_channel"] else "Not set", inline=False)
            await ctx.send(embed=e)

    @antinuke.command(name="enable", description="Enable all antinuke")
    @mod_only()
    async def enable(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO antinuke_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE antinuke_config SET anti_channel=1, anti_role=1, anti_ban=1, anti_kick=1, anti_bot=1, anti_webhook=1 WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        await ctx.send(embed=success_embed("AntiNuke ENABLED ✅"))

    @antinuke.command(name="disable", description="Disable all antinuke")
    @mod_only()
    async def disable(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("UPDATE antinuke_config SET anti_channel=0, anti_role=0, anti_ban=0, anti_kick=0, anti_bot=0, anti_webhook=0 WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        await ctx.send(embed=success_embed("AntiNuke DISABLED ❌"))

    @antinuke.command(name="log", description="Set log channel")
    @mod_only()
    async def log_channel(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO antinuke_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE antinuke_config SET log_channel=? WHERE guild_id=?", (str(channel.id), str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Log set to {channel.mention}"))

    @commands.hybrid_command(name="whitelist", description="Whitelist a user - only bypass automod")
    @mod_only()
    async def whitelist(self, ctx, user: discord.User):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO whitelist VALUES (?,?,?)", (str(ctx.guild.id), str(user.id), "user"))
            await db.commit()
        await ctx.send(embed=base_embed("Whitelisted", f"{user} added - Will bypass AutoMod but NOT AntiNuke"))

    @commands.hybrid_command(name="unwhitelist")
    @mod_only()
    async def unwhitelist(self, ctx, user: discord.User):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(user.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Removed {user} from whitelist"))

    @commands.hybrid_command(name="whitelistlist", aliases=["wlshow"])
    @mod_only()
    async def wlshow(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT user_id FROM whitelist WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send(embed=base_embed("Whitelist", "No one whitelisted"))
        desc = "\n".join([f"<@{r[0]}> - `{r[0]}`" for r in rows])
        await ctx.send(embed=base_embed(f"Whitelisted [{len(rows)}]", desc[:4000]))

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
