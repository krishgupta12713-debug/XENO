import discord, re, aiohttp, os, aiosqlite, asyncio, io
from discord.ext import commands
from discord import ui
from utils.embeds import base_embed, success_embed, error_embed
from utils.database import set_prefix_db
from utils.security_checks import mod_only, everyone

class StealView(ui.View):
    def __init__(self, emoji_data=None, sticker_data=None, author_id=None):
        super().__init__(timeout=60)
        self.emoji_data = emoji_data
        self.sticker_data = sticker_data
        self.author_id = author_id

    @ui.button(label="Steal This", emoji="🦋", style=discord.ButtonStyle.primary)
    async def steal_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Only command user!", ephemeral=True)
        await interaction.response.defer()
        guild = interaction.guild
        try:
            if self.sticker_data:
                async with aiohttp.ClientSession() as s:
                    async with s.get(self.sticker_data['url']) as r:
                        data = await r.read()
                file = discord.File(fp=io.BytesIO(data), filename=f"{self.sticker_data['name']}.png")
                new_s = await guild.create_sticker(name=self.sticker_data['name'][:30], description="stolen", emoji="🦋", file=file)
                await interaction.followup.send(embed=success_embed(f"Sticker stolen: {new_s.name}"))
            elif self.emoji_data:
                stolen = []
                for name, eid, is_anim, url in self.emoji_data:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url) as r:
                            img = await r.read()
                    new_e = await guild.create_custom_emoji(name=name[:32], image=img)
                    stolen.append(str(new_e))
                if stolen:
                    await interaction.followup.send(embed=success_embed(f"Stolen: {' '.join(stolen)}"))
            for child in self.children: child.disabled = True
            await interaction.edit_original_response(view=self)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(str(e)), ephemeral=True)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="steal", description="Steal emoji/sticker - Owner/Admin/Staff only")
    @mod_only()
    async def steal(self, ctx):
        e = base_embed("Steal Mode 🦋", "Send an **emoji** or **sticker** now (30s)")
        msg = await ctx.send(embed=e)
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and (m.stickers or "<:" in m.content or "<a:" in m.content or m.emojis)
        try:
            user_msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await msg.edit(embed=error_embed("Time out!"))

        emoji_data = []
        sticker_data = None

        if user_msg.stickers:
            sticker = user_msg.stickers[0]
            sticker_data = {"name": sticker.name, "url": sticker.url}
            preview = base_embed("Sticker Found", f"**Name:** {sticker.name}")
            preview.set_thumbnail(url=sticker.url)
            view = StealView(sticker_data=sticker_data, author_id=ctx.author.id)
            await ctx.send(embed=preview, view=view)
        else:
            matches = re.findall(r'<(a)?:(\w+):(\d+)>', user_msg.content)
            if not matches and user_msg.emojis:
                for em in user_msg.emojis:
                    url = f"https://cdn.discordapp.com/emojis/{em.id}.{'gif' if em.animated else 'png'}"
                    emoji_data.append((em.name, em.id, em.animated, url))
            for anim_flag, name, eid in matches:
                url = f"https://cdn.discordapp.com/emojis/{eid}.{'gif' if anim_flag else 'png'}"
                emoji_data.append((name, eid, bool(anim_flag), url))
            if emoji_data:
                desc = "\n".join([f"{'<a:' if a else '<:'}{n}:{eid}> - `{n}`" for n, eid, a, _ in emoji_data])
                preview = base_embed("Emoji Found", desc)
                preview.set_thumbnail(url=emoji_data[0][3])
                view = StealView(emoji_data=emoji_data, author_id=ctx.author.id)
                await ctx.send(embed=preview, view=view)

    @commands.hybrid_command(name="setprefix", description="Set prefix - Mod only")
    @mod_only()
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 3:
            return await ctx.send(embed=error_embed("Prefix max 3 chars"))
        await set_prefix_db(ctx.guild.id, new_prefix)
        await ctx.send(embed=success_embed(f"Prefix set to `{new_prefix}`"))

    # ===== SABKE LIYE OPEN =====
    @commands.hybrid_command(name="serverinfo", description="Server info - Everyone can use")
    @everyone()
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = base_embed(f"{g.name}")
        e.add_field(name="ID", value=f"`{g.id}`", inline=True)
        e.add_field(name="Owner ID", value=f"`{g.owner_id}`", inline=True)
        e.add_field(name="Members", value=f"`{g.member_count}`", inline=True)
        e.add_field(name="Roles", value=f"`{len(g.roles)}`", inline=True)
        e.add_field(name="Channels", value=f"`{len(g.channels)}`", inline=True)
        e.add_field(name="Boosts", value=f"`{g.premium_subscription_count}`", inline=True)
        e.add_field(name="Created", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=False)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="findid", aliases=["lookup","userid"], description="Find user by ID - Everyone")
    @everyone()
    async def findid(self, ctx, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            e = base_embed(f"{user}", f"**ID:** `{user.id}`\n**Bot:** {user.bot}\n**Created:** <t:{int(user.created_at.timestamp())}:R>")
            e.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=e)
        except:
            await ctx.send(embed=error_embed("Invalid ID"))

    @commands.hybrid_command(name="userinfo", description="User info - Everyone")
    @everyone()
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        e = base_embed(f"{member.display_name}")
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="ID", value=f"`{member.id}`", inline=True)
        e.add_field(name="Tag", value=str(member), inline=True)
        e.add_field(name="Joined Discord", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        e.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        e.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        roles = [r.mention for r in member.roles[1:][-10:]]
        e.add_field(name=f"Roles [{len(member.roles)-1}]", value=" ".join(roles) if roles else "None", inline=False)
        await ctx.send(embed=e)

async def setup(bot):
    await bot.add_cog(Utility(bot))
