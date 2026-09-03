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
        self.clean_data_task.start()
        print(f"✅ HMB MUSIC IS READY")

    @tasks.loop(minutes=10)
    async def clean_data_task(self):
        try:
            for file in os.listdir('.'):
                if file.endswith((".webm", ".m4a", ".mp3", ".pydat")):
                    os.remove(file)
            print("♻️ Data cleaned.")
        except:
            pass

bot = MusicBot()

# --- رێکخستنا موزیکێ ---
YTDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'auto'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ Paused", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("⏹️ Stopped", ephemeral=True)

@bot.hybrid_command(name="play", description="لێدانا موزیکێ")
async def play(ctx, *, search: str):
    await ctx.defer()
    if not ctx.author.voice:
        return await ctx.send("❌ تو یێ د چەناڵەکێ دەنگی دا نینی!")

    # پەیوەندی ب چەناڵی
    try:
        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect()
        else:
            vc = ctx.voice_client
    except Exception as e:
        return await ctx.send(f"❌ نەشێم پەیوەندیێ بکەم: {e}")

    # کێشانا دەنگی
    try:
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        if 'entries' in data: data = data['entries'][0]
        
        # لێدانا موزیکێ
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS))
        vc.play(source)

        embed = discord.Embed(title="🎶 HMB MUSIC", description=f"**{data['title']}**", color=discord.Color.blue())
        await ctx.send(embed=embed, view=ControlPanel())
    except Exception as e:
        await ctx.send(f"❌ خەلەتی: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
