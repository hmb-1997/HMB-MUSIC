import discord
from discord.ext import commands
from discord import app_commands, ui
import yt_dlp
import asyncio
import os

# --- رێکخستنا Intents ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- رێکخستنا موزیکێ ---
YTDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'auto'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

queues = {}

# --- ١. پەنجەرەیا گوهۆڕینا دەنگی (Volume Modal) ---
class VolumeModal(ui.Modal, title="Adjust Volume"):
    volume_input = ui.TextInput(label="Volume (1-200)", placeholder="ژمارەکێ بنڤیسە...", min_length=1, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vol = int(self.volume_input.value) / 100
            vc.source.volume = vol
            await interaction.response.send_message(f"🔊 دەنگ هاتە گوهۆڕین بۆ: {self.volume_input.value}%", ephemeral=True)

# --- ٢. پەنجەرەیا گەڕیانێ (Search Modal) ---
class SearchModal(ui.Modal, title="Search Music"):
    search_input = ui.TextInput(label="Song Name / Link", placeholder="ناڤێ سترانێ ل ڤێرێ بنڤیسە...", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # ل ڤێرێ فەرمانا play دووبارە دهێتە بانگکرن
        command = bot.get_hybrid_command('play')
        await interaction.followup.send(f"🔎 دگەڕیێم بۆ: {self.search_input.value}", ephemeral=True)
        await interaction.channel.send(f"!play {self.search_input.value}")

# --- ٣. کۆنترۆڵ پانێلا پێشکەفتی (Advanced Control Panel) ---
class AdvancedControl(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="⏮️", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("ئەڤ تایبەتمەندییە د وەشانا داهاتی دا دێ هێت..", ephemeral=True)

    @ui.button(label="⏸️ / ▶️", style=discord.ButtonStyle.blurple)
    async def play_pause(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("ڕاوەستا ⏸️", ephemeral=True)
        else:
            vc.resume()
            await interaction.response.send_message("بەردەوام بوو ▶️", ephemeral=True)

    @ui.button(label="⏭️", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skip ⏭️", ephemeral=True)

    @ui.button(label="⏹️", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("بۆت دەرکەفت ⏹️", ephemeral=True)

    @ui.button(label="🔊 Volume", style=discord.ButtonStyle.gray, row=1)
    async def volume(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(VolumeModal())

    @ui.button(label="🔎 Search", style=discord.ButtonStyle.gray, row=1)
    async def search(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SearchModal())

# --- ٤. فەرمانا Play ---
def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        voice = ctx.voice_client
        source = queues[ctx.guild.id].pop(0)
        voice.play(source, after=lambda e: check_queue(ctx))

@bot.hybrid_command(name="play", description="Play music from any link")
async def play(ctx, *, search: str):
    if not ctx.interaction: await ctx.defer()
    else: await ctx.defer()

    if not ctx.author.voice:
        return await ctx.send("❌ Join a voice channel!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
    if 'entries' in data: data = data['entries'][0]
    
    url = data['url']
    title = data['title']
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

    if vc.is_playing() or vc.is_paused():
        if ctx.guild.id not in queues: queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(source)
        await ctx.send(f"➕ Added to queue: **{title}**")
    else:
        vc.play(source, after=lambda e: check_queue(ctx))
        
        embed = discord.Embed(title="🎶 HMB MUSIC PLAYER", color=discord.Color.from_rgb(47, 49, 54))
        embed.add_field(name="Now Playing", value=f"**{title}**", inline=False)
        embed.add_field(name="Requested By", value=ctx.author.mention, inline=True)
        if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
        
        await ctx.send(embed=embed, view=AdvancedControl())

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ HMB MUSIC IS READY")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
