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
        embed.add_field(name="**Security & Protection**", value=f"```\n{self.current_prefix}antinuke - Advanced server protection\n{self.current_prefix}moderation - Powerful mod tools\n{self.current_prefix}automod - Automated moderation\n```", inline=False)
        embed.add_field(name="**Server Management**", value=f"```\n{self.current_prefix}utility - Essential utilities\n{self.current_prefix}logging - Server activity logs\n{self.current_prefix}autorespond - Custom responses\n{self.current_prefix}giveaway - Host giveaways\n```", inline=False)
        embed.add_field(name="**Engagement & Fun**", value=f"```\n{self.current_prefix}fun - Games & entertainment\n{self.current_prefix}welcomer - Welcome messages\n```", inline=False)
        embed.add_field(name="**Community Features**", value=f"```\n{self.current_prefix}tickets - Support system\n{self.current_prefix}reactionroles - Role management\n```", inline=False)
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
        if self.bot.user in message.mentions:
            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return
            try:
                live_prefix = await get_prefix(message.guild.id)
            except:
                live_prefix = os.getenv("DEFAULT_PREFIX", "?")

            embed = discord.Embed(
                title=f"Hey, I'm {self.bot.user.name}", 
                description=f"**Server Prefix:** `{live_prefix}`\n**Get Started:** Run `{live_prefix}help` to discover all features\n**Support:** Having issues ? Join our [Support Server]({SUPPORT_URL})", 
                color=0x2B2D31
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Powered by XENO Development")
            view = FeatureView(self.bot, live_prefix)
            await message.reply(embed=embed, view=view, mention_author=False)

    # YAHI ADD KIYA - HELP COMMAND BHI ISI ME
    @commands.hybrid_command(name="help", description="Show all bot commands")
    async def help_command(self, ctx):
        try:
            live_prefix = await get_prefix(ctx.guild.id) if ctx.guild else "?"
        except:
            live_prefix = "?"

        embed = discord.Embed(
            title=f"{self.bot.user.name} Help Panel",
            description=(
                f"**Server Prefix:** `{live_prefix}`\n"
                f"**Total Categories:** `4`\n\n"
                "**Security & Protection**\n"
                f"`{live_prefix}antinuke` `{live_prefix}moderation`\n\n"
                "**Server Management**\n"
                f"`{live_prefix}utility` `{live_prefix}logging`\n\n"
                f"Use `{live_prefix}help <command>` for more info"
            ),
            color=0x2B2D31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Current Prefix: {live_prefix} | Powered by XENO Development")
        
        view = HelpView(self.bot, live_prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Mention(bot))
