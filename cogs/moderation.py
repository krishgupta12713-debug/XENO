import discord
from discord.ext import commands
from utils.embeds import base_embed, success_embed, error_embed
import datetime, asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.ban(reason=reason)
        await ctx.send(embed=success_embed(f"Banned {member} | {reason}"))

    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, reason="Unbanned"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(embed=success_embed(f"Unbanned {user}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.kick(reason=reason)
        await ctx.send(embed=success_embed(f"Kicked {member}"))

    @commands.hybrid_command(name="mute", description="Timeout user")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="Muted"):
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await ctx.send(embed=success_embed(f"Muted {member} for {minutes}m"))

    @commands.hybrid_command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(embed=success_embed(f"Unmuted {member}"))

    @commands.hybrid_command(name="purge", description="Delete messages")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 50, user: discord.Member = None):
        if user:
            def check(m): return m.author == user
            deleted = await ctx.channel.purge(limit=amount, check=check)
        else:
            deleted = await ctx.channel.purge(limit=amount+1)
        await ctx.send(embed=success_embed(f"Purged {len(deleted)} messages"), delete_after=3)

    @commands.hybrid_command(name="nuke", description="Nuke channel")
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        ch = await ctx.channel.clone(reason=f"Nuked by {ctx.author}")
        await ch.edit(position=ctx.channel.position)
        await ctx.channel.delete(reason="Nuke")
        await ch.send(embed=success_embed(f"Channel nuked by {ctx.author.mention}"))

    @commands.hybrid_command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(embed=success_embed(f"Slowmode set to {seconds}s"))

    @commands.hybrid_command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=success_embed(f"{channel.mention} locked 🔒"))

    @commands.hybrid_command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=success_embed(f"{channel.mention} unlocked 🔓"))

    @commands.hybrid_command(name="hide")
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send(embed=success_embed(f"{channel.mention} hidden"), ephemeral=True)

    @commands.hybrid_command(name="unhide")
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send(embed=success_embed(f"{channel.mention} unhidden"))

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="Warned"):
        import aiosqlite, os, time
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (str(ctx.guild.id), str(member.id), reason, int(time.time())))
            await db.commit()
        await ctx.send(embed=base_embed("Warned", f"{member.mention} - {reason}"))

    @commands.hybrid_command(name="warnings")
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        import aiosqlite, os
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT reason, time FROM warns WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id))) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send(embed=base_embed("Warnings", "No warnings"))
        desc = "\n".join([f"`{i+1}.` {r[0]} - <t:{r[1]}:R>" for i,r in enumerate(rows[-10:])])
        await ctx.send(embed=base_embed(f"{member.display_name}'s Warnings", desc))

    @commands.hybrid_command(name="clearwarn")
    @commands.has_permissions(manage_messages=True)
    async def clearwarn(self, ctx, member: discord.Member):
        import aiosqlite, os
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Cleared warnings for {member}"))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
