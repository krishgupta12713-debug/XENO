import discord
from discord.ext import commands
from utils.database import get_prefix
import os

SUPPORT_URL = os.getenv("SUPPORT_SERVER", "https://discord.gg/xeno")

# Saare commands ka data - Yahi Features button me bhi dikhega
COMMANDS_DATA = {
    "Security & Protection": {
        "emoji": "🛡️",
        "desc": "Advanced server security",
        "commands": [
            "`antinuke` - Enable/disable antinuke system",
            "`whitelist` - Manage whitelisted users",
            "`panel` - Security control panel"
        ]
    },
    "Moderation": {
        "emoji": "🔨",
        "desc": "Powerful mod tools",
        "commands": [
            "`ban`, `unban`, `kick`, `mute`, `unmute`",
            "`warn`, `clearwarn`, `purge`, `nuke`",
            "`lock`, `unlock`, `slowmode`, `role`"
        ]
    },
    "Automod": {
        "emoji": "🤖",
        "desc": "Automated moderation",
        "commands": [
            "`automod` - Setup automod",
            "`anti-invite`, `anti-link`, `anti-spam`",
            "`anti-massmention`"
        ]
    },
    "Utility": {
        "emoji": "🛠️",
        "desc": "Essential utilities",
        "commands": [
            "`prefix` - Change server prefix",
            "`afk`, `avatar`, `userinfo`, `serverinfo`",
            "`ping`, `uptime`, `invite`"
        ]
    },
    "Welcomer": {
        "emoji": "👋",
        "desc": "Welcome & Goodbye messages",
        "commands": [
            "`welcome` - Setup welcome system",
            "`goodbye` - Setup goodbye",
            "`booster` - Booster messages",
            "`autorole` - Auto role on join"
        ]
    },
    "Logging": {
        "emoji": "📜",
        "desc": "Server activity logs",
        "commands": [
            "`logging` - Setup all logs",
            "`setlog` - Set log channel"
        ]
    },
    "Fun & Giveaway": {
        "emoji": "🎉",
        "desc": "Games & entertainment",
        "commands": [
            "`giveaway` - Host giveaways",
            "`autorespond` - Custom auto replies",
            "`8ball`, `meme`, `joke`"
        ]
    }
}

class HelpSelect(discord.ui.Select):
    def __init__(self, current_prefix):
        self.current_prefix = current_prefix
        options = []
        for category, data in COMMANDS_DATA.items():
            options.append(discord.SelectOption(
                label=category,
                description=data["desc"],
                emoji=data["emoji"]
            ))
        
        super().__init__(placeholder="Select a category...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        data = COMMANDS_DATA[category]
        
        embed = discord.Embed(
            title=f"{data['emoji']} {category}",
            description=f"**Prefix:** `{self.current_prefix}` | Use `{self.current_prefix}help <command>` for details\n\n" + "\n".join(data["commands"]),
            color=0x2B2D31
        )
        embed.set_footer(text=f"Requested by {interaction.user} | Powered by XENO Development", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, current_prefix):
        super().__init__(timeout=120)
        self.bot = bot
        self.current_prefix = current_prefix
        self.add_item(HelpSelect(current_prefix))
        
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite", style=discord.ButtonStyle.link, url=invite_url, emoji="🔗"))
        self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=SUPPORT_URL, emoji="💬"))

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show all bot commands")
    async def help_command(self, ctx: commands.Context):
        # Live prefix lao
        try:
            live_prefix = await get_prefix(ctx.guild.id) if ctx.guild else "?"
        except:
            live_prefix = "?"

        # Main Help Embed - Zynrax Style
        embed = discord.Embed(
            title=f"{self.bot.user.name} Help Panel",
            description=(
                f"**Server Prefix:** `{live_prefix}`\n"
                f"**Total Commands:** `{len(COMMANDS_DATA)} categories`\n"
                f"**Get Started:** Select a category below\n\n"
                "**__Security & Protection__**\nAntinuke - Advanced server protection\nModeration - Powerful mod tools\nAutomod - Automated moderation\n\n"
                "**__Server Management__**\nUtility - Essential utilities\nLogging - Server activity logs\nAutoResponder - Custom responses\n\n"
                "**__Community__**\nWelcomer - Welcome messages\nFun - Games & entertainment\nGiveaway - Host giveaways\n"
            ),
            color=0x2B2D31
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Powered by XENO Development")
        
        view = HelpView(self.bot, live_prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
