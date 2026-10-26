import discord
from discord.ext import commands
from utils.database import is_whitelisted
from utils.embeds import perm_error_embed

# ===== AUDIT LOG HELPER =====
async def get_audit_actor(guild: discord.Guild, action: discord.AuditLogAction):
    try:
        async for entry in guild.audit_logs(limit=1, action=action):
            if (discord.utils.utcnow() - entry.created_at).total_seconds() < 8:
                return entry.user
    except: pass
    return None

# ===== 1. NUKE TRUSTED - SIRF OWNER =====
# Whitelist bhi isme trusted nahi hai - Nuke karega toh ban hoga
async def is_nuke_trusted(guild: discord.Guild, user: discord.Member):
    if not user: return False
    if user.id == guild.owner_id: return True
    # Bot owner (tu) - .env me BOT_OWNER_ID daal de
    import os
    if str(user.id) == os.getenv("BOT_OWNER_ID"): return True
    return False

# ===== 2. AUTOMOD BYPASS - Owner + Admin + Whitelist + Bot =====
async def is_automod_bypass(guild: discord.Guild, user: discord.Member):
    if not user: return False
    if user.id == guild.owner_id: return True
    if user.guild_permissions.administrator: return True
    if user.bot: return True
    if await is_whitelisted(guild.id, user.id): return True
    return False

# ===== 3. MOD ONLY CHECK - Owner / Admin / Manage Guild =====
# Whitelist ko command ka permission nahi hai
def mod_only():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if ctx.author.guild_permissions.manage_guild:
            return True
        if ctx.author.guild_permissions.manage_messages:
            return True
        # Whitelist check nahi - command nahi chala payega
        return False
    return commands.check(predicate)

# ===== 4. EVERYONE - Sabke liye open =====
def everyone():
    def predicate(ctx):
        return True
    return commands.check(predicate)

# ===== 5. QUARANTINE SYSTEM =====
async def quarantine_user(guild: discord.Guild, user: discord.Member, reason: str):
    try:
        # Jail role banao
        jail_role = discord.utils.get(guild.roles, name="Quarantined")
        if not jail_role:
            jail_role = await guild.create_role(
                name="Quarantined", 
                color=discord.Color.from_str("#2b2d31"),
                reason="Dhadkhan Security System"
            )
            # Sab channels se hide
            for channel in guild.channels:
                try:
                    await channel.set_permissions(jail_role, send_messages=False, connect=False, view_channel=False, speak=False)
                except: continue
        
        # Roles strip + Jail role
        try:
            await user.edit(roles=[jail_role], reason=f"Security: {reason}")
        except: pass
        
        # Ban attempt
        try:
            await guild.ban(user, reason=f"Quarantine: {reason}", delete_message_days=0)
        except: pass
        
        print(f"🔒 Quarantined: {user} ({user.id}) - {reason}")
        return True
    except Exception as e:
        print(f"Quarantine failed for {user}: {e}")
        return False
