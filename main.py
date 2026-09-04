import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os

# --- رێکخستنا Intents ---
intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Commands synced for {self.user}")

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
        ctx.voice_client.play(discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS), 
                               after=lambda e: (os.remove(file_path) if os.path.exists(file_path) else None, check_queue(ctx)))

# --- فرمانا لێدانا موزیکێ ---
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
            await ctx.send(f"➕ Added to queue: **{song_info['title']}**")
        else:
            vc.play(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), 
                    after=lambda e: (os.remove(filename) if os.path.exists(filename) else None, check_queue(ctx)))
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

# --- لیستا گۆرانیێن تایبەت ---
class MultiDropdown(discord.ui.Select):
    def __init__(self, ctx, placeholder, options_data):
        options = [
            discord.SelectOption(label=name, description=desc, value=link)
            for name, desc, link in options_data
        ]
        super().__init__(placeholder=placeholder, options=options)
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🎵 دهێتە ئامادەکرن: {self.values[0]}", ephemeral=True)
        await play_logic(self.ctx, self.values[0])

class SongListView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        
        # ل ڤێرە گۆرانیێن خۆ زێدە بکە (هەر لیستەک ٢٥ گۆرانی)
        # نموونە: ("ناڤێ سترانێ", "ناڤێ هونەرمەندی", "لینکا یوتیوب")
        
        songs_part1 = [
            ("سترانا ١", "Hunermend 1", "https://www.youtube.com/watch?v=1"),
            ("سترانا ٢", "Hunermend 2", "https://www.youtube.com/watch?v=2"),
            # هەتا ٢٥ دانە ل ڤێرە زێدە بکە...
        ]
        
        songs_part2 = [
            ("سترانا ٢٦", "Hunermend 26", "https://www.youtube.com/watch?v=26"),
            # هەتا ٢٥ دانە ل ڤێرە زێدە بکە...
        ]

        songs_part3 = [
            ("سترانا ٥١", "Hunermend 51", "https://www.youtube.com/watch?v=51"),
            # هەتا ٢٥ دانە ل ڤێرە زێدە بکە...
        ]

        songs_part4 = [
            ("سترانا ٧٦", "Hunermend 76", "https://www.youtube.com/watch?v=76"),
            # هەتا ٢٥ دانە ل ڤێرە زێدە بکە...
        ]

        # زێدەکرنا لیستێن دایە ل سەر سکرینێ
        if songs_part1: self.add_item(MultiDropdown(ctx, "📂 لیستا ١ (١-٢٥)", songs_part1))
        if songs_part2: self.add_item(MultiDropdown(ctx, "📂 لیستا ٢ (٢٦-٥٠)", songs_part2))
        if songs_part3: self.add_item(MultiDropdown(ctx, "📂 لیستا ٣ (٥١-٧٥)", songs_part3))
        if songs_part4: self.add_item(MultiDropdown(ctx, "📂 لیستا ٤ (٧٦-١٠٠)", songs_part4))

# --- فەرمانێن بۆتی ---

@bot.hybrid_command(name="yt_music", description="لیستەکا ١٠٠ موزیکێن ئامادەکری")
async def yt_music(ctx):
    embed = discord.Embed(
        title="🎵 HMB MUSIC LIBRARY",
        description="گۆرانیەکێ ژ لیستێن خوارێ هەلبژێرە دا بۆت دەست ب لێدانێ بکەت.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=SongListView(ctx))

@bot.hybrid_command(name="play", description="لێدانا موزیکێ ب لینک یان ناڤ")
@app_commands.describe(search="ناڤ یان لینکا موزیکێ")
async def play(ctx, *, search: str):
    await ctx.defer()
    await play_logic(ctx, search)

@bot.hybrid_command(name="stop", description="ڕاوەستاندنا موزیکێ")
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ موزیک هاتە ڕاوەستاندن.")
    else:
        await ctx.send("❌ بۆت یێ د ناڤ چو چەناڵان دا نینە!")

@bot.hybrid_command(name="skip", description="چوونە سەر موزیکا داهاتی")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ موزیک هاتە بازدان.")
    else:
        await ctx.send("❌ چو موزیک ناهێنە لێدان نوکە!")

@bot.hybrid_command(name="pause", description="ڕاوەستاندنا کاتی")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ موزیک هاتە ڕاوەستاندن.")

@bot.hybrid_command(name="resume", description="بەردەوامکرنا موزیکێ")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ موزیک دووبارە دەستپێکرەڤە.")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")

bot.run(os.getenv("DISCORD_TOKEN"))
