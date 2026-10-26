import discord
from discord.ext import commands
import aiosqlite, os, time
from utils.embeds import base_embed, success_embed, error_embed
from utils.security_checks import everyone

COLOR = 0x2B2D31
AFK_COLOR = 0x5865F2

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="afk", description="Set yourself AFK - Everyone")
    @everyone()
    async def afk(self, ctx, *, reason: str = "AFK"):
        # Aesthetic embed for setting AFK
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS afk (guild_id TEXT, user_id TEXT, reason TEXT, time INTEGER, PRIMARY KEY (guild_id, user_id))")
            await db.execute("INSERT OR REPLACE INTO afk VALUES (?,?,?,?)", (str(ctx.guild.id), str(ctx.author.id), reason, int(time.time())))
            await db.commit()
        
        embed = discord.Embed(
            color=AFK_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{ctx.author.display_name} is now AFK", icon_url=ctx.author.display_avatar.url)
        embed.description = f"```\n💤 Reason: {reason}\n```"
        embed.add_field(name="From Now", value=f"All mentions will get your AFK message", inline=False)
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1108803442702646834.gif") # moon emoji gif
        embed.set_footer(text=f"Use any message to remove AFK • {ctx.guild.name}")

        # Try to set nickname with [AFK]
        try:
            if "[AFK]" not in ctx.author.display_name:
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except:
            pass

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: 
            return
        
        async with aiosqlite.connect(os.getenv("DATABASE_PATH","database.db")) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS afk (guild_id TEXT, user_id TEXT, reason TEXT, time INTEGER, PRIMARY KEY (guild_id, user_id))")
            
            # If author was AFK and now sends message -> Remove AFK
            async with db.execute("SELECT reason, time FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(message.author.id))) as cur:
                data = await cur.fetchone()
                if data:
                    await db.execute("DELETE FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(message.author.id)))
                    await db.commit()

                    # Aesthetic Welcome Back
                    embed = discord.Embed(
                        color=0x57F287,
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_author(name=f"Welcome Back, {message.author.display_name}!", icon_url=message.author.display_avatar.url)
                    embed.description = f"You were AFK for <t:{data[1]}:R>\n```\nReason was: {data[0]}\n```"
                    embed.set_footer(text=f"AFK Removed • {message.guild.name}")

                    # Try to remove [AFK] from nick
                    try:
                        if message.author.display_name.startswith("[AFK] "):
                            await message.author.edit(nick=message.author.display_name[6:])
                    except:
                        pass

                    try:
                        await message.channel.send(embed=embed, delete_after=10)
                    except:
                        pass

            # If someone mentions AFK user
            if message.mentions:
                for user in message.mentions:
                    if user.id == message.author.id:
                        continue
                    async with db.execute("SELECT reason, time FROM afk WHERE guild_id=? AND user_id=?", (str(message.guild.id), str(user.id))) as cur:
                        afk_data = await cur.fetchone()
                        if afk_data:
                            reason, afk_time = afk_data
                            
                            embed = discord.Embed(
                                color=COLOR,
                                timestamp=discord.utils.utcnow()
                            )
                            embed.set_author(name=f"{user.display_name} is AFK 💤", icon_url=user.display_avatar.url)
                            embed.description = f"```\n{reason}\n```"
                            embed.add_field(name="AFK Since", value=f"<t:{afk_time}:R> • <t:{afk_time}:F>", inline=False)
                            embed.set_footer(text=f"They will reply when they are back • {message.guild.name}")
                            
                            try:
                                await message.channel.send(embed=embed, delete_after=12)
                            except:
                                pass
                            break # Only show one AFK per message to avoid spam

async def setup(bot):
    await bot.add_cog(AFK(bot))
