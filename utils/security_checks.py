import discord
from utils.database import is_whitelisted

async def get_audit_actor(guild: discord.Guild, action: discord.AuditLogAction):
    try:
        async for entry in guild.audit_logs(limit=1, action=action):
            # 5 sec window
            if (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                return entry.user
    except: pass
    return None

async def is_trusted(guild: discord.Guild, user: discord.User):
    if user.id == guild.owner_id: return True
    if user.bot and await is_whitelisted(guild.id, user.id): return True
    if await is_whitelisted(guild.id, user.id): return True
    if user.guild_permissions.administrator:
        # Still need whitelist for critical actions
        return False
    return False

async def quarantine_user(guild: discord.Guild, user: discord.Member, reason: str):
    try:
        # Create jail role if not exists
        jail_role = discord.utils.get(guild.roles, name="Quarantined")
        if not jail_role:
            jail_role = await guild.create_role(name="Quarantined", reason="Security System")
            for channel in guild.channels:
                try:
                    await channel.set_permissions(jail_role, send_messages=False, connect=False, view_channel=False)
                except: pass
        # Strip roles
        await user.edit(roles=[jail_role], reason=reason)
        try:
            await guild.ban(user, reason=f"Quarantine: {reason}")
        except:
            pass
    except Exception as e:
        print(f"Quarantine failed: {e}")