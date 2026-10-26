import discord, re, aiohttp, os, aiosqlite, asyncio, io
from discord.ext import commands
from discord import ui
from utils.embeds import base_embed, success_embed, error_embed
from utils.database import set_prefix_db
import datetime

COLOR = 0x2b2d31

# --- STEAL BUTTON VIEW ---
class StealView(ui.View):
    def __init__(self, emoji_data=None, sticker_data=None, author_id=None):
        super().__init__(timeout=60)
        self.emoji_data = emoji_data # list of (name, id, is_animated, url)
        self.sticker_data = sticker_data # dict with name, url
        self.author_id = author_id

    @ui.button(label="Steal This", emoji="🦋", style=discord.ButtonStyle.primary)
    async def steal_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Only command user can steal!", ephemeral=True)

        await interaction.response.defer()

        guild = interaction.guild
        if self.sticker_data:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(self.sticker_data['url']) as r:
                        data = await r.read()
                file = discord.File(fp=io.BytesIO(data), filename=f"{self.sticker_data['name']}.png")
                new_s = await guild.create_sticker(name=self.sticker_data['name'][:30], description="stolen", emoji="🦋", file=file)
                await interaction.followup.send(embed=success_embed(f"Sticker stolen: {new_s.name} - {new_s.url}"))
                for child in self.children: child.disabled = True
                await interaction.edit_original_response(view=self)
            except Exception as e:
                await interaction.followup.send(embed=error_embed(str(e)), ephemeral=True)

        elif self.emoji_data:
            stolen = []
            for name, eid, is_anim, url in self.emoji_data:
                try:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url) as r:
                            img = await r.read()
                    new_e = await guild.create_custom_emoji(name=name[:32], image=img)
                    stolen.append(str(new_e))
                except Exception as e:
                    await interaction.followup.send(embed=error_embed(f"{name}: {e}"), ephemeral=True)
            if stolen:
                await interaction.followup.send(embed=success_embed(f"Stolen: {' '.join(stolen)}"))
                for child in self.children: child.disabled = True
                await interaction.edit_original_response(view=self)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="steal", description="Steal emoji/sticker - Then send emoji/sticker")
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def steal(self, ctx):
        e = base_embed("Steal Mode 🦋", "Send an **emoji**, **sticker**, or **custom emoji** now (30s)\n\n> I will show you a button to steal it instantly!")
        e.set_footer(text=f"Requested by {ctx.author.display_name}")
        msg = await ctx.send(embed=e)

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and (m.stickers or "<:" in m.content or "<a:" in m.content or m.emojis)

        try:
            user_msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await msg.edit(embed=error_embed("Time out! No emoji/sticker sent."))

        # Parse
        emoji_data = []
        sticker_data = None

        if user_msg.stickers:
            sticker = user_msg.stickers[0]
            sticker_data = {"name": sticker.name, "url": sticker.url}
            preview = base_embed("Sticker Found", f"**Name:** {sticker.name}\nClick below to steal!")
            preview.set_thumbnail(url=sticker.url)
            view = StealView(sticker_data=sticker_data, author_id=ctx.author.id)
            await ctx.send(embed=preview, view=view)

        else:
            # Emoji from content
            content = user_msg.content
            matches = re.findall(r'<(a)?:(\w+):(\d+)>', content)
            if not matches:
                # Check if default unicode emojis - try custom via message emojis attr
                if user_msg.emojis:
                    for em in user_msg.emojis:
                        is_anim = em.animated
                        url = f"https://cdn.discordapp.com/emojis/{em.id}.{'gif' if is_anim else 'png'}"
                        emoji_data.append((em.name, em.id, is_anim, url))
                else:
                    return await ctx.send(embed=error_embed("No custom emoji/sticker found! Send a custom one."))

            for anim_flag, name, eid in matches:
                is_anim = bool(anim_flag)
                url = f"https://cdn.discordapp.com/emojis/{eid}.{'gif' if is_anim else 'png'}"
                emoji_data.append((name, eid, is_anim, url))

            if emoji_data:
                desc = "\n".join([f"{'<a:' if a else '<:'}{n}:{eid}> - `{n}`" for n, eid, a, _ in emoji_data])
                preview = base_embed("Emoji Found", desc)
                preview.set_thumbnail(url=emoji_data[0][3])
                view = StealView(emoji_data=emoji_data, author_id=ctx.author.id)
                await ctx.send(embed=preview, view=view)

    @commands.hybrid_command(name="setprefix", description="Set custom prefix")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 3:
            return await ctx.send(embed=error_embed("Prefix max 3 chars"))
        await set_prefix_db(ctx.guild.id, new_prefix)
        await ctx.send(embed=success_embed(f"Prefix set to `{new_prefix}`"))

    @commands.hybrid_command(name="serverinfo", description="Server info - Owner ID only + Roles")
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = base_embed(f"{g.name}")
        e.add_field(name="ID", value=f"`{g.id}`", inline=True)
        e.add_field(name="Owner ID", value=f"`{g.owner_id}`", inline=True) # ONLY ID
        e.add_field(name="Members", value=f"`{g.member_count}`", inline=True)
        e.add_field(name="Roles", value=f"`{len(g.roles)} roles`", inline=True) # Added roles count
        e.add_field(name="Channels", value=f"`{len(g.channels)}`", inline=True)
        e.add_field(name="Boosts", value=f"`{g.premium_subscription_count}`", inline=True)
        e.add_field(name="Created", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=False)
        # Optional: list top 3 roles
        top_roles = ", ".join([r.mention for r in g.roles[-4:-1][::-1]]) if len(g.roles) > 1 else "None"
        if top_roles:
            e.add_field(name=f"Top Roles", value=top_roles[:1024], inline=False)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="findid", aliases=["lookup","userid"], description="Find user by ID globally")
    async def findid(self, ctx, user_id: str):
        try:
            uid = int(user_id)
            user = await self.bot.fetch_user(uid)
            e = base_embed(f"{user}", f"**ID:** `{user.id}`\n**Bot:** {user.bot}\n**Created:** <t:{int(user.created_at.timestamp())}:R>")
            e.set_thumbnail(url=user.display_avatar.url)
            e.add_field(name="Badges", value=", ".join([str(b) for b in user.public_flags.all()]) or "None")
            await ctx.send(embed=e)
        except:
            await ctx.send(embed=error_embed("Invalid ID or user not found"))

    @commands.hybrid_command(name="userinfo", description="Detailed user info")
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