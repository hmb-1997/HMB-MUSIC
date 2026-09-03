import discord
from discord.ext import commands
from discord import app_commands, ui
import yt_dlp
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# رێکخستنا ب هێزتر بۆ yt-dlp
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
queues = {}

class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="⏸️/▶️", style=discord.ButtonStyle.blurple)
    async def play_pause(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing(): vc.pause()
        elif vc.is_paused(): vc.resume()
        await interaction.response.send_message("Done!", ephemeral=True)

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction, button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skipped!", ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction, button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Stopped!", ephemeral=True)

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        voice = ctx.voice_client
        source = queues[ctx.guild.id].pop(0)
        voice.play(source, after=lambda e: check_queue(ctx))

@bot.hybrid_command(name="play", description="Play music")
async def play(ctx, *, search: str):
    await ctx.defer()
    if not ctx.author.voice: return await ctx.send("Join voice first!")
    
    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    # ئەگەر لینکێ Spotify یان TikTok بیت، ب ناڤ لێ بگەڕە
    query = f"ytsearch:{search}" if "http" not in search or "spotify" in search or "tiktok" in search else search

    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data: data = data['entries'][0]
        
        url = data['url']
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

        if vc.is_playing():
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(source)
            await ctx.send(f"➕ Added to queue: **{data['title']}**")
        else:
            vc.play(source, after=lambda e: check_queue(ctx))
            embed = discord.Embed(title="🎶 Now Playing", description=f"**{data['title']}**", color=discord.Color.blue())
            if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
            await ctx.send(embed=embed, view=ControlPanel())
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ HMB MUSIC IS READY")

bot.run(os.getenv("DISCORD_TOKEN"))
