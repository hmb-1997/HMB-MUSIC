import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil
from aiohttp import web # بۆ وێب سێرڤەری
import markdown2 # بۆ جوانکرنا لاپەڕان

# --- رێکخستنا Intents ---
intents = discord.Intents.all()

# --- فەنکشنا جوانکرنا لاپەڕێن TOS و Privacy ---
def render_page(title, file_path):
    if not os.path.exists(file_path):
        return "<h1>File Not Found</h1>"
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_body = markdown2.markdown(md_content)
    
    return f"""
    <!DOCTYPE html>
    <html lang="ku" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>{title} - HMB MUSIC</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
        <style>
            body {{ font-family: sans-serif; padding: 40px; line-height: 1.6; background-color: #1a1a1a; color: #ffffff; }}
            h1 {{ color: #5865F2; text-align: center; border-bottom: 2px solid #5865F2; padding-bottom: 10px; }}
            div.container {{ max-width: 800px; margin: auto; background: #2c2f33; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            {html_body}
        </div>
    </body>
    </html>
    """

# --- بەشێ وێب سێرڤەری ---
async def web_tos(request):
    return web.Response(text=render_page("Terms of Service", "TOS.md"), content_type='text/html')

async def web_privacy(request):
    return web.Response(text=render_page("Privacy Policy", "PRIVACY.md"), content_type='text/html')

async def web_home(request):
    return web.Response(text="<h1 style='text-align:center; margin-top:100px; font-family:sans-serif;'>HMB MUSIC Bot is Online 🚀</h1>", content_type='text/html')

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.cleanup_task.start()
        
        # --- دەستپێکرنا وێب سێرڤەری ل سەر Railway ---
        app = web.Application()
        app.router.add_get('/', web_home)
        app.router.add_get('/tos', web_tos)
        app.router.add_get('/privacy', web_privacy)
        
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        print(f"✅ Web Server started on port {port}")
        print(f"✅ Commands synced and Cleanup Task started for {self.user}")

    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        folder = 'downloads'
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except:
                    pass

bot = MyBot()

# --- رێکخستنا yt-dlp ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'extractor_args': {'youtube': {'player_client': ['android', 'web_embedded']}},
}
FFMPEG_OPTIONS = {'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

if not os.path.exists('downloads'): os.makedirs('downloads')
queues = {}

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        file_path = next_song['file']
        if os.path.exists(file_path):
            ctx.voice_client.play(discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS), 
                                   after=lambda e: (check_queue(ctx)))

async def play_logic(ctx, search: str):
    if not ctx.author.voice: return await ctx.send("❌ پێدڤییە تو ل ناڤ چەناڵەکێ دەنگی بی!")
    vc = ctx.voice_client or await ctx.author.voice.channel.connect()
    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=True))
        if 'entries' in data and data['entries']: data = data['entries'][0]
        filename = ytdl.prepare_filename(data)
        song_info = {'file': filename, 'title': data.get('title', 'Unknown')}
        if vc.is_playing() or vc.is_paused():
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(song_info)
            await ctx.send(f"➕ هاتە زێدەکرن: **{song_info['title']}**")
        else:
            vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), after=lambda e: (check_queue(ctx)))
            embed = discord.Embed(title="🎶 HMB MUSIC - NOW PLAYING", description=f"**{song_info['title']}**", color=discord.Color.blue())
            if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
            await ctx.send(embed=embed, view=ControlView(ctx))
    except Exception as e: await ctx.send(f"❌ خەلەتییەک چێبوو: {str(e)}")

class ControlView(discord.ui.View):
    def __init__(self, ctx): super().__init__(timeout=None); self.ctx = ctx
    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def play_pause(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing(): vc.pause(); await interaction.response.send_message("Paused ⏸️", ephemeral=True)
        elif vc.is_paused(): vc.resume(); await interaction.response.send_message("Resumed ▶️", ephemeral=True)
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction, button):
        if interaction.guild.voice_client: interaction.guild.voice_client.stop(); await interaction.response.send_message("Skipped ⏭️", ephemeral=True)
    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction, button):
        if interaction.guild.voice_client: queues[interaction.guild.id] = []; await interaction.guild.voice_client.disconnect(); await interaction.response.send_message("Stopped ⏹️", ephemeral=True)

class MultiDropdown(discord.ui.Select):
    def __init__(self, ctx, placeholder, songs):
        options = [discord.SelectOption(label=s[0], description=s[1], value=s[2]) for s in songs]
        super().__init__(placeholder=placeholder, options=options)
        self.ctx = ctx
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🎵 دهێتە لێدان...", ephemeral=True)
        await play_logic(self.ctx, self.values[0])

class YTMusicView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        list1 = [("سترانا ١", "Hunermend", "https://music.youtube.com/watch?v=kFeYV_QO2oo"), ("سترانا ٢", "Hunermend", "https://music.youtube.com/watch?v=FpRC6QYiQ3I")] 
        self.add_item(MultiDropdown(ctx, "📂 لیستا ١ (١-٢٥)", list1))

@bot.hybrid_command(name="yt_music", description="لیستا ١٠٠ گۆرانیێن ئامادەکری")
async def yt_music(ctx):
    embed = discord.Embed(title="🎶 YT MUSIC LIBRARY", description="گۆرانیەکێ هەلبژێرە دا بۆت لێ بدەت.", color=discord.Color.red())
    await ctx.send(embed=embed, view=YTMusicView(ctx))

@bot.hybrid_command(name="play")
async def play(ctx, *, search: str): await ctx.defer(); await play_logic(ctx, search)

@bot.hybrid_command(name="stop")
async def stop(ctx):
    if ctx.voice_client: queues[ctx.guild.id] = []; await ctx.voice_client.disconnect(); await ctx.send("⏹️ موزیک هاتە ڕاوەستاندن.")

@bot.event
async def on_ready(): print(f"✅ {bot.user} is online and ready!")

bot.run(os.getenv("DISCORD_TOKEN"))
