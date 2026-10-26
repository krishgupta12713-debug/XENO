import discord, datetime

COLOR = 0x2b2d31  # Base dark
SUCCESS = 0x57F287
ERROR = 0xED4245
WARN = 0xFEE75C
SECURITY = 0x5865F2  # Blurple for security

def base_embed(title=None, desc=None):
    e = discord.Embed(title=title, description=desc, color=COLOR, timestamp=datetime.datetime.utcnow())
    e.set_footer(text="Dhadkhan • Security", icon_url="https://cdn.discordapp.com/emojis/1094055436510998611.gif")
    return e

def error_embed(desc):
    e = discord.Embed(
        title="✦ Error",
        description=f">>> {desc}",
        color=ERROR,
        timestamp=datetime.datetime.utcnow()
    )
    e.set_footer(text="Dhadkhan • Action Failed")
    return e

def success_embed(desc):
    e = discord.Embed(
        title="✦ Success",
        description=f">>> {desc}",
        color=SUCCESS,
        timestamp=datetime.datetime.utcnow()
    )
    e.set_footer(text="Dhadkhan • Action Completed")
    return e

def warn_embed(desc):
    e = discord.Embed(
        title="✦ Warning",
        description=f">>> {desc}",
        color=WARN,
        timestamp=datetime.datetime.utcnow()
    )
    e.set_footer(text="Dhadkhan • Warning")
    return e

def security_embed(action, actor, victim=None):
    e = discord.Embed(
        title=f"🛡️ Security Alert • {action}",
        color=SECURITY,
        timestamp=datetime.datetime.utcnow()
    )
    e.add_field(
        name="👤 Intruder", 
        value=f"**{actor}**\n`ID: {actor.id}`\n{actor.mention}", 
        inline=True
    )
    if victim:
        e.add_field(
            name="🎯 Target", 
            value=f"`{str(victim)[:100]}`", 
            inline=True
        )
    e.add_field(
        name="⚡ Action Taken", 
        value="> `Quarantined`\n> `Action Reversed`\n> `Logged`", 
        inline=False
    )
    e.set_thumbnail(url=actor.display_avatar.url if hasattr(actor, 'display_avatar') else None)
    e.set_footer(text="Dhadkhan Security • Enterprise Protection", icon_url="https://cdn.discordapp.com/emojis/1170813307241984100.gif")
    return e

def perm_error_embed():
    e = discord.Embed(
        title="🔒 Permission Denied",
        description=">>> **Only Owner / Admin / Staff can use this command.**\n> Fun & Info commands are open for everyone.",
        color=ERROR,
        timestamp=datetime.datetime.utcnow()
    )
    e.set_footer(text="Dhadkhan • Access Restricted")
    return e

def info_embed(title, desc, fields=None):
    e = discord.Embed(title=f"✦ {title}", description=desc, color=COLOR, timestamp=datetime.datetime.utcnow())
    if fields:
        for name, value, inline in fields:
            e.add_field(name=name, value=value, inline=inline)
    e.set_footer(text="Dhadkhan • Info")
    return e
