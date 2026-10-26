import discord
from discord.ext import commands
from utils.embeds import base_embed, success_embed, error_embed
import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.ban(reason=reason)
        await ctx.send(embed=success_embed(f"Banned {member} | {reason}"))

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.kick(reason=reason)
        await ctx.send(embed=success_embed(f"Kicked {member}"))

    @commands.hybrid_command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="Muted"):
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await ctx.send(embed=success_embed(f"Muted {member} for {minutes}m"))

    @commands.hybrid_command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(embed=success_embed(f"Unmuted {member}"))

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="Warned"):
        import aiosqlite, os, time
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (str(ctx.guild.id), str(member.id), reason, int(time.time())))
            await db.commit()
        await ctx.send(embed=base_embed("Warned", f"{member.mention} - {reason}"))

    @commands.hybrid_command(name="quarantine")
    @commands.has_permissions(administrator=True)
    async def quarantine(self, ctx, member: discord.Member, *, reason="Quarantine"):
        from utils.security_checks import quarantine_user
        await quarantine_user(ctx.guild, member, reason)
        await ctx.send(embed=success_embed(f"Quarantined {member}"))

    @commands.hybrid_command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=success_embed("Channel locked 🔒"))

    @commands.hybrid_command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=success_embed("Channel unlocked 🔓"))

    @commands.hybrid_command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 50):
        await ctx.channel.purge(limit=amount+1)
        await ctx.send(embed=success_embed(f"Purged {amount}"), delete_after=2)

async def setup(bot):
    await bot.add_cog(Moderation(bot))