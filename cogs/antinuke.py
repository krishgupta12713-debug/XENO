import discord
from discord.ext import commands
from utils.security_checks import get_audit_actor, is_nuke_trusted, quarantine_user, mod_only
from utils.embeds import security_embed, base_embed, success_embed, error_embed
import aiosqlite, os
from typing import Literal

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

    # ===== LISTENERS =====
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        config = await self.get_config(channel.guild.id)
        if not config["anti_channel"]: return
        guild = channel.guild
        actor = await get_audit_actor(guild, discord.AuditLogAction.channel_delete)
        if not actor or actor.bot: return
        if await is_nuke_trusted(guild, actor): return
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

    # ===== AESTHETIC MAIN PANEL =====
    @commands.hybrid_group(name="antinuke", description="🛡️ AntiNuke Control Panel")
    @mod_only()
    async def antinuke(self, ctx):
        if ctx.invoked_subcommand is None:
            config = await self.get_config(ctx.guild.id)
            
            embed = discord.Embed(
                title=f"🛡️ {ctx.guild.name} - AntiNuke",
                description="> **Ultimate Server Protection System**\n> Protects from nukers, even whitelisted users will be punished except Owner.",
                color=0x2B2D31
            )
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else self.bot.user.display_avatar.url)
            
            def status(v): return "> 🟢 **ON**" if v else "> 🔴 **OFF**"
            
            embed.add_field(name="📁 Anti-Channel", value=status(config["anti_channel"]), inline=True)
            embed.add_field(name="🎭 Anti-Role", value=status(config["anti_role"]), inline=True)
            embed.add_field(name="🔨 Anti-Ban", value=status(config["anti_ban"]), inline=True)
            embed.add_field(name="👢 Anti-Kick", value=status(config["anti_kick"]), inline=True)
            embed.add_field(name="🤖 Anti-Bot", value=status(config["anti_bot"]), inline=True)
            embed.add_field(name="🔗 Anti-Webhook", value=status(config["anti_webhook"]), inline=True)
            
            log_txt = f"<#{config['log_channel']}> ✅" if config["log_channel"] else "`Not Set` ❌"
            embed.add_field(name="📜 Log Channel", value=log_txt, inline=False)
            
            embed.add_field(
                name="📚 Commands",
                value=(
                    "```\n"
                    "/antinuke enable - Enable all\n"
                    "/antinuke disable - Disable all\n"
                    "/antinuke log #channel\n"
                    "/whitelist add @user\n"
                    "```"
                ),
                inline=False
            )
            embed.set_footer(text=f"Requested by {ctx.author} • Owner bypass only", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @antinuke.command(name="enable", description="Enable all protection")
    @mod_only()
    async def enable(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO antinuke_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE antinuke_config SET anti_channel=1, anti_role=1, anti_ban=1, anti_kick=1, anti_bot=1, anti_webhook=1 WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        embed = discord.Embed(title="✅ AntiNuke Enabled", description="> All protections are now **ACTIVE** 🟢\n> Your server is secured.", color=0x00FF7F)
        await ctx.send(embed=embed)

    @antinuke.command(name="disable", description="Disable all protection")
    @mod_only()
    async def disable(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("UPDATE antinuke_config SET anti_channel=0, anti_role=0, anti_ban=0, anti_kick=0, anti_bot=0, anti_webhook=0 WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        embed = discord.Embed(title="❌ AntiNuke Disabled", description="> All protections are now **OFF** 🔴\n> Server is vulnerable.", color=0xFF4D4D)
        await ctx.send(embed=embed)

    @antinuke.command(name="log", description="Set security log channel")
    @mod_only()
    async def log_channel(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO antinuke_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE antinuke_config SET log_channel=? WHERE guild_id=?", (str(channel.id), str(ctx.guild.id)))
            await db.commit()
        embed = discord.Embed(title="📜 Log Channel Updated", description=f"> Logs will be sent to {channel.mention}", color=0x2B2D31)
        await ctx.send(embed=embed)

    # ===== 3 in 1 WHITELIST - AESTHETIC =====
    @commands.hybrid_command(name="whitelist", description="Manage whitelisted users")
    @mod_only()
    async def whitelist(self, ctx, action: Literal["add", "remove", "list"], user: discord.User = None):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS whitelist (guild_id TEXT, user_id TEXT, type TEXT, PRIMARY KEY (guild_id, user_id))")
            
            if action == "add":
                if not user:
                    return await ctx.send(embed=error_embed("❌ User tag karo! `?whitelist add @user`"))
                await db.execute("INSERT OR IGNORE INTO whitelist VALUES (?,?,?)", (str(ctx.guild.id), str(user.id), "user"))
                await db.commit()
                
                embed = discord.Embed(
                    title="✅ User Whitelisted",
                    description=f"> {user.mention} (`{user.id}`) has been added.\n> **Note:** Will bypass AutoMod but **NOT** AntiNuke.",
                    color=0x00FF7F
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text=f"Added by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                await ctx.send(embed=embed)

            elif action == "remove":
                if not user:
                    return await ctx.send(embed=error_embed("❌ User tag karo! `?whitelist remove @user`"))
                await db.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(user.id)))
                await db.commit()
                
                embed = discord.Embed(
                    title="🗑️ Whitelist Removed",
                    description=f"> {user.mention} removed from whitelist.",
                    color=0xFF4D4D
                )
                await ctx.send(embed=embed)

            elif action == "list":
                async with db.execute("SELECT user_id FROM whitelist WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    rows = await cur.fetchall()
                
                if not rows:
                    embed = discord.Embed(title="📋 Whitelist Empty", description="> No users whitelisted yet.", color=0x2B2D31)
                    return await ctx.send(embed=embed)
                
                desc = "\n".join([f"`{i+1}.` <@{r[0]}> - `{r[0]}`" for i, r in enumerate(rows)])
                embed = discord.Embed(
                    title=f"📋 Whitelisted Users [{len(rows)}]",
                    description=desc,
                    color=0x2B2D31
                )
                embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
                embed.set_footer(text=f"{ctx.guild.name} • Owner can still punish whitelisted", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
