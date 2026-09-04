import discord
from discord.ext import commands, tasks # tasks هاتە زێدەکرن
from discord import app_commands
import yt_dlp
import asyncio
import os
import shutil # بۆ پاقژکرنا فۆڵدەران

# --- رێکخستنا Intents ---
intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.cleanup_task.start() # دەستپێکرنا سیستەمێ پاقژکرنێ
        print(f"✅ Commands synced and Cleanup Task started for {self.user}")

    # --- سیستەمێ پاقژکرنا داتایێن کاتی (هەر ١٠ خولەکان) ---
    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        folder = 'downloads'
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    # ئەگەر فایل نوکە ناهێتە لێدان، ڕەشکە
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    print(f"♻️ Cleaned: {filename}")
                except Exception as e:
                    # ئەگەر فایل نوکە یێ "In Use" بیت دێ هێلیت بۆ جارەکا دی
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

if not os.path.exists('downloads'):
    os.makedirs('downloads')

queues = {}

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        file_path = next_song['file']
        if os.path.exists(file_path):
            ctx.voice_client.play(discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS), 
                                   after=lambda e: (check_queue(ctx)))

# --- مەکینا لێدانا موزیکێ ---
async def play_logic(ctx, search: str):
    if not ctx.author.voice:
        return await ctx.send("❌ پێدڤییە تو ل ناڤ چەناڵەکێ دەنگی بی!")

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
            vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), 
                    after=lambda e: (check_queue(ctx)))
            embed = discord.Embed(title="🎶 HMB MUSIC - NOW PLAYING", description=f"**{song_info['title']}**", color=discord.Color.blue())
            if 'thumbnail' in data: embed.set_thumbnail(url=data['thumbnail'])
            await ctx.send(embed=embed, view=ControlView(ctx))
    except Exception as e:
        await ctx.send(f"❌ خەلەتییەک چێبوو: {str(e)}")

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

# --- لیستا گۆرانیێن هەلبژارتی (Dropdowns) ---
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
        list1 = [("سترانا ١", "Hunermend", "https://music.youtube.com/watch?v=kFeYV_QO2oo&si=3ry1V7TfAza4BzvA"), ("سترانا ٢", "Hunermend", "https://music.youtube.com/watch?v=FpRC6QYiQ3I&si=BRqpWPUT0eYDiSNM")] 
        list2 = [("سترانا ٢٦", "Hunermend", "https://music.youtube.com/watch?v=i97rBoSUvWo&si=bgVl8NAjEO78BLAy")]
        list3 = [("سترانا ٥١", "Hunermend", "https://music.youtube.com/watch?v=ay8V-XqEmi8&si=Omkvb3kNFyue-mnT")]
        list4 = [("سترانا ٧٦", "Hunermend", "https://music.youtube.com/watch?v=Hs05RfeCsf8&si=_mTpPxvgqQx7CXv9")]

        self.add_item(MultiDropdown(ctx, "📂 لیستا ١ (١-٢٥)", list1))
        self.add_item(MultiDropdown(ctx, "📂 لیستا ٢ (٢٦-٥٠)", list2))
        self.add_item(MultiDropdown(ctx, "📂 لیستا ٣ (٥١-٧٥)", list3))
        self.add_item(MultiDropdown(ctx, "📂 لیستا ٤ (٧٦-١٠٠)", list4))

# --- فەرمانێن بۆتی ---

@bot.hybrid_command(name="yt_music", description="لیستا ١٠٠ گۆرانیێن ئامادەکری")
async def yt_music(ctx):
    embed = discord.Embed(title="🎶 YT MUSIC LIBRARY", description="گۆرانیەکێ هەلبژێرە دا بۆت لێ بدەت.", color=discord.Color.red())
    await ctx.send(embed=embed, view=YTMusicView(ctx))

@bot.hybrid_command(name="play", description="لێدانا موزیکێ ب لینک یان ناڤ")
async def play(ctx, *, search: str):
    await ctx.defer()
    await play_logic(ctx, search)

@bot.hybrid_command(name="stop", description="ڕاوەستاندنا موزیکێ")
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ موزیک هاتە ڕاوەستاندن.")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")

bot.run(os.getenv("DISCORD_TOKEN"))
