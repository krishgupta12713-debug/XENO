import discord
from discord.ext import commands
from utils.embeds import base_embed, success_embed, error_embed
from utils.security_checks import mod_only, everyone
import datetime, aiosqlite, os, time

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban", description="Ban user - Mod only")
    @mod_only()
    async def ban(self, ctx, member: discord.Member, *, reason="No reason"):
        if member.id == ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Can't ban Owner!"))
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("You can't ban someone with higher/equal role!"))
        try:
            await member.ban(reason=f"{reason} | By {ctx.author}")
            await ctx.send(embed=success_embed(f"Banned {member} | {reason}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="unban", description="Unban user - Mod only")
    @mod_only()
    async def unban(self, ctx, user_id: str, *, reason="Unbanned"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(embed=success_embed(f"Unbanned {user}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="kick", description="Kick user - Mod only")
    @mod_only()
    async def kick(self, ctx, member: discord.Member, *, reason="No reason"):
        if member.id == ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Can't kick Owner!"))
        try:
            await member.kick(reason=reason)
            await ctx.send(embed=success_embed(f"Kicked {member}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="mute", description="Timeout user - Mod only")
    @mod_only()
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="Muted"):
        try:
            await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
            await ctx.send(embed=success_embed(f"Muted {member} for {minutes}m | {reason}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="unmute", description="Unmute - Mod only")
    @mod_only()
    async def unmute(self, ctx, member: discord.Member):
        try:
            await member.timeout(None)
            await ctx.send(embed=success_embed(f"Unmuted {member}"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="purge", description="Delete messages - Mod only")
    @mod_only()
    async def purge(self, ctx, amount: int = 50, user: discord.Member = None):
        if amount > 100: amount = 100
        try:
            if user:
                def check(m): return m.author == user
                deleted = await ctx.channel.purge(limit=amount, check=check)
            else:
                deleted = await ctx.channel.purge(limit=amount+1)
            await ctx.send(embed=success_embed(f"Purged {len(deleted)} messages"), delete_after=3)
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="nuke", description="Nuke channel - Mod only")
    @mod_only()
    async def nuke(self, ctx):
        try:
            ch = await ctx.channel.clone(reason=f"Nuked by {ctx.author}")
            await ch.edit(position=ctx.channel.position)
            await ctx.channel.delete(reason="Nuke")
            await ch.send(embed=success_embed(f"Channel nuked by {ctx.author.mention} 💥"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="slowmode", description="Set slowmode - Mod only")
    @mod_only()
    async def slowmode(self, ctx, seconds: int = 0):
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            await ctx.send(embed=success_embed(f"Slowmode set to {seconds}s"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="lock", description="Lock channel - Mod only")
    @mod_only()
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(embed=success_embed(f"{channel.mention} locked 🔒"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="unlock", description="Unlock channel - Mod only")
    @mod_only()
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
            await ctx.send(embed=success_embed(f"{channel.mention} unlocked 🔓"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="hide", description="Hide channel - Mod only")
    @mod_only()
    async def hide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)
            await ctx.send(embed=success_embed(f"{channel.mention} hidden"), ephemeral=True)
        except: pass

    @commands.hybrid_command(name="unhide", description="Unhide channel - Mod only")
    @mod_only()
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=True)
            await ctx.send(embed=success_embed(f"{channel.mention} unhidden"))
        except Exception as e:
            await ctx.send(embed=error_embed(str(e)))

    @commands.hybrid_command(name="warn", description="Warn user - Mod only")
    @mod_only()
    async def warn(self, ctx, member: discord.Member, *, reason="Warned"):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (str(ctx.guild.id), str(member.id), reason, int(time.time())))
            await db.commit()
        await ctx.send(embed=base_embed("Warned", f"{member.mention} - {reason}"))

    @commands.hybrid_command(name="warnings", description="Check warnings - Everyone")
    @everyone()
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT reason, time FROM warns WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id))) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send(embed=base_embed("Warnings", f"No warnings for {member.display_name}"))
        desc = "\n".join([f"`{i+1}.` {r[0]} - <t:{r[1]}:R>" for i,r in enumerate(rows[-10:])])
        await ctx.send(embed=base_embed(f"{member.display_name}'s Warnings", desc))

    @commands.hybrid_command(name="clearwarn", description="Clear warnings - Mod only")
    @mod_only()
    async def clearwarn(self, ctx, member: discord.Member):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Cleared warnings for {member}"))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
