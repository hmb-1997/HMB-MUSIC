import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil

# --- رێکخستنا Intents ---
intents = discord.Intents.all()

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.clean_data_task.start() # دەستپێکرنا پاقژکرنا ئۆتۆماتیکی
        print(f"✅ Slash Commands Synced and Cleaner Started.")

    # --- سیستەمێ پاقژکرنا داتایان هەر ١٠ خولەکان ---
    @tasks.loop(minutes=10)
    async def clean_data_task(self):
        """ئەڤە داتایێن کاتی پاقژ دکەت دا سێرڤەر گران نەبیت"""
        try:
            # پاقژکرنا فۆلدەرێ کاتی یێ yt-dlp
            if os.path.exists('~/.cache/yt-dlp'):
                shutil.rmtree('~/.cache/yt-dlp', ignore_errors=True)
            
            # ئەگەر هەر فایلەکێ دەنگی یێ کاتی مابیت دێ هێتە ژێبرن
            for file in os.listdir('.'):
                if file.endswith((".webm", ".m4a", ".mp3", ".pydat")):
                    os.remove(file)
            print("♻️ داتایێن کاتی هاتنە پاقژکرن (10-minute reset).")
        except Exception as e:
            print(f"❌ Error during cleaning: {e}")

bot = MusicBot()

# --- رێکخستنا موزیکێ ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# --- کۆنترۆڵ پانێل (Buttons) ---
class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ Stop", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ Resume", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("⏹️ بۆت دەرکەفت", ephemeral=True)

    @discord.ui.button(label="🔊 Vol +", style=discord.ButtonStyle.gray)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = min(vc.source.volume + 0.1, 2.0)
            await interaction.response.send_message(f"🔊 {int(vc.source.volume*100)}%", ephemeral=True)

    @discord.ui.button(label="🔉 Vol -", style=discord.ButtonStyle.gray)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = max(vc.source.volume - 0.1, 0.0)
            await interaction.response.send_message(f"🔉 {int(vc.source.volume*100)}%", ephemeral=True)

# --- فەرمانا Play ---
@bot.hybrid_command(name="play", description="لێدانا موزیکێ ژ YouTube, TikTok, Spotify")
async def play(ctx, *, search: str):
    await ctx.defer()
    if not ctx.author.voice:
        return await ctx.send("❌ پێدڤییە تو د چەناڵەکێ دەنگی دابی!")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
    if 'entries' in data: data = data['entries'][0]
    
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS))
    vc.play(source)

    embed = discord.Embed(title="🎶 نوکە لێدەت", description=f"**{data['title']}**", color=discord.Color.green())
    await ctx.send(embed=embed, view=ControlPanel())

@bot.event
async def on_ready():
    print(f'🤖 بۆت یێ ئامادەیە: {bot.user}')

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
