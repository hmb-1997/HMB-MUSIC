import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil
from aiohttp import web
import markdown2

# --- دروستکرنا فایلا Cookies ژ Railway Variables ---
COOKIES_FILE = "cookies.txt"
cookies_raw = os.getenv("YT_COOKIES")

if cookies_raw:
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(cookies_raw)
    print("✅ Cookies file created successfully.")
else:
    print("⚠️ Warning: YT_COOKIES not found!")

# --- Intents ---
intents = discord.Intents.all()

# --- وێب سێرڤەر بۆ TOS و Privacy ---
def render_page(title, file_path):
    if not os.path.exists(file_path): return "<h1>File Not Found</h1>"
    with open(file_path, "r", encoding="utf-8") as f: content = f.read()
    html_body = markdown2.markdown(content)
    return f"""<html><head><title>{title}</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css"><style>body{{background:#1a1a1a;color:white;padding:40px;}}h1{{color:#5865F2;text-align:center;}}</style></head><body><div style="max-width:800px;margin:auto;"><h1>{title}</h1>{html_body}</div></body></html>"""

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.cleanup_task.start()
        
        # Web Server Setup
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="HMB MUSIC IS ONLINE", content_type='text/html'))
        app.router.add_get('/tos', lambda r: web.Response(text=render_page("Terms of Service", "TOS.md"), content_type='text/html'))
        app.router.add_get('/privacy', lambda r: web.Response(text=render_page("Privacy Policy", "PRIVACY.md"), content_type='text/html'))
        
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"✅ Web Server & Bot Active on port {port}")

    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        folder = 'downloads'
        if os.path.exists(folder):
            for f in os.listdir(folder):
                try: os.remove(os.path.join(folder, f))
                except: pass

bot = MyBot()

# --- ڕێکخستنا ب هێز یا yt-dlp بۆ (YT, TikTok, YT Music) ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
    'extractor_args': {'youtube': {'player_client': ['android', 'web_embedded']}},
}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
FFMPEG_OPTIONS = {'options': '-vn'}

if not os.path.exists('downloads'): os.makedirs('downloads')
queues = {}

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        if os.path.exists(next_song['file']):
            ctx.voice_client.play(discord.FFmpegPCMAudio(next_song['file'], **FFMPEG_OPTIONS), after=lambda e: check_queue(ctx))

async def play_logic(ctx, search: str):
    if not ctx.author.voice: return await ctx.send("❌ پێدڤییە تو ل ناڤ چەناڵەکێ دەنگی بی!")
    vc = ctx.voice_client or await ctx.author.voice.channel.connect()
    
    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=True))
        if 'entries' in data: data = data['entries'][0]
        filename = ytdl.prepare_filename(data)
        
        if vc.is_playing() or vc.is_paused():
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            queues[ctx.guild.id].append({'file': filename, 'title': data.get('title')})
            return await ctx.send(f"➕ Added to queue: **{data.get('title')}**")
            
        vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), after=lambda e: check_queue(ctx))
        embed = discord.Embed(title="🎶 HMB MUSIC - NOW PLAYING", description=f"**{data.get('title')}**", color=discord.Color.blue())
        if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
        await ctx.send(embed=embed, view=ControlView(ctx))
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

# --- کۆنترۆڵ پانێل دگەل SKIP ---
class ControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing(): vc.pause(); await interaction.response.send_message("Paused ⏸️", ephemeral=True)
        else: vc.resume(); await interaction.response.send_message("Resumed ▶️", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip_btn(self, interaction, button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skipped ⏭️", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop_btn(self, interaction, button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Stopped ⏹️", ephemeral=True)

class SongDropdown(discord.ui.Select):
    def __init__(self, ctx, label, songs):
        super().__init__(placeholder=label, options=[discord.SelectOption(label=s[0], value=s[1]) for s in songs])
        self.ctx = ctx
    async def callback(self, inter):
        await inter.response.send_message("🎵 Loading...", ephemeral=True)
        await play_logic(self.ctx, self.values[0])

class YTMusicView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        # ل ڤێرە لیستێن خۆ دابنێ
        l1 = [("Kurdish Melody", "https://music.youtube.com/watch?v=kFeYV_QO2oo"), ("Le Le Shivan", "https://www.youtube.com/watch?v=FpRC6QYiQ3I")]
        self.add_item(SongDropdown(ctx, "📂 Playlist 1", l1))

# --- فەرمانێن بۆتی ---

@bot.hybrid_command(name="play")
async def play(ctx, *, search: str):
    await ctx.defer()
    await play_logic(ctx, search)

@bot.hybrid_command(name="skip", description="بازدان ب سەر سترانا داهاتی")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ موزیک هاتە بازدان (Skipped).")
    else:
        await ctx.send("❌ چو موزیک ناهێنە لێدان!")

@bot.hybrid_command(name="stop", description="ڕاوەستاندن و دەرکەفتن")
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ موزیک هاتە ڕاوەستاندن.")

@bot.hybrid_command(name="yt_music", description="لیستا گۆرانیان")
async def yt_music(ctx):
    await ctx.send("🎶 Select a song:", view=YTMusicView(ctx))

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")

bot.run(os.getenv("DISCORD_TOKEN"))
