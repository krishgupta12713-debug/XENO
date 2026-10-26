import discord
from discord.ext import commands
import aiosqlite, os, json
from utils.embeds import base_embed, success_embed, error_embed
from utils.security_checks import mod_only, everyone

class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="greet", description="Setup greetings - Mod only")
    @mod_only()
    async def greet(self, ctx):
        if ctx.invoked_subcommand is None:
            e = base_embed("Greet Setup - Variables",
                "**Variables:**\n`{user}` = mention\n`{username}` = name\n`{server}` = server name\n`{count}` = member count\n\n"
                "**Commands:**\n`?greet welcome #ch message` - Normal text\n`?greet welcome_embed #ch` - Embed builder\n`?greet goodbye #ch message`\n`?greet booster #ch message`\n`?greet show`\n`?greet disable welcome`")
            await ctx.send(embed=e)

    def parse_vars(self, text, member):
        return text.format(
            user=member.mention, 
            username=str(member),
            server=member.guild.name, 
            count=member.guild.member_count
        ).replace("\\n", "\n")

    # --- NORMAL TEXT WELCOME ---
    @greet.command(name="welcome", description="Set normal welcome text")
    @mod_only()
    async def welcome(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        channel = channel or ctx.channel
        msg = message or "Welcome {user} to **{server}**! You are {count}th member 🎉"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET welcome_channel=?, welcome_msg=?, welcome_embed=NULL WHERE guild_id=?", (str(channel.id), msg, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Welcome TEXT set in {channel.mention}"))

    # --- EMBED WELCOME ---
    @greet.command(name="welcome_embed", description="Set welcome as fancy embed")
    @mod_only()
    async def welcome_embed(self, ctx, channel: discord.TextChannel = None, title: str = None, *, description: str = None):
        channel = channel or ctx.channel
        if not title or not description:
            return await ctx.send(embed=error_embed("Usage: `?greet welcome_embed #channel Title \\n Description with {user}`\nExample: `?greet welcome_embed #welcome Welcome to server \\n Hello {user} you are {count}th member`"))
        
        embed_data = json.dumps({"title": title, "desc": description})
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET welcome_channel=?, welcome_embed=?, welcome_msg=NULL WHERE guild_id=?", (str(channel.id), embed_data, str(ctx.guild.id)))
            await db.commit()
        
        # Preview
        e = base_embed(self.parse_vars(title, ctx.author), self.parse_vars(description, ctx.author))
        e.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(content=f"✅ Embed Welcome set in {channel.mention} - Preview:", embed=e)

    @greet.command(name="goodbye", description="Setup goodbye - Mod only")
    @mod_only()
    async def goodbye(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        channel = channel or ctx.channel
        msg = message or "Goodbye {user}, we will miss you! 😢"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET goodbye_channel=?, goodbye_msg=? WHERE guild_id=?", (str(channel.id), msg, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Goodbye set in {channel.mention}"))

    @greet.command(name="booster", description="Setup booster - Mod only")
    @mod_only()
    async def booster(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        channel = channel or ctx.channel
        msg = message or "Thank you {user} for boosting **{server}**! 🚀"
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("INSERT OR IGNORE INTO greet_config (guild_id) VALUES (?)", (str(ctx.guild.id),))
            await db.execute("UPDATE greet_config SET booster_channel=?, booster_msg=? WHERE guild_id=?", (str(channel.id), msg, str(ctx.guild.id)))
            await db.commit()
        await ctx.send(embed=success_embed(f"Booster set in {channel.mention}"))

    @greet.command(name="disable")
    @mod_only()
    async def disable(self, ctx, type: str):
        type = type.lower()
        col = {"welcome":"welcome_channel","goodbye":"goodbye_channel","booster":"booster_channel"}.get(type)
        if not col:
            return await ctx.send(embed=error_embed("Use: welcome / goodbye / booster"))
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute(f"UPDATE greet_config SET {col}=NULL WHERE guild_id=?", (str(ctx.guild.id),))
            await db.commit()
        await ctx.send(embed=success_embed(f"{type} disabled"))

    @greet.command(name="show")
    @mod_only()
    async def show(self, ctx):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT welcome_channel, welcome_msg, welcome_embed, goodbye_channel, goodbye_msg, booster_channel, booster_msg FROM greet_config WHERE guild_id=?", (str(ctx.guild.id),)) as cur:
                row = await cur.fetchone()
        if not row or not any(row):
            return await ctx.send(embed=base_embed("Greet Config", "Nothing set"))
        e = base_embed(f"Greet Config")
        e.add_field(name="Welcome", value=f"<#{row[0]}> - {'Embed' if row[2] else row[1][:100]}" if row[0] else "Not set", inline=False)
        e.add_field(name="Goodbye", value=f"<#{row[3]}>" if row[3] else "Not set", inline=True)
        e.add_field(name="Booster", value=f"<#{row[5]}>" if row[5] else "Not set", inline=True)
        await ctx.send(embed=e)

    # LISTENERS
    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT welcome_channel, welcome_msg, welcome_embed FROM greet_config WHERE guild_id=?", (str(member.guild.id),)) as cur:
                row = await cur.fetchone()
        if not row or not row[0]: return
        ch = member.guild.get_channel(int(row[0]))
        if not ch: return
        try:
            if row[2]: # Embed mode
                data = json.loads(row[2])
                title = self.parse_vars(data["title"], member)
                desc = self.parse_vars(data["desc"], member)
                e = base_embed(title, desc)
                e.set_thumbnail(url=member.display_avatar.url)
                e.set_footer(text=f"You are {member.guild.member_count}th member")
                await ch.send(content=member.mention, embed=e)
            else:
                msg = self.parse_vars(row[1], member)
                e = base_embed("Welcome 🎉", msg)
                e.set_thumbnail(url=member.display_avatar.url)
                await ch.send(content=member.mention, embed=e)
        except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            async with db.execute("SELECT goodbye_channel, goodbye_msg FROM greet_config WHERE guild_id=?", (str(member.guild.id),)) as cur:
                row = await cur.fetchone()
        if row and row[0]:
            ch = member.guild.get_channel(int(row[0]))
            if ch:
                try: await ch.send(embed=base_embed("Goodbye", self.parse_vars(row[1], member)))
                except: pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.premium_since and after.premium_since:
            async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
                async with db.execute("SELECT booster_channel, booster_msg FROM greet_config WHERE guild_id=?", (str(after.guild.id),)) as cur:
                    row = await cur.fetchone()
            if row and row[0]:
                ch = after.guild.get_channel(int(row[0]))
                if ch:
                    try:
                        msg = row[1].format(user=after.mention, server=after.guild.name)
                        await ch.send(embed=base_embed("Server Boost 🚀", msg))
                    except: pass

async def setup(bot):
    await bot.add_cog(Greeting(bot))
