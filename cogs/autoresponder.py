import discord
from discord.ext import commands
import aiosqlite, os
from utils.embeds import base_embed, success_embed
from utils.security_checks import everyone

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT trigger, response FROM autorespond WHERE guild_id=?", (str(message.guild.id),)) as cur:
                rows = await cur.fetchall()
                for trigger, response in rows:
                    if trigger.lower() in message.content.lower():
                        try:
                            await message.channel.send(response)
                            break
                        except: pass

    @commands.hybrid_command(name="ar_add", description="Add auto respond - Everyone")
    @everyone()
    async def ar_add(self, ctx, trigger: str, *, response: str):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR REPLACE INTO autorespond VALUES (?,?,?)", (str(ctx.guild.id), trigger.lower(), response))
            await db.commit()
        await ctx.send(embed=success_embed(f"Added: `{trigger}` -> {response[:100]}"))

    @commands.hybrid_command(name="ar_remove", description="Remove auto respond - Everyone")
    @everyone()
    async def ar_remove(self, ctx, trigger: str):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("DELETE FROM autorespond WHERE guild_id=? AND trigger=?", (str(ctx.guild.id), trigger.lower()))
            await db.commit()
        await ctx.send(embed=success_embed(f"Removed: `{trigger}`"))

    @commands.hybrid_command(name="ar_list", description="List auto responds - Everyone")
    @everyone()
    async def ar_list(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT trigger, response FROM autorespond WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send(embed=base_embed("AutoRespond", "No triggers set"))
        desc = "\n".join([f"`{r[0]}` -> {r[1][:80]}" for r in rows])
        await ctx.send(embed=base_embed("AutoRespond List", desc[:2000]))

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))
