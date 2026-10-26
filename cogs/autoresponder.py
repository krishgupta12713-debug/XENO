import discord
from discord.ext import commands
import aiosqlite, os
from utils.embeds import base_embed, success_embed, error_embed
from utils.security_checks import everyone
from typing import Literal

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        # Command hai toh autorespond mat bhejo
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS autorespond (guild_id TEXT, trigger TEXT, response TEXT, PRIMARY KEY (guild_id, trigger))")
            async with db.execute("SELECT trigger, response FROM autorespond WHERE guild_id=?", (str(message.guild.id),)) as cur:
                rows = await cur.fetchall()
                for trigger, response in rows:
                    if trigger.lower() in message.content.lower():
                        try:
                            await message.channel.send(response)
                            break
                        except: pass

    @commands.hybrid_command(name="autorespond", description="Manage auto responses - Everyone")
    @everyone()
    async def autorespond(self, ctx, 
                          action: Literal["add", "remove", "list"], 
                          trigger: str = None, 
                          response: str = None):
        
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS autorespond (guild_id TEXT, trigger TEXT, response TEXT, PRIMARY KEY (guild_id, trigger))")
            
            if action == "add":
                if not trigger or not response:
                    return await ctx.send(embed=error_embed("Use: `?autorespond add trigger response` ya `/autorespond add trigger:hi response:hello`"))
                await db.execute("INSERT OR REPLACE INTO autorespond VALUES (?,?,?)", (str(ctx.guild.id), trigger.lower(), response))
                await db.commit()
                await ctx.send(embed=success_embed(f"Added ✅\n`{trigger}` -> {response[:100]}"))

            elif action == "remove":
                if not trigger:
                    return await ctx.send(embed=error_embed("Trigger de! `?autorespond remove hi`"))
                await db.execute("DELETE FROM autorespond WHERE guild_id=? AND trigger=?", (str(ctx.guild.id), trigger.lower()))
                await db.commit()
                await ctx.send(embed=success_embed(f"Removed ✅ `{trigger}`"))

            elif action == "list":
                async with db.execute("SELECT trigger, response FROM autorespond WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                    rows = await cur.fetchall()
                if not rows:
                    return await ctx.send(embed=base_embed("AutoRespond", "No triggers set"))
                desc = "\n".join([f"`{r[0]}` -> {r[1][:80]}" for r in rows])
                await ctx.send(embed=base_embed(f"AutoRespond List - {len(rows)}", desc[:2000]))

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))
