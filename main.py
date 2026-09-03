import discord
from discord.ext import commands
from discord import app_commands, ui
import yt_dlp
import asyncio
import os

# --- رێکخستنا Intents ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- رێکخستنا موزیکێ (yt-dlp) ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'no_warnings': True,
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
queues = {}

# --- ١. پەنجەرەیا گوهۆڕینا دەنگی (Volume Modal) ---
class VolumeModal(ui.Modal, title="Adjust Volume"):
    volume_input = ui.TextInput(label="Volume (1-200)", placeholder="100", min_length=1, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.source:
            try:
                new_vol = int(self.volume_input.value) / 100
                vc.source.volume = new_vol
                await interaction.response.send_message(f"🔊 دەنگ هاتە گوهۆڕین بۆ: {self.volume_input.value}%", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ تکایە بتنێ ژماران بنڤیسە!", ephemeral=True)

# --- ٢. پەنجەرەیا گەڕیانێ (Search Modal) ---
class SearchModal(ui.Modal, title="Search Music"):
    search_input = ui.TextInput(label="Song Name / Link", placeholder="ناڤێ سترانێ ل ڤێرێ بنڤیسە...", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # ل ڤێرێ مە خەلەتی ڕاست کر (bot.get_command ب کار دئینین)
        play_command = bot.get_command('play')
        ctx = await bot.get_context(interaction.message)
        await interaction.followup.send(f"🔎 دگەڕیێم بۆ: {self.search_input.value}", ephemeral=True)
        await ctx.invoke(play_command, search=self.search_input.value)

# --- ٣. کۆنترۆڵ پانێلا پێشکەفتی ---
class AdvancedControl(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="⏸️ / ▶️", style=discord.ButtonStyle.blurple)
    async def play_pause(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("ڕاوەستا ⏸️", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("بەردەوام بوو ▶️", ephemeral=True)

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skip ⏭️", ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("بۆت دەرکەفت ⏹️", ephemeral=True)

    @ui.button(label="🔊 Vol", style=discord.ButtonStyle.gray)
    async def volume(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(VolumeModal())

    @ui.button(label="🔎 Search", style=discord.ButtonStyle.gray)
    async def search(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SearchModal())

# --- ٤. سیستەمێ ڕیزکرنێ ---
def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        voice = ctx.voice_client
        if voice:
            next_song = queues[ctx.guild.id].pop(0)
            voice.play(next_song, after=lambda e: check_queue(ctx))

# --- ٥. فەرمانا Play (ل ڤێرێ سپۆتیفای و تیکتۆک ڕاست بوون) ---
@bot.hybrid_command(name="play", description="Play music from YouTube, TikTok, or Spotify")
async def play(ctx, *, search: str):
    if not ctx.interaction:
        await ctx.defer()

    if not ctx.author.voice:
        return await ctx.send("❌ پێدڤییە تو ل ناڤ چەناڵەکێ دەنگی بی!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    # سیستەمێ گەڕیانێ بۆ Spotify و TikTok
    query = search
    if "spotify.com" in search or "tiktok.com" in search:
        # ئەگەر لینک بیت، ناڤێ سترانێ ل یوتیوبێ دگەریت
        query = f"ytsearch:{search}"

    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        
        url = data['url']
        title = data['title']
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

        if vc.is_playing() or vc.is_paused():
            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(source)
            await ctx.send(f"➕ زێدە بوو بۆ ڕیزێ: **{title}**")
        else:
            vc.play(source, after=lambda e: check_queue(ctx))
            
            embed = discord.Embed(title="🎶 HMB MUSIC PLAYER", color=discord.Color.blue())
            embed.add_field(name="Now Playing", value=f"**{title}**", inline=False)
            if 'thumbnail' in data:
                embed.set_thumbnail(url=data['thumbnail'])
            
            await ctx.send(embed=embed, view=AdvancedControl())

    except Exception as e:
        await ctx.send(f"❌ خەلەتییەک چێبوو: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ HMB MUSIC IS READY")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
