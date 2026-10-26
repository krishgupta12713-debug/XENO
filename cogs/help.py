import discord
from discord.ext import commands
from utils.database import get_prefix
import os

SUPPORT_URL = os.getenv("SUPPORT_SERVER", "https://discord.gg/xeno")

class HelpSelect(discord.ui.Select):
    def __init__(self, current_prefix):
        self.current_prefix = current_prefix
        options = [
            discord.SelectOption(label="Moderation", description=f"Use {current_prefix}ban, {current_prefix}kick", emoji="🔨"),
            discord.SelectOption(label="Security", description="Antinuke & protection", emoji="🛡️"),
            discord.SelectOption(label="Utility", description=f"Prefix, info commands", emoji="🛠️"),
            discord.SelectOption(label="Welcomer", description="Welcome system", emoji="👋"),
            discord.SelectOption(label="Logging", description="Server logs", emoji="📜"),
        ]
        super().__init__(placeholder=f"Current Prefix: {current_prefix} | Select category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{self.values[0]} Commands",
            description=f"Use `{self.current_prefix}help <command>` for more info\nCurrent prefix: `{self.current_prefix}`",
            color=0x2B2D31
        )
        # Yaha apne commands add kar de category wise
        if self.values[0] == "Moderation":
            embed.add_field(name="Commands", value=f"```{self.current_prefix}ban, {self.current_prefix}kick, {self.current_prefix}mute, {self.current_prefix}purge```", inline=False)
        elif self.values[0] == "Utility":
            embed.add_field(name="Commands", value=f"```{self.current_prefix}prefix, {self.current_prefix}setprefix, {self.current_prefix}ping, {self.current_prefix}userinfo```", inline=False)
        
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, current_prefix):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(current_prefix))
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite", style=discord.ButtonStyle.link, url=invite_url))

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show all commands")
    async def help_command(self, ctx):
        # LIVE PREFIX - Yahi main fix hai
        live_prefix = await get_prefix(ctx.guild.id) if ctx.guild else "?"
        
        embed = discord.Embed(
            title=f"{self.bot.user.name} Help Panel",
            description=(
                f"**Server Prefix:** `{live_prefix}`\n"
                f"**Use:** `{live_prefix}help` or `/help`\n\n"
                f"**Moderation**\n`{live_prefix}ban` `{live_prefix}kick` `{live_prefix}mute`\n\n"
                f"**Prefix**\n`{live_prefix}setprefix` `{live_prefix}prefix`\n\n"
                f"**Utility**\n`{live_prefix}ping` `{live_prefix}userinfo`\n"
            ),
            color=0x2B2D31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Current Prefix: {live_prefix} | Powered by XENO")
        
        view = HelpView(self.bot, live_prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
