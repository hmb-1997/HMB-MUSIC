import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# رێکخستنا تایبەت بۆ پاقژکرنا فایلێن دابەزی پاش لێدانێ
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'outtmpl': 'song_%(id)s.%(ext)s', # فایلێ دابەزی ب ڤی ناڤی دێ بیت
}

FFMPEG_OPTIONS = {
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ HMB MUSIC IS ACTIVE")

@bot.hybrid_command(name="play", description="لێدانا موزیکێ ب گەرەنتی")
async def play(ctx, *, search: str):
    await ctx.defer()
    
    if not ctx.author.voice:
        return await ctx.send("❌ Join a voice channel!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    try:
        # کێشانا زانیارییان و دابەزاندنەکا خێرا (Download)
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=True))
        if 'entries' in data: data = data['entries'][0]
        
        filename = ytdl.prepare_filename(data)
        
        # لێدانا فایلی ب ڕێکا FFmpeg
        vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), 
                after=lambda e: os.remove(filename) if os.path.exists(filename) else None)

        embed = discord.Embed(title="🎶 Now Playing", description=f"**{data['title']}**", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# پاقژکەرێ ئۆتۆماتیکی یێ فایلان (بۆ زێدەهی)
@tasks.loop(minutes=5)
async def cleaner():
    for f in os.listdir('.'):
        if f.startswith("song_") and f.endswith((".webm", ".m4a", ".mp3")):
            try: os.remove(f)
            except: pass

bot.run(os.getenv("DISCORD_TOKEN"))
