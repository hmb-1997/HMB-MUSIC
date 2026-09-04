import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil
from aiohttp import web
import markdown2

# --- دروستکرنا فایلا Cookies ژ Railway ---
COOKIES_FILE = "cookies.txt"
cookies_raw = os.getenv("YT_COOKIES")

if cookies_raw:
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(cookies_raw)
    print("✅ System Secure: Cookies Active")

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.cleanup_task.start()
        # وێب سێرڤەر بۆ پاراستنا پڕۆژەی
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="HMB SYSTEM ACTIVE", content_type='text/html'))
        runner = web.AppRunner(app); await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port); await site.start()

    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        if os.path.exists('downloads'):
            for f in os.listdir('downloads'):
                try: os.remove(os.path.join('downloads', f))
                except: pass

bot = MyBot()

# --- سیستەمێ داکێشانێ یێ ب هێزکری (War Mode) ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'], # بکارئینانا ئەندرۆید بۆ تێپەڕاندنا بلۆکی
            'skip': ['dash', 'hls']
        }
    },
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ڕێکخستنا ب هێز یا FFmpeg دا کو دەنگ تێک نەچیت
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

queues = {}

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        ctx.voice_client.play(discord.FFmpegPCMAudio(next_song['file'], **FFMPEG_OPTIONS), after=lambda e: check_queue(ctx))

async def play_logic(ctx, search: str):
    if not ctx.author.voice: return await ctx.send("❌ پێدڤییە تو ل ڤۆیس بی!")
    vc = ctx.voice_client or await ctx.author.voice.channel.connect()
    
    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=True))
        if 'entries' in data: data = data['entries'][0]
        filename = ytdl.prepare_filename(data)
        
        if vc.is_playing():
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            queues[ctx.guild.id].append({'file': filename, 'title': data.get('title')})
            return await ctx.send(f"➕ Added to queue: **{data.get('title')}**")
            
        vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), after=lambda e: check_queue(ctx))
        embed = discord.Embed(title="🎶 Now Playing", description=f"**{data.get('title')}**", color=0x00ff00)
        await ctx.send(embed=embed, view=ControlView(ctx))
    except Exception as e:
        await ctx.send(f"⚠️ یوتیوب سێرڤەری بلۆک دکەت. تکایە Cookies نوو بکەڤە.")

class ControlView(discord.ui.View):
    def __init__(self, ctx): super().__init__(timeout=None); self.ctx = ctx
    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def pause(self, i, b):
        if i.guild.voice_client.is_playing(): i.guild.voice_client.pause(); await i.response.send_message("Paused", ephemeral=True)
        else: i.guild.voice_client.resume(); await i.response.send_message("Resumed", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, i, b):
        if i.guild.voice_client: 
            i.guild.voice_client.stop()
            await i.response.send_message("Skipped ⏭️", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, i, b):
        if i.guild.voice_client: 
            queues[i.guild.id] = []
            await i.guild.voice_client.disconnect()
            await i.response.send_message("Stopped", ephemeral=True)

@bot.hybrid_command(name="play")
async def play(ctx, *, search: str): await ctx.defer(); await play_logic(ctx, search)

@bot.hybrid_command(name="skip")
async def skip(ctx):
    if ctx.voice_client: ctx.voice_client.stop(); await ctx.send("⏭️ Skipped.")

@bot.event
async def on_ready(): print(f"🚀 HMB SYSTEM IS ONLINE AND POWERFUL!")

bot.run(os.getenv("DISCORD_TOKEN"))
