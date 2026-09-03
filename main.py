import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# --- رێکخستنا Intents ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- رێکخستنا yt-dlp بۆ دابەزاندنا خێرا ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'outtmpl': 'downloads/%(id)s.%(ext)s', # فایل د فۆلدەرێ downloads دێ بن
}

FFMPEG_OPTIONS = {'options': '-vn'}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
if not os.path.exists('downloads'): os.makedirs('downloads')

queues = {}

# --- سیستەمێ ڕیزکرنێ (Queue) ---
def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        file_path = next_song['file']
        ctx.voice_client.play(discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS), 
                               after=lambda e: (os.remove(file_path) if os.path.exists(file_path) else None, check_queue(ctx)))

# --- کۆنترۆڵ پانێل (Buttons) ---
class ControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def play_pause(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing(): vc.pause(); await interaction.response.send_message("Paused ⏸️", ephemeral=True)
        elif vc.is_paused(): vc.resume(); await interaction.response.send_message("Resumed ▶️", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction, button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skipped ⏭️", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction, button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Stopped ⏹️", ephemeral=True)

# --- فەرمانا Play (بو یوتیوب و تیکتۆک) ---
@bot.hybrid_command(name="play", description="لێدانا موزیکێ ژ یوتیوب و تیکتۆک")
async def play(ctx, *, search: str):
    await ctx.defer()
    
    if not ctx.author.voice:
        return await ctx.send("❌ پێدڤییە تو ل ناڤ چەناڵەکێ دەنگی بی!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    try:
        # دابەزاندنا فایلێ دەنگی
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=True))
        if 'entries' in data and data['entries']: data = data['entries'][0]
        
        filename = ytdl.prepare_filename(data)
        
        song_info = {'file': filename, 'title': data.get('title', 'Unknown')}

        if vc.is_playing() or vc.is_paused():
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(song_info)
            await ctx.send(f"➕ Added to queue: **{song_info['title']}**")
        else:
            vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), 
                    after=lambda e: (os.remove(filename) if os.path.exists(filename) else None, check_queue(ctx)))
            
            embed = discord.Embed(title="🎶 HMB MUSIC - NOW PLAYING", description=f"**{song_info['title']}**", color=discord.Color.blue())
            if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
            await ctx.send(embed=embed, view=ControlView(ctx))

    except Exception as e:
        await ctx.send(f"❌ خەلەتییەک چێبوو. تکایە ناڤێ سترانێ بنڤیسە د شوینا لایڤ یان وێنەیان.")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ HMB MUSIC IS READY & STABLE")

bot.run(os.getenv("DISCORD_TOKEN"))
