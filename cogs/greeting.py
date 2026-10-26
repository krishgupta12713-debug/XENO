import discord
from discord.ext import commands
import aiosqlite, os
from utils.embeds import base_embed, success_embed, error_embed

class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="greet", description="Setup greetings")
    @commands.has_permissions(administrator=True)
    async def greet(self, ctx): pass

    @greet.command(name="welcome", description="Setup welcome")
    async def welcome(self, ctx, channel: discord.TextChannel = None, message: str = None):
        channel = channel or ctx.channel
        # {user} {server} {count}
        msg = message or "Welcome {user} to **{server}**! You are {count}th member 🎉"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR REPLACE INTO greet_config (guild_id, welcome_channel, welcome_msg) VALUES (?,?,?)", (str(ctx.guild.id), str(channel.id), msg))
            await db.commit()
        await ctx.send(embed=success_embed(f"Welcome set in {channel.mention}\n`{msg}`"))

    @greet.command(name="goodbye", description="Setup goodbye")
    async def goodbye(self, ctx, channel: discord.TextChannel = None, message: str = None):
        channel = channel or ctx.channel
        msg = message or "Goodbye {user}, we will miss you! 😢"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET goodbye_channel=?, goodbye_msg=? WHERE guild_id=?", (str(channel.id), msg, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Goodbye set in {channel.mention}"))

    @greet.command(name="booster", description="Setup booster message")
    async def booster(self, ctx, channel: discord.TextChannel = None, message: str = None):
        channel = channel or ctx.channel
        msg = message or "Thank you {user} for boosting **{server}**! 🚀"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET booster_channel=?, booster_msg=? WHERE guild_id=?", (str(channel.id), msg, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Booster message set in {channel.mention}"))

    @greet.command(name="disable", description="Disable greeting")
    async def disable(self, ctx, type: str):
        type = type.lower()
        col = {"welcome":"welcome_channel","goodbye":"goodbye_channel","booster":"booster_channel"}.get(type)
        if not col:
            return await ctx.send(embed=error_embed("Use: welcome / goodbye / booster"))
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute(f"UPDATE greet_config SET {col}=NULL WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        await ctx.send(embed=success_embed(f"{type} disabled"))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT welcome_channel, welcome_msg FROM greet_config WHERE guild_id=?", (str(member.guild.id),)) as cur:
                row = await cur.fetchone()
        if row and row[0]:
            ch = member.guild.get_channel(int(row[0]))
            if ch:
                msg = row[1].format(user=member.mention, server=member.guild.name, count=member.guild.member_count, username=str(member))
                e = base_embed("Welcome", msg)
                e.set_thumbnail(url=member.display_avatar.url)
                try: await ch.send(content=member.mention, embed=e)
                except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT goodbye_channel, goodbye_msg FROM greet_config WHERE guild_id=?", (str(member.guild.id),)) as cur:
                row = await cur.fetchone()
        if row and row[0]:
            ch = member.guild.get_channel(int(row[0]))
            if ch:
                msg = row[1].format(user=str(member), server=member.guild.name)
                try: await ch.send(embed=base_embed("Goodbye", msg))
                except: pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.premium_since and after.premium_since: # Booster
            async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
                async with db.execute("SELECT booster_channel, booster_msg FROM greet_config WHERE guild_id=?", (str(after.guild.id),)) as cur:
                    row = await cur.fetchone()
            if row and row[0]:
                ch = after.guild.get_channel(int(row[0]))
                if ch:
                    msg = row[1].format(user=after.mention, server=after.guild.name)
                    try: await ch.send(embed=base_embed("Server Boost 🚀", msg))
                    except: pass

async def setup(bot):
    await bot.add_cog(Greeting(bot))
