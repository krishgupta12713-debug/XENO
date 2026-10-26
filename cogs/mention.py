import discord
from discord.ext import commands
from utils.embeds import base_embed
import os

SUPPORT_URL = os.getenv("SUPPORT_SERVER", "https://discord.gg/xeno") # .env me SUPPORT_SERVER link daal de
PREFIX = os.getenv("PREFIX", "?")

class FeatureView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Features", style=discord.ButtonStyle.secondary)
    async def features_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Yaha tere saare features dikhenge - isko apne hisab se edit kar sakta hai
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

    @discord.ui.button(label="Support Server", style=discord.ButtonStyle.secondary, url=SUPPORT_URL)
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass # Link button ko callback nahi chahiye

class Mention(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            # Agar message sirf mention hai (ya mention ke saath kuch bhi)
            # Aur command nahi hai
            if message.content.strip() in [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]:
                pass # allow
            elif not message.content.strip().startswith(f"<@{self.bot.user.id}>") and not message.content.strip().startswith(f"<@!{self.bot.user.id}>"):
                # Agar beech me mention hai to bhi dikhana hai? Zynrax beech me bhi dikhata hai
                # Agar tu chahe sirf start pe ho to upar wala condition use kar
                pass

            # Avoid replying to every message where bot is mentioned with other text + command
            # Sirf jab prefix nahi hai tab reply karo
            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return # Ye command hai, ignore

            embed = discord.Embed(
                title=f"Hey, I'm {self.bot.user.name}",
                description=f"**Server Prefix:** `{PREFIX}`\n**Get Started:** Run `{PREFIX}help` to discover all features\n**Support:** Having issues ? Join our [Support Server]({SUPPORT_URL})",
                color=0x2B2D31
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Powered by XENO Development")

            view = FeatureView()
            # Support link ko dynamic update
            view.children[1].url = SUPPORT_URL

            await message.reply(embed=embed, view=view, mention_author=False)

async def setup(bot):
    await bot.add_cog(Mention(bot))
