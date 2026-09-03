import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil

# --- ١. رێکخستنا Intents و دەستهەلاتان ---
intents = discord.Intents.all()

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync کردنا فەرمانێن Slash (/) دا ل دیسکۆردێ دیار بن
        await self.tree.sync()
        self.clean_data_task.start() # دەستپێکرنا پاقژکەرێ ئۆتۆماتیکی
        print(f"✅ HMB MUSIC IS READY - Logged in as {self.user}")

    # --- ٢. سیستەمێ پاقژکرنا داتایان هەر ١٠ خولەکان ---
    @tasks.loop(minutes=10)
    async def clean_data_task(self):
        try:
            for file in os.listdir('.'):
                if file.endswith((".webm", ".m4a", ".mp3", ".pydat", ".temp")):
                    os.remove(file)
            print("♻️ Temporary data cleaned.")
        except Exception as e:
            print(f"Cleaner Error: {e}")

bot = MusicBot()

# --- ٣. رێکخستنا موزیکێ (yt-dlp & FFmpeg) ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# --- ٤. کۆنترۆڵ پانێل (Buttons) ---
class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ موزیک هاتە ڕاوەستاندن", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ موزیک بەردەوام بوو", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹️ بۆت دەرکەفت و موزیک ڕاوەستا", ephemeral=True)

# --- ٥. فەرمانا Play (Hybrid: !play یان /play) ---
@bot.hybrid_command(name="play", description="لێدانا موزیکێ ژ YouTube, TikTok, Spotify")
@app_commands.describe(search="ناڤ یان لینکا سترانێ")
async def play(ctx, *, search: str):
    await ctx.defer() # بۆ هندێ بۆت "Thinking" نیشان بدەت

    if not ctx.author.voice:
        return await ctx.send("❌ تو پێدڤییە ل ناڤ چەناڵەکێ دەنگی بی!")

    # پەیوەندی ب چەناڵی
    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client

    try:
        # کێشانا زانیاریێن ڤیدیۆیێ
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        url = data['url']
        title = data['title']

        # ئەگەر سترانەکا دی یا لێدەت، وێ ڕاوەستینە
        if vc.is_playing():
            vc.stop()

        # لێدانا موزیکێ
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
