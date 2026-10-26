import discord
from discord.ext import commands
from utils.embeds import base_embed
import os

SUPPORT_URL = os.getenv("SUPPORT_SERVER", "https://discord.gg/xeno")
PREFIX = os.getenv("PREFIX", "?")

class FeatureView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        
        # Invite Link Auto Banega Bot ID se
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        
        # Invite Button - FIXED TARIKA
        self.add_item(discord.ui.Button(
            label="Invite",
            style=discord.ButtonStyle.link,
            url=invite_url,
            emoji="🔗"
        ))

    @discord.ui.button(label="Features", style=discord.ButtonStyle.secondary)
    async def features_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="XENO - All Features",
            color=0x2B2D31
        )
        embed.add_field(name="**Security & Protection**", value="```\nAntinuke - Advanced server protection\nModeration - Powerful mod tools\nAutomod - Automated moderation\n```", inline=False)
        embed.add_field(name="**Server Management**", value="```\nUtility - Essential utilities\nLogging - Server activity logs\nAutoResponder - Custom responses\nGiveaway - Host giveaways\n```", inline=False)
        embed.add_field(name="**Engagement & Fun**", value="```\nFun - Games & entertainment\nMusic - Music player\nWelcomer - Welcome messages\n```", inline=False)
        embed.add_field(name="**Community Features**", value="```\nTickets - Support system\nReaction Roles - Role management\nVoiceMaster - Temp Voice channels\nLeveling - Chat levels\n```", inline=False)
        embed.set_footer(text="Powered by XENO Development")
        await interaction.response.edit_message(embed=embed, view=self)

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

            embed = discord.Embed(
                title=f"Hey, I'm {self.bot.user.name}",
                description=f"**Server Prefix:** `{PREFIX}`\n**Get Started:** Run `{PREFIX}help` to discover all features\n**Support:** Having issues ? Join our [Support Server]({SUPPORT_URL})",
                color=0x2B2D31
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Powered by XENO Development")

            view = FeatureView(self.bot)
            await message.reply(embed=embed, view=view, mention_author=False)

async def setup(bot):
    await bot.add_cog(Mention(bot))
