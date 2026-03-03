import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime, timezone
import os
from dotenv import load_dotenv
import asyncio
import re
import json
import time
import random

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
intents.message_content = True


bot = commands.Bot(command_prefix="!", intents=intents)
datetime.now(timezone.utc)
bot.remove_command("help")

# ===============================
# DATABASE SEDERHANA (IN MEMORY)
# ===============================
afk_users = {}

WELCOME_FILE = "welcome.json"

def load_welcome():
    try:
        with open(WELCOME_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=4)

welcome_data = load_welcome()

def parse_time(time_str):
    match = re.match(r"(\d+)([smhd])", time_str)
    if not match:
        return None

    value, unit = match.groups()
    value = int(value)

    if unit == "s":
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    
TRIGGER_FILE = "triggers.json"

def load_triggers():
    if not os.path.exists(TRIGGER_FILE):
        with open(TRIGGER_FILE, "w") as f:
            json.dump({}, f)

    with open(TRIGGER_FILE, "r") as f:
        return json.load(f)

def save_triggers(data):
    with open(TRIGGER_FILE, "w") as f:
        json.dump(data, f, indent=4)

triggers = load_triggers()
# ===============================
# READY
# ===============================
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over your server 👀"
        )
    )
    print(f"✅ Bot aktif sebagai {bot.user}")
    
@bot.event
async def on_message(message):

    # Jangan proses bot
    if message.author.bot:
        return

    # Hindari error kalau DM
    if not message.guild:
        return

    guild_id = str(message.guild.id)
    content = message.content.lower().strip()

    # =====================
    # TRIGGER SYSTEM
    # =====================
    guild_id = str(message.guild.id)
    content = message.content.lower().strip()

    if guild_id in triggers:
        for data in triggers[guild_id].values():
            if content == data["trigger"]:
                await message.channel.send(data["response"])
                break
    # =====================
    # AFK RETURN CHECK
    # =====================
    if message.author.id in afk_users:
        afk_data = afk_users.pop(message.author.id)
        afk_time = int(time.time() - afk_data["time"])

        # Format durasi AFK
        hours = afk_time // 3600
        minutes = (afk_time % 3600) // 60
        seconds = afk_time % 60

        duration = ""
        if hours:
            duration += f"{hours}h "
        if minutes:
            duration += f"{minutes}m "
        if seconds:
            duration += f"{seconds}s"

        # Remove [AFK] dari nickname
        try:
            if message.author.nick and "[AFK]" in message.author.nick:
                new_nick = message.author.nick.replace("[AFK]", "").strip()
                await message.author.edit(nick=new_nick)
        except:
            pass

        await message.channel.send(
            f"Welcome back {message.author.mention}'s from your journy outside.. "
            f"you have been AFK for {duration.strip()}!"
        )

    # =====================
    # AFK MENTION CHECK
    # =====================
    for user in message.mentions:
        if user.id in afk_users:
            afk_data = afk_users[user.id]
            afk_time = int(time.time() - afk_data["time"])

            hours = afk_time // 3600
            minutes = (afk_time % 3600) // 60
            seconds = afk_time % 60

            duration = ""
            if hours:
                duration += f"{hours}h "
            if minutes:
                duration += f"{minutes}m "
            if seconds:
                duration += f"{seconds}s"

            await message.channel.send(
                f"{user.mention} have been AFK for: {duration.strip()}!, with reason: {afk_data['reason']}.",
                allowed_mentions=discord.AllowedMentions(users=False)
            )

    # Penting supaya command tetap jalan
    await bot.process_commands(message)

# ===============================
# WELCOME MESSAGE
# ===============================
@bot.command()
@commands.has_permissions(manage_guild=True)
async def welc(ctx, *, message):
    guild_id = str(ctx.guild.id)

    if guild_id not in welcome_data:
        welcome_data[guild_id] = {}

    welcome_data[guild_id]["message"] = message
    save_welcome(welcome_data)

    await ctx.send("✅ Welcome message berhasil disimpan.")
    
@bot.command()
@commands.has_permissions(manage_guild=True)
async def setchannel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)

    if guild_id not in welcome_data:
        welcome_data[guild_id] = {}

    welcome_data[guild_id]["channel"] = channel.id
    save_welcome(welcome_data)

    await ctx.send(f"✅ Welcome channel diset ke {channel.mention}")
    
@bot.command()
async def test_greet(ctx):
    guild_id = str(ctx.guild.id)

    if guild_id not in welcome_data:
        return await ctx.send("❌ Welcome belum dikonfigurasi.")

    channel_id = welcome_data[guild_id].get("channel")
    message_template = welcome_data[guild_id].get("message")

    if not channel_id or not message_template:
        return await ctx.send("❌ Welcome belum lengkap.")

    channel = bot.get_channel(channel_id)

    msg = message_template.replace("{user}", ctx.author.mention)\
                          .replace("{server}", ctx.guild.name)

    await channel.send(msg)
    
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)

    if guild_id not in welcome_data:
        return

    channel_id = welcome_data[guild_id].get("channel")
    message_template = welcome_data[guild_id].get("message")

    if not channel_id or not message_template:
        return

    channel = bot.get_channel(channel_id)

    msg = message_template.replace("{user}", member.mention)\
                          .replace("{server}", member.guild.name)

    await channel.send(msg)


# ===============================
# USER TRACKER
# ===============================
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)

    # Fetch full user (biar banner kebaca)
    user = await bot.fetch_user(member.id)

    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
    role_text = ", ".join(roles[:10])
    if len(roles) > 10:
        role_text += f" and {len(roles) - 10} more roles"

    embed = discord.Embed(
        title=f"{member.display_name}",
        color=member.color if member.color != discord.Color.default() else discord.Color.dark_gray()
    )

    # ✅ Avatar (GIF support otomatis)
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="📛 Username", value=member, inline=False)
    embed.add_field(name="🆔 User ID", value=member.id, inline=False)
    embed.add_field(
        name="Account Created",
        value=member.created_at.strftime('%d %b %Y'),
        inline=True
    )

    embed.add_field(
        name="Joined Server",
        value=member.joined_at.strftime('%d %b %Y'),
        inline=True
    )

    embed.add_field(
        name=f"Roles[{len(roles)}]",
        value=f"{role_text if role_text else 'No roles'}\n",
        inline=False
    )

    # ✅ Banner (GIF support otomatis)
    if user.banner:
        embed.set_image(url=user.banner.url)

    await ctx.send(embed=embed)

# ===============================
# BAN
# ===============================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} permanent ban.")
    
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)

    await ctx.guild.unban(user)
    await ctx.send(f"✅ {user} get unban.")

# ===============================
# KICK
# ===============================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, duration: str):

    seconds = parse_time(duration)

    if not seconds:
        return await ctx.send("❌ Format waktu salah. Contoh: 1d")

    if seconds < 86400:
        return await ctx.send("❌ Minimal durasi kick adalah 1 hari (1d).")

    await member.kick(reason="Temporary Kick")
    await ctx.send(f"👢 {member} dikick selama {duration}")

    await asyncio.sleep(seconds)

    invite = await ctx.channel.create_invite(max_age=300)

    try:
        await member.send(f"Kamu bisa join kembali: {invite}")
    except:
        pass

# ===============================
# TIMEOUT
# ===============================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def to(ctx, member: discord.Member, duration: str):
    seconds = parse_time(duration)

    if not seconds:
        return await ctx.send("❌ Format waktu salah. Contoh: 10m, 1h")

    if seconds < 600:
        return await ctx.send("❌ Minimal timeout adalah 10 menit (10m).")

    until = discord.utils.utcnow() + timedelta(seconds=seconds)

    # Cek role hierarchy
    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Role bot lebih rendah dari target.")

    try:
        await member.timeout(until)
        await ctx.send(f"⏳ {member} ditimeout selama {duration}")
    except discord.Forbidden:
        await ctx.send("❌ Bot tidak punya izin untuk timeout user ini.")
# ===============================
# EMBED
# ===============================
@bot.command()
async def embedcreate(ctx, *, text):

    parts = text.split("|")

    if len(parts) != 3:
        return await ctx.send("Format:\n!embedcreate Title | Description | link")

    title = parts[0].strip()
    description = parts[1].strip()
    image_url = parts[2].strip()

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )

    embed.set_image(url=image_url)

    await ctx.send(embed=embed)

# ===============================
# STEAL EMOJI
# ===============================
@bot.command()
@commands.has_permissions(manage_emojis=True)
async def steal(ctx, emoji: str):
    if not ctx.guild.me.guild_permissions.manage_emojis:
        return await ctx.send("❌ Bot tidak punya permission Manage Emojis!")

    match = re.match(r'<a?:(\w+):(\d+)>', emoji)
    if not match:
        return await ctx.send("❌ Emoji tidak valid!")

    name, emoji_id = match.groups()
    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
    url2 = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"

    async with bot.http._HTTPClient__session.get(url) as resp:
        if resp.status != 200:
            return await ctx.send("❌ Gagal mengambil emoji.")
        data = await resp.read()
        
    async with bot.http._HTTPClient__session.get(url2) as resp:
        if resp.status != 200:
            return await ctx.send("❌ Gagal mengambil emoji.")
        data = await resp.read()

    try:
        await ctx.guild.create_custom_emoji(name=name, image=data)
        await ctx.send("✅ Emoji berhasil diambil.")
    except discord.Forbidden:
        await ctx.send("❌ Bot tidak punya izin untuk membuat emoji.")
# ===============================
# ADD TRIGGER
# ===============================
@bot.command()
@commands.has_permissions(manage_guild=True)
async def trigger_create(ctx, *, text):

    if "|" not in text:
        return await ctx.send("Format:\n!trigger_create trigger | response")

    trigger_text, response = text.split("|", 1)
    trigger_text = trigger_text.strip().lower()
    response = response.strip()

    guild_id = str(ctx.guild.id)

    if guild_id not in triggers:
        triggers[guild_id] = {}

    # Cek duplikat
    for data in triggers[guild_id].values():
        if data["trigger"] == trigger_text:
            return await ctx.send("❌ Trigger sudah ada.")

    trigger_id = str(random.randint(100000, 999999))

    triggers[guild_id][trigger_id] = {
        "trigger": trigger_text,
        "response": response
    }

    save_triggers(triggers)

    await ctx.send(f"<a:Verified:1384383595308646451> has maded. with ID: `{trigger_id}`")
    
@bot.command()
@commands.has_permissions(manage_guild=True)
async def trigger_edit(ctx, trigger_id: str, *, new_response):

    guild_id = str(ctx.guild.id)

    if guild_id not in triggers or trigger_id not in triggers[guild_id]:
        return await ctx.send("❌ Trigger ID tidak ditemukan.")

    triggers[guild_id][trigger_id]["response"] = new_response.strip()

    save_triggers(triggers)

    await ctx.send(f"✅ Trigger `{trigger_id}` berhasil diupdate.")
    
@bot.command()
@commands.has_permissions(manage_guild=True)
async def trigger_remove(ctx, trigger_id: str):

    guild_id = str(ctx.guild.id)

    if guild_id not in triggers or trigger_id not in triggers[guild_id]:
        return await ctx.send("❌ Trigger ID tidak ditemukan.")

    del triggers[guild_id][trigger_id]

    save_triggers(triggers)

    await ctx.send(f"🗑 Trigger `{trigger_id}` dihapus.")
    
@bot.command()
async def trigger_list(ctx):

    guild_id = str(ctx.guild.id)

    if guild_id not in triggers or not triggers[guild_id]:
        return await ctx.send("Belum ada trigger di server ini.")

    embed = discord.Embed(
        title="📌 Daftar Trigger",
        color=discord.Color.blue()
    )

    description = ""

    for trigger_id, data in triggers[guild_id].items():
        description += (
            f"**ID:** `{trigger_id}`\n"
            f"Trigger: `{data['trigger']}`\n\n"
        )

    embed.description = description[:4096]

    await ctx.send(embed=embed)

# ===============================
# SERVER INFO
# ===============================
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)

    # Locked channels (deny send_messages)
    locked = 0
    for channel in guild.channels:
        overwrite = channel.overwrites_for(guild.default_role)
        if hasattr(overwrite, "send_messages"):
            if overwrite.send_messages is False:
                locked += 1

    # Features formatting
    if guild.features:
        features = "\n".join(
            [f"✅ {f.replace('_', ' ').title()}" for f in guild.features]
        )
    else:
        features = "None"

    # Boost info
    boost_level = guild.premium_tier
    boost_count = guild.premium_subscription_count

    embed = discord.Embed(
        title=f"Info for {guild.name}",
        color=discord.Color.dark_gray()
    )

    # Server icon thumbnail (kanan atas)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Row 1
    embed.add_field(name="Owner", value=guild.owner, inline=True)
    embed.add_field(name="Features", value=features[:1024], inline=True)
    embed.add_field(
        name="Boosts",
        value=f"Level {boost_level} ({boost_count} boosts)",
        inline=True
    )

    # Row 2
    embed.add_field(
        name="Channels",
        value=f"💬 {text_channels} ({locked} locked)\n🔊 {voice_channels}",
        inline=True
    )

    embed.add_field(
        name="Info",
        value=f"Verification level: {str(guild.verification_level).title()}\n"
              f"{'[Icon Link]('+guild.icon.url+')' if guild.icon else 'No Icon'}",
        inline=True
    )

    embed.add_field(
        name="Members",
        value=f"Total: {guild.member_count}\nHumans: {humans}\nBots: {bots}",
        inline=True
    )

    # Row 3
    embed.add_field(
        name="Roles",
        value=f"{len(guild.roles)} roles",
        inline=True
    )

    embed.set_footer(
        text=f"ID: {guild.id}, Created - {guild.created_at.strftime('%d/%m/%Y %H:%M')}"
    )

    await ctx.send(embed=embed)
# ===============================
# VOICE INFO
# ===============================
@bot.command()
async def voiceinfo(ctx):
    if not ctx.author.voice:
        return await ctx.send("Kamu tidak di voice!")

    vc = ctx.author.voice.channel
    await ctx.send(f"🎧 Nama: {vc.name}\n👥 User: {len(vc.members)}")

# ===============================
# USER PFP AND BANNER
# ===============================

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author

    # Global Avatar
    global_avatar = member.display_avatar.replace(size=4096).url
    await ctx.send(
        f"Here is {member.mention}'s [profile]({global_avatar})"
    )

    # Server Avatar (jika ada)
    if member.guild_avatar:
        server_avatar = member.guild_avatar.replace(size=4096).url
        await ctx.send(
            f"and [server profile]({server_avatar})"
        )

@bot.command()
async def banner(ctx, member: discord.Member = None):
    member = member or ctx.author

    user = await bot.fetch_user(member.id)

    if not user.banner:
        return await ctx.send(f"{member.mention} tidak memiliki banner.")

    banner_url = user.banner.replace(size=4096).url

    await ctx.send(
        f"Here is {member.mention}'s [banner]({banner_url})"
    )

# ===============================
# SERVER ICON
# ===============================
@bot.command()
async def servericon(ctx):
    if ctx.guild.icon:
        await ctx.send(ctx.guild.icon.url)

# ===============================
# SERVER BANNER
# ===============================
@bot.command()
async def serverbanner(ctx):
    if ctx.guild.banner:
        await ctx.send(ctx.guild.banner.url)

# ===============================
# MUSIC INFO
# ===============================

MUSIC_BOTS = {
    "Gennosic 1": 411916947773587456,
    "Gennosic 2": 412347257233604609,
    "Gennosic 3": 412347553141751808,
    "Gennosic 4": 412347780841865216,
    "Gennosic 5": 185476724627210241,
    "Gennosic 6": 1190991820637868042,
    "Gennosic 7": 1205557263738216559,
    "Gennosic 8": 235088799074484224,
    "Gennosic 9": 184405311681986560,
    "Gennosic 10": 810540985032900648,
    "Gennosic 11": 451379187031343104,
    "Gennosic 12": 1040955279128412220,
    "Gennosic 13": 684773505157431347,
    "Gennosic 14": 707627135577358417,
    "Gennosic 15": 749248172756303913,
    "Gennosic 16": 944016826751389717,
    "Gennosic 17": 917761628924149771,
    "Gennosic 18": 1066057160125059112,
    "Gennosic 19": 1145363441524166758,
    "Gennosic 20": 1259530981526868048,
    "Gennosic 21": 1021732722479202304,
    "Gennosic 22": 1083614706289348728,
    "Gennosic 23": 749248172756303913,
    "Gennosic 24": 679643572814741522
}

@bot.command()
async def musicinfo(ctx):
    guild = ctx.guild

    used_bots = []
    unused_bots = []

    for name, bot_id in MUSIC_BOTS.items():
        member = guild.get_member(bot_id)

        if member and member.voice:
            used_bots.append(f"🟢 **{name}** - Digunakan di {member.voice.channel.mention}\n")
        else:
            unused_bots.append(f"🔴 **{name}** - Tidak digunakan\n")

    embed = discord.Embed(
        title="🎵 Music Bot Status",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Sedang Dipakai",
        value="\n".join(used_bots) if used_bots else "Tidak ada bot yang digunakan",
        inline=False
    )

    embed.add_field(
        name="Tidak Dipakai",
        value="\n".join(unused_bots) if unused_bots else "Semua bot sedang digunakan",
        inline=False
    )

    await ctx.send(embed=embed)
    
# ===============================
# AFK
# ===============================
@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = {
        "reason": reason,
        "time": time.time()
    }

    # Tambah tag [AFK] di nickname
    try:
        if ctx.author.nick:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.nick}")
        else:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.name}")
    except:
        pass

    await ctx.send(f"{ctx.author.mention} | set AFK, reason: {reason}")
    
# ===============================
# DMEMBED
# ===============================       
@bot.command()
@commands.has_permissions(manage_messages=True)
async def dmembed(ctx, *, args):

    if not args:
        return await ctx.send(
            "Format:\n"
            "!dmembed @user | Pesan\n"
            "atau\n"
            "!dmembed Pesan"
        )

    parts = args.split("|")

    # Cek mention
    member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

    # Hapus mention dari teks kalau ada
    if ctx.message.mentions:
        parts[0] = parts[0].replace(member.mention, "").strip()

    description = parts[0].strip()

    if not description:
        return await ctx.send("Isi pesan tidak boleh kosong.")

    embed = discord.Embed(
        description=description,
        timestamp=discord.utils.utcnow()
    )

    # ===== CUSTOM NAME =====
    CUSTOM_NAME = "GENNOVERA Supports"

    # Author (icon server + custom name)
    if ctx.guild.icon:
        embed.set_author(
            name=CUSTOM_NAME,
            icon_url=ctx.guild.icon.url
        )
    else:
        embed.set_author(name=CUSTOM_NAME)

    # Footer sekarang berisi tag user
    embed.set_footer(
        text=f"Dikirim oleh {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    try:
        await member.send(embed=embed)
        await ctx.send(f"✅ Berhasil kirim DM ke {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ Tidak bisa mengirim DM (DM user tertutup).")
        

    
OWNER_ID = 1023233349873041470

@bot.command()
async def say(ctx, *, message):

    # Cek apakah user yang pakai adalah owner
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ You are not allowed to use this command.")

    # Hapus command biar clean
    try:
        await ctx.message.delete()
    except:
        pass

    # Kirim pesan tanpa bisa abuse @everyone
    await ctx.send(
        message,
        allowed_mentions=discord.AllowedMentions(
            everyone=False,
            roles=False,
            users=True
        )
    )

bot.run(TOKEN)