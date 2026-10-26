import discord, datetime
COLOR = 0x2b2d31  # Dark mode

def base_embed(title=None, desc=None):
    e = discord.Embed(title=title, description=desc, color=COLOR, timestamp=datetime.datetime.utcnow())
    e.set_footer(text="Dhadkhan Security • Enterprise")
    return e

def error_embed(desc):
    e = base_embed("❌ Error", desc)
    e.color = 0xED4245
    return e

def success_embed(desc):
    e = base_embed("✅ Success", desc)
    e.color = 0x57F287
    return e

def security_embed(action, actor, victim=None):
    e = base_embed(f"🛡️ Anti-Nuke Triggered: {action}")
    e.add_field(name="Actor", value=f"`{actor.id}`", inline=True)
    if victim:
        e.add_field(name="Target", value=str(victim)[:100])
    e.add_field(name="Action", value="Quarantined & Reversed", inline=False)
    return e