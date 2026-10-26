import discord
from discord.ext import commands
from utils.security_checks import get_audit_actor, is_trusted, quarantine_user
from utils.embeds import security_embed, base_embed
import asyncio

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.channel_delete)
        if not actor or actor.bot: return
        if await is_trusted(guild, actor): return

        # Auto Recovery
        try:
            new_ch = await channel.clone(reason="Anti-Channel Recovery")
            await new_ch.edit(position=channel.position)
        except: pass

        member = guild.get_member(actor.id)
        if member:
            await quarantine_user(guild, member, "Anti-Channel Delete")
            for ch in guild.text_channels:
                if "log" in ch.name.lower():
                    await ch.send(embed=security_embed("Channel Delete", actor, channel.name))
                    break

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.channel_create)
        if not actor or await is_trusted(guild, actor): return
        try:
            await channel.delete(reason="Anti-Channel Create")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Channel Create")
        except: pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.role_delete)
        if not actor or await is_trusted(guild, actor): return
        try:
            await guild.create_role(name=role.name, color=role.color, permissions=role.permissions, hoist=role.hoist, mentionable=role.mentionable, reason="Anti-Role Recovery")
        except: pass
        m = guild.get_member(actor.id)
        if m: await quarantine_user(guild, m, "Anti-Role Delete")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        actor = await get_audit_actor(role.guild, discord.AuditLogAction.role_create)
        if not actor or await is_trusted(role.guild, actor): return
        try:
            if role.permissions.administrator or role.permissions.ban_members:
                await role.delete(reason="Anti-Role Dangerous Perms")
                m = role.guild.get_member(actor.id)
                if m: await quarantine_user(role.guild, m, "Dangerous Role Create")
        except: pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        actor = await get_audit_actor(guild, discord.AuditLogAction.ban)
        if not actor or await is_trusted(guild, actor): return
        try:
            await guild.unban(user, reason="Anti-Ban Recovery")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Ban")
        except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.kick)
        if not actor or await is_trusted(guild, actor): return
        m = guild.get_member(actor.id)
        if m: await quarantine_user(guild, m, "Anti-Kick")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot: return
        guild = member.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.bot_add)
        if not actor or await is_trusted(guild, actor): return
        try:
            await member.ban(reason="Anti-Bot Unauthorized")
            mod = guild.get_member(actor.id)
            if mod: await quarantine_user(guild, mod, "Unauthorized Bot Add")
        except: pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.webhook_create)
        if not actor or await is_trusted(guild, actor): return
        try:
            wbs = await channel.webhooks()
            for wh in wbs:
                if wh.user and wh.user.id == actor.id:
                    await wh.delete(reason="Anti-Webhook")
            m = guild.get_member(actor.id)
            if m: await quarantine_user(guild, m, "Anti-Webhook")
        except: pass

    @commands.hybrid_command(name="whitelist", description="Whitelist a user/bot")
    @commands.has_permissions(administrator=True)
    async def whitelist(self, ctx, user: discord.User):
        import aiosqlite, os
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO whitelist VALUES (?,?,?)", (str(ctx.guild.id), str(user.id), "user"))
            await db.commit()
        await ctx.send(embed=base_embed("Whitelisted", f"`{user.id}` added to trusted list"))

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))