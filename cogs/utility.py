import discord, re, aiohttp, os, aiosqlite, asyncio, io
from discord.ext import commands
from discord import ui
from utils.embeds import base_embed, success_embed, error_embed
from utils.database import set_prefix_db
from utils.security_checks import mod_only

# Everyone check - Simple, always allow
def everyone():
    def predicate(ctx):
        return True
    return commands.check(predicate)

class StealView(ui.View):
    def __init__(self, emoji_data=None, sticker_data=None, author_id=None):
        super().__init__(timeout=60)
        self.emoji_data = emoji_data
        self.sticker_data = sticker_data
        self.author_id = author_id

    @ui.button(label="Steal This", emoji="🦋", style=discord.ButtonStyle.primary)
    async def steal_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Only command user can steal!", ephemeral=True)
        
        await interaction.response.defer()
        guild = interaction.guild
        
        if not guild.me.guild_permissions.manage_emojis_and_stickers:
            return await interaction.followup.send(embed=error_embed("I need `Manage Emojis & Stickers` permission!"), ephemeral=True)

        try:
            if self.sticker_data:
                async with aiohttp.ClientSession() as s:
                    async with s.get(self.sticker_data['url']) as r:
                        data = await r.read()
                file = discord.File(fp=io.BytesIO(data), filename=f"{self.sticker_data['name']}.png")
                new_s = await guild.create_sticker(name=self.sticker_data['name'][:30], description="Stolen by XENO", emoji="🦋", file=file)
                await interaction.followup.send(embed=success_embed(f"Sticker Stolen: {new_s.name}"))
            
            elif self.emoji_data:
                stolen = []
                for name, eid, is_anim, url in self.emoji_data:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url) as r:
                            if r.status != 200:
                                continue
                            img = await r.read()
                    try:
                        new_e = await guild.create_custom_emoji(name=name[:32].replace(" ", "_"), image=img)
                        stolen.append(str(new_e))
                    except discord.HTTPException as e:
                        if "Maximum number of emojis" in str(e):
                            await interaction.followup.send(embed=error_embed("Emoji limit reached!"), ephemeral=True)
                            break
                if stolen:
                    await interaction.followup.send(embed=success_embed(f"Stolen {len(stolen)} emoji: {' '.join(stolen)}"))
                else:
                    await interaction.followup.send(embed=error_embed("Failed to steal emojis!"), ephemeral=True)

            for child in self.children: 
                child.disabled = True
                child.label = "Stolen ✅"
            await interaction.edit_original_response(view=self)

        except Exception as e:
            await interaction.followup.send(embed=error_embed(f"Error: {str(e)[:200]}"), ephemeral=True)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="steal", description="Steal emoji/sticker from message")
    @mod_only()
    async def steal(self, ctx):
        e = base_embed("Steal Mode 🦋", "Send an **emoji, custom emoji or sticker** in this channel now!\nYou have **30 seconds**.")
        e.set_footer(text=f"Requested by {ctx.author.display_name}")
        msg = await ctx.send(embed=e)

        def check(m):
            if m.author.id != ctx.author.id or m.channel.id != ctx.channel.id:
                return False
            # Check if message has sticker or custom emoji pattern
            has_sticker = len(m.stickers) > 0
            has_emoji_pattern = bool(re.search(r'<a?:\w+:\d+>', m.content))
            has_attachment = len(m.attachments) > 0 and m.stickers
            return has_sticker or has_emoji_pattern or has_attachment

        try:
            user_msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await msg.edit(embed=error_embed("⏰ Time out! You didn't send anything in 30s."))

        emoji_data = []
        sticker_data = None

        # 1. Sticker Case
        if user_msg.stickers:
            sticker = user_msg.stickers[0]
            sticker_data = {"name": sticker.name, "url": sticker.url}
            preview = base_embed("Sticker Found ✨", f"**Name:** `{sticker.name}`\n**ID:** `{sticker.id}`")
            preview.set_thumbnail(url=sticker.url)
            view = StealView(sticker_data=sticker_data, author_id=ctx.author.id)
            await ctx.send(embed=preview, view=view)
            try: await user_msg.delete()
            except: pass
            return

        # 2. Emoji Case
        matches = re.findall(r'<(a)?:(\w+):(\d+)>', user_msg.content)
        if matches:
            for anim_flag, name, eid in matches:
                ext = "gif" if anim_flag else "png"
                url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}"
                emoji_data.append((name, eid, bool(anim_flag), url))
            
            if emoji_data:
                desc = ""
                for n, eid, a, _ in emoji_data[:5]: # Show max 5
                    em_str = f"<{'a' if a else ''}:{n}:{eid}>"
                    desc += f"{em_str} - `{n}`\n"
                
                preview = base_embed(f"Found {len(emoji_data)} Emoji(s) ✨", desc)
                preview.set_thumbnail(url=emoji_data[0][3])
                view = StealView(emoji_data=emoji_data, author_id=ctx.author.id)
                await ctx.send(embed=preview, view=view)
                try: await user_msg.delete()
                except: pass
                return

        await ctx.send(embed=error_embed("No valid emoji/sticker found! Send like `<:name:id>` or a sticker."))

    @commands.hybrid_command(name="setprefix", description="Change server prefix")
    @mod_only()
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 3:
            return await ctx.send(embed=error_embed("❌ Prefix max 3 characters allowed!"))
        if len(new_prefix) < 1:
            return await ctx.send(embed=error_embed("❌ Prefix can't be empty!"))
        
        try:
            await set_prefix_db(ctx.guild.id, new_prefix)
            await ctx.send(embed=success_embed(f"✅ Prefix changed to `{new_prefix}`\nExample: `{new_prefix}help`"))
        except Exception as e:
            await ctx.send(embed=error_embed(f"DB Error: {e}"))

    # ===== EVERYONE COMMANDS - FIXED =====
    @commands.hybrid_command(name="serverinfo", aliases=["si", "guildinfo"], description="Show server information")
    @everyone()
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = discord.Embed(title=f"{g.name}", color=0x2B2D31, timestamp=discord.utils.utcnow())
        e.add_field(name="👑 Owner", value=f"<@{g.owner_id}>", inline=True)
        e.add_field(name="🆔 ID", value=f"`{g.id}`", inline=True)
        e.add_field(name="👥 Members", value=f"`{g.member_count}`", inline=True)
        e.add_field(name="🎭 Roles", value=f"`{len(g.roles)}`", inline=True)
        e.add_field(name="📁 Channels", value=f"`{len(g.channels)}`", inline=True)
        e.add_field(name="🚀 Boosts", value=f"`{g.premium_subscription_count}`", inline=True)
        e.add_field(name="📅 Created", value=f"<t:{int(g.created_at.timestamp())}:D> (<t:{int(g.created_at.timestamp())}:R>)", inline=False)
        e.set_footer(text=f"Requested by {ctx.author.display_name}")
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        if g.banner:
            e.set_image(url=g.banner.url)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="findid", aliases=["lookup","userid", "finduser"], description="Find user by ID")
    @everyone()
    async def findid(self, ctx, user_id: str):
        if not user_id.isdigit():
            return await ctx.send(embed=error_embed("❌ Please provide a valid numeric ID!"))
        try:
            user = await self.bot.fetch_user(int(user_id))
            e = discord.Embed(title=f"{user.display_name}", description=f"**ID:** `{user.id}`\n**Bot:** {'Yes 🤖' if user.bot else 'No'}\n**Created:** <t:{int(user.created_at.timestamp())}:R>", color=0x2B2D31)
            e.set_thumbnail(url=user.display_avatar.url)
            e.set_footer(text="User Found")
            view = ui.View()
            view.add_item(ui.Button(label="Avatar Link", url=user.display_avatar.url))
            await ctx.send(embed=e, view=view)
        except discord.NotFound:
            await ctx.send(embed=error_embed("❌ User not found with that ID!"))
        except Exception as ex:
            await ctx.send(embed=error_embed(f"Error: {str(ex)[:100]}"))

    @commands.hybrid_command(name="userinfo", aliases=["ui", "whois"], description="Show user information")
    @everyone()
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        e = discord.Embed(title=f"{member.display_name}", color=0x2B2D31, timestamp=discord.utils.utcnow())
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        e.add_field(name="🏷️ Tag", value=f"`{str(member)}`", inline=True)
        e.add_field(name="🤖 Bot", value=f"{'Yes' if member.bot else 'No'}", inline=True)
        e.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        e.add_field(name="📥 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        e.add_field(name="👑 Top Role", value=member.top_role.mention, inline=True)
        roles = [r.mention for r in member.roles[1:]][::-1][:10]
        e.add_field(name=f"🎭 Roles [{len(member.roles)-1}]", value=" ".join(roles) if roles else "None", inline=False)
        e.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=e)

async def setup(bot):
    await bot.add_cog(Utility(bot))
