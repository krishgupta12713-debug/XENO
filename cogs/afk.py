import discord
from discord.ext import commands
import aiosqlite, os, time
from utils.embeds import base_embed, success_embed
from utils.security_checks import everyone

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="afk", description="Set AFK - Everyone")
    @everyone()
    async def afk(self, ctx, *, reason: str = "AFK"):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR REPLACE INTO afk VALUES (?,?,?,?)", (str(ctx.guild.id), str(ctx.author.id), reason, int(time.time())))
            await db.commit()
        await ctx.send(embed=success_embed(f"{ctx.author.display_name} is now AFK: {reason}"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT 1 FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(message.author.id))) as cur:
                if await cur.fetchone():
                    await db.execute("DELETE FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(message.author.id)))
                    await db.commit()
                    try:
                        await message.channel.send(embed=base_embed("Welcome Back", f"{message.author.mention} is back!"), delete_after=5)
                    except: pass
            if message.mentions:
                for user in message.mentions:
                    async with db.execute("SELECT reason, time FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(user.id))) as cur:
                        data = await cur.fetchone()
                        if data:
                            await message.channel.send(embed=base_embed("💤 AFK", f"**{user.display_name}** is AFK: {data[0]}\n> <t:{data[1]}:R>"), delete_after=10)

async def setup(bot):
    await bot.add_cog(AFK(bot))
