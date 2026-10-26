import discord
from discord.ext import commands
from discord import ui
import random, asyncio
from utils.embeds import base_embed
from utils.security_checks import everyone

COLOR = 0x2b2d31

class RPSView(ui.View):
    def __init__(self, author):
        super().__init__(timeout=30)
        self.author = author
    async def play(self, interaction, user_choice):
        bot_choice = random.choice(["rock","paper","scissors"])
        win_map = {"rock":"scissors","paper":"rock","scissors":"paper"}
        if user_choice == bot_choice: res = "Tie! 🟰"
        elif win_map[user_choice] == bot_choice: res = "You Win! ✅"
        else: res = "You Lose! ❌"
        e = base_embed("Rock Paper Scissors", f"You: **{user_choice}**\nBot: **{bot_choice}**\n\n{res}")
        await interaction.response.edit_message(embed=e, view=None)
    @ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.secondary)
    async def rock(self, i, b): await self.play(i, "rock")
    @ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.secondary)
    async def paper(self, i, b): await self.play(i, "paper")
    @ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.secondary)
    async def scissor(self, i, b): await self.play(i, "scissors")

# ===== NEW COINFLIP WITH CHOOSE OPTION =====
class CoinChooseView(ui.View):
    def __init__(self, author, user_choice=None):
        super().__init__(timeout=30)
        self.author = author
        self.user_choice = user_choice

    @ui.button(label="Heads", emoji="🌟", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        await self.start_flip(interaction, "Heads")

    @ui.button(label="Tails", emoji="🌙", style=discord.ButtonStyle.secondary)
    async def tails(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        await self.start_flip(interaction, "Tails")

    async def start_flip(self, interaction, choice):
        self.user_choice = choice
        # Animation 1
        e1 = discord.Embed(title="🪙 Flipping...", description=f"You chose **{choice}**\n\n`[■□□□□]`", color=COLOR)
        await interaction.response.edit_message(embed=e1, view=None)
        await asyncio.sleep(0.6)
        e2 = discord.Embed(title="🪙 In Air...", description=f"You chose **{choice}**\n\n`[■■■□□]`\n*The coin is in the air...*", color=COLOR)
        await interaction.edit_original_response(embed=e2)
        await asyncio.sleep(0.8)
        
        # Result
        result = random.choice(["Heads", "Tails"])
        is_win = result.lower() == choice.lower()
        
        if is_win:
            title = f"🎉 YOU WIN! - {result}"
            desc = f"**Your Choice:** {choice}\n**Result:** {result}\n\n**{interaction.user.mention} WON! ✅**"
            color = 0x57F287 # Green
        else:
            title = f"💀 YOU LOSE! - {result}"
            desc = f"**Your Choice:** {choice}\n**Result:** {result}\n\n**{interaction.user.mention} LOST! ❌**"
            color = 0xED4245 # Red

        e_final = discord.Embed(title=title, description=desc, color=color, timestamp=discord.utils.utcnow())
        e_final.set_footer(text="Dhadkhan • Coinflip")
        # Play again view
        view = CoinChooseView(self.author)
        await interaction.edit_original_response(embed=e_final, view=view)

class CoinViewSimple(ui.View):
    def __init__(self):
        super().__init__(timeout=30)
    @ui.button(label="Flip Coin", emoji="🪙", style=discord.ButtonStyle.primary)
    async def flip(self, interaction: discord.Interaction, button: ui.Button):
        e1 = base_embed("Coinflip", "Flipping... 🪙\n`[■□□□□]`")
        await interaction.response.edit_message(embed=e1, view=None)
        await asyncio.sleep(0.5)
        e2 = base_embed("Coinflip", "Flipping... 🪙\n`[■■■□□]`\n*The coin is in the air...*")
        await interaction.edit_original_response(embed=e2)
        await asyncio.sleep(0.7)
        result = random.choice(["Heads", "Tails"])
        emoji = "🌟" if result == "Heads" else "🌙"
        e_final = discord.Embed(title=f"{emoji} {result}! {emoji}", description=f"**{interaction.user.display_name}** flipped **{result}**!", color=COLOR, timestamp=discord.utils.utcnow())
        e_final.set_footer(text="Dhadkhan • Coinflip")
        new_view = CoinViewSimple()
        await interaction.edit_original_response(embed=e_final, view=new_view)

class TicTacToeView(ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=120)
        self.board = [""]*9
        self.p1, self.p2 = p1, p2
        self.turn = p1
        for i in range(9):
            btn = ui.Button(label="\u200b", style=discord.ButtonStyle.secondary, row=i//3)
            btn.callback = self.make_callback(i)
            self.add_item(btn)
    def make_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id not in [self.p1.id, self.p2.id]:
                return await interaction.response.send_message("❌ You are not in this game!", ephemeral=True)
            if interaction.user != self.turn:
                return await interaction.response.send_message(f"❌ It's {self.turn.mention}'s turn!", ephemeral=True)
            if self.board[idx] != "": 
                return await interaction.response.send_message("Already taken!", ephemeral=True)
            self.board[idx] = "X" if self.turn == self.p1 else "O"
            self.children[idx].label = self.board[idx]
            self.children[idx].disabled = True
            self.children[idx].style = discord.ButtonStyle.success if self.board[idx]=="X" else discord.ButtonStyle.danger
            win = self.check_win()
            if win or "" not in self.board:
                for c in self.children: c.disabled = True
                if win:
                    desc = f"🏆 **Winner:** {self.turn.mention}"
                else:
                    desc = f"🟰 **Draw!**"
                e = base_embed("TicTacToe - Game Over", desc)
                return await interaction.response.edit_message(embed=e, view=self)
            self.turn = self.p2 if self.turn == self.p1 else self.p1
            display = ""
            for i in range(0,9,3):
                row = []
                for j in range(3):
                    val = self.board[i+j]
                    row.append(val if val else "⬜")
                display += "".join(row) + "\n"
            e = base_embed("TicTacToe", f"**{self.p1.mention} (X)** vs **{self.p2.mention} (O)**\nTurn: {self.turn.mention}\n\n{display}")
            await interaction.response.edit_message(embed=e, view=self)
        return cb
    def check_win(self):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if self.board[a] and self.board[a]==self.board[b]==self.board[c]:
                return True
        return False

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rps", description="Rock Paper Scissors - Everyone")
    @everyone()
    async def rps(self, ctx):
        await ctx.send(embed=base_embed("RPS", "Choose your move:"), view=RPSView(ctx.author))

    @commands.hybrid_command(name="coinflip", aliases=["flip", "cf"], description="Flip a coin - Choose Heads/Tails and Win/Lose")
    @everyone()
    async def coinflip(self, ctx, choice: str = None):
        # Agar direct ?coinflip heads likha to instant result
        if choice and choice.lower() in ["heads", "head", "h", "tails", "tail", "t"]:
            user_choice = "Heads" if choice.lower() in ["heads","head","h"] else "Tails"
            e1 = discord.Embed(title="🪙 Flipping...", description=f"You chose **{user_choice}**\n\n`[■□□□□]`", color=COLOR)
            msg = await ctx.send(embed=e1)
            await asyncio.sleep(0.6)
            e2 = discord.Embed(title="🪙 In Air...", description=f"You chose **{user_choice}**\n\n`[■■■□□]`", color=COLOR)
            await msg.edit(embed=e2)
            await asyncio.sleep(0.8)
            result = random.choice(["Heads", "Tails"])
            is_win = result.lower() == user_choice.lower()
            if is_win:
                e_final = discord.Embed(title=f"🎉 YOU WIN! - {result}", description=f"**Your Choice:** {user_choice}\n**Result:** {result}\n\n**{ctx.author.mention} WON! ✅**", color=0x57F287)
            else:
                e_final = discord.Embed(title=f"💀 YOU LOSE! - {result}", description=f"**Your Choice:** {user_choice}\n**Result:** {result}\n\n**{ctx.author.mention} LOST! ❌**", color=0xED4245)
            e_final.set_footer(text="Dhadkhan • Coinflip")
            return await msg.edit(embed=e_final, view=CoinChooseView(ctx.author))

        # Normal - Choose wala UI
        e = discord.Embed(
            title="🪙 Coinflip - Choose Your Side",
            description=f"{ctx.author.mention} Choose **Heads** or **Tails** below!\n\n🌟 Heads\n🌙 Tails",
            color=COLOR
        )
        await ctx.send(embed=e, view=CoinChooseView(ctx.author))

    @commands.hybrid_command(name="avatar", aliases=["av"], description="Show avatar - Everyone")
    @everyone()
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        e = base_embed(f"{user.display_name}'s Avatar")
        e.set_image(url=user.display_avatar.url)
        view = ui.View()
        view.add_item(ui.Button(label="PNG", url=user.display_avatar.with_format("png").url))
        view.add_item(ui.Button(label="JPG", url=user.display_avatar.with_format("jpg").url))
        if user.display_avatar.is_animated():
            view.add_item(ui.Button(label="GIF", url=user.display_avatar.with_format("gif").url))
        await ctx.send(embed=e, view=view)

    @commands.hybrid_command(name="tictactoe", aliases=["ox","ttt"], description="Play TicTacToe - Everyone")
    @everyone()
    async def ttt(self, ctx, opponent: discord.Member = None):
        if not opponent:
            return await ctx.send(embed=base_embed("❌ Error","Mention someone to play!\nExample: `?tictactoe @user`"))
        if opponent.id == ctx.author.id:
            return await ctx.send(embed=base_embed("❌ Error","You can't play with yourself!"))
        if opponent.bot:
            return await ctx.send(embed=base_embed("❌ Error","You can't play with a bot!"))
        view = TicTacToeView(ctx.author, opponent)
        e = base_embed("TicTacToe", f"**{ctx.author.mention} (X)** vs **{opponent.mention} (O)**\nTurn: {ctx.author.mention}\n\n⬜⬜⬜\n⬜⬜⬜")
        await ctx.send(embed=e, view=view)

async def setup(bot):
    await bot.add_cog(Fun(bot))
