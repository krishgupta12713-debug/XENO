import discord
from discord.ext import commands
import os
from utils.database import get_prefix

SUPPORT_URL = os.getenv("SUPPORT_SERVER", "https://discord.gg/xeno")

class FeatureView(discord.ui.View):
    def __init__(self, bot, current_prefix: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.current_prefix = current_prefix
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite", style=discord.ButtonStyle.link, url=invite_url, emoji="🔗"))

    @discord.ui.button(label="Features", style=discord.ButtonStyle.secondary, emoji="📜")
    async def features_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="XENO - All Features", color=0x2B2D31)
        embed.description = f"Current Prefix: `{self.current_prefix}` | Use `{self.current_prefix}help <command>`"
        embed.add_field(name="**Security**", value=f"```\n{self.current_prefix}antinuke\n{self.current_prefix}moderation\n```", inline=False)
        embed.set_footer(text="Powered by XENO Development")
        await interaction.response.edit_message(embed=embed, view=self)

class HelpView(discord.ui.View):
    def __init__(self, bot, current_prefix):
        super().__init__(timeout=120)
        self.current_prefix = current_prefix
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite", style=discord.ButtonStyle.link, url=invite_url))
        self.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.link, url=SUPPORT_URL))

class Mention(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # ==== NAYA FIX: Sirf prefix akela hai toh ignore ====
        try:
            live_prefix = await get_prefix(message.guild.id)
        except:
            live_prefix = os.getenv("DEFAULT_PREFIX", "?")

        # Agar message sirf "?" ya "!" ya prefix akela hai toh kuch mat karo
        if message.content.strip() == live_prefix:
            return
        
        if message.content.strip() == f"<@{self.bot.user.id}>" or message.content.strip() == f"<@!{self.bot.user.id}>":
            pass # Isko aane do - ye proper mention hai
        elif message.reference and not message.mentions:
            return # Drag/reply ignore

        # Proper mention check
        bot_mention_1 = f"<@{self.bot.user.id}>"
        bot_mention_2 = f"<@!{self.bot.user.id}>"
        if bot_mention_1 not in message.content and bot_mention_2 not in message.content and self.bot.user not in message.mentions:
            return

        # Agar valid command hai (?help) toh mention embed mat bhejo
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        embed = discord.Embed(
            title=f"Hey, I'm {self.bot.user.name}", 
            description=f"**Server Prefix:** `{live_prefix}`\n**Get Started:** Run `{live_prefix}help`\n**Support:** [Support Server]({SUPPORT_URL})", 
            color=0x2B2D31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Powered by XENO Development")
        view = FeatureView(self.bot, live_prefix)
        await message.reply(embed=embed, view=view, mention_author=False)

    @commands.hybrid_command(name="help", description="Show all bot commands")
    async def help_command(self, ctx):
        try:
            live_prefix = await get_prefix(ctx.guild.id) if ctx.guild else "?"
        except:
            live_prefix = "?"
        embed = discord.Embed(
            title=f"{self.bot.user.name} Help Panel",
            description=f"**Server Prefix:** `{live_prefix}`\n\n`{live_prefix}antinuke` `{live_prefix}moderation`\n`{live_prefix}utility` `{live_prefix}logging`\n\nUse `{live_prefix}help <command>`",
            color=0x2B2D31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Current Prefix: {live_prefix} | Powered by XENO")
        view = HelpView(self.bot, live_prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Mention(bot))
