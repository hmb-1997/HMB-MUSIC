import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import shutil

# --- رێکخستنا Intents ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- رێکخستنا موزیکێ ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'nocheckcertificate': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# --- سیستەمێ ڕیزکرنێ (Queue) ---
queues = {}

def check_queue(ctx):
    if queues[ctx.guild.id]:
        voice = ctx.voice_client
        source = queues[ctx.guild.id].pop(0)
        voice.play(source, after=lambda e: check_queue(ctx))

# --- کلاسیک کۆنترۆڵ پانێل (Professional UI) ---
class ClassicControl(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.gray)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("موزیک ڕاوەستا ⏸️", ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.green)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("بەردەوام بوو ▶️", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("چووە سەر سترانا دی ⏭️", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("بۆت دەرکەفت ⏹️", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ HMB MUSIC IS ONLINE: {bot.user}")

@bot.hybrid_command(name="play", description="لێدانا موزیکێ ژ YouTube, TikTok, Spotify")
async def play(ctx, *, search: str):
    await ctx.defer()
    
    if not ctx.author.voice:
        return await ctx.send("❌ پێدڤییە ل ناڤ چەناڵێ دەنگی بی!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    # ئەگەر لینکێ سپۆتیفای بیت
    if "spotify.com" in search:
        await ctx.send("🔍 زانیاریێن سپۆتیفای دهێنە کێشان...")
        # ل ڤێرێ ب تنێ ناڤێ سترانێ ل یوتیوبێ دگەریت
        search = f"{search} lyrics" 

    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        if 'entries' in data: data = data['entries'][0]
        
        url = data['url']
        title = data['title']
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

        guild_id = ctx.guild.id
        if guild_id not in queues:
            queues[guild_id] = []

        if vc.is_playing() or vc.is_paused():
            queues[guild_id].append(source)
            await ctx.send(f"➕ زێدە بوو بۆ ڕیزێ: **{title}**")
        else:
            vc.play(source, after=lambda e: check_queue(ctx))
            
            embed = discord.Embed(title="📀 HMB MUSIC - NOW PLAYING", color=0x2f3136)
            embed.add_field(name="ستران", value=f"**{title}**", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
            
            await ctx.send(embed=embed, view=ClassicControl(ctx))

    except Exception as e:
        await ctx.send(f"❌ خەلەتی: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
