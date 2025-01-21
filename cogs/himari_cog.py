import asyncio
import aiohttp
import discord
import logging
import logging.handlers
import yt_dlp as youtube_dl
from discord.ext import commands
from discord import slash_command

TTV_STREAM="https://twitch.tv/lamentfulcyberia"

# Suppress youtube_dl output
youtube_dl.utils.bug_reports_message = lambda: ''

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.original = source
        
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = asyncio.get_event_loop()
        print(f"Using event loop: {loop}")
        print(f"Running extract_info in executor for URL: {url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
        }
        
        ffmpeg_options = {
            'options': '-vn'
        }
    
        # Wrapping the extraction process inside the executor
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(
                url, 
                download=not stream)
            )
            if 'entries' in data:
                data = data['entries'][0]
            
            filename = data['url'] if stream else ydl.prepare_filename(data)
            print(f"Extracted filename: {filename}")
            return cls(
                discord.FFmpegPCMAudio(filename, **ffmpeg_options), 
                data=data
            )
     
   # async def cleanup(self):
        # Override cleanup to close session and handle original
   #     if self.session:
   #         await self.session.close()
   #     if hasattr(self, 'original') and self.original:
   #         await self.original.cleanup()
        
#class AudioRecorder(discord.sinks.WaveSink):
    #TODO  


class Himari(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        # Use this variable to store the currently playing music track
        self.currently_playing = None
        self.current_player = None
        self.session = aiohttp.ClientSession(loop=asyncio.get_event_loop())
        print('Himari cog loaded!')
        
    async def cog_unload(self):
        print("Himari cog unloaded~!")
    
    '''COMMANDS'''
    # Change Himari's current status.
    @commands.command(name='set_status')
    async def set_status(self, ctx, activity_type: str, *, status_msg: str):
        activity = None
            
        if activity_type.lower() == 'playing':
            activity = discord.Game(name=status_msg)
        elif activity_type.lower() == 'streaming':
            activity = discord.Streaming(name=status_msg, url=TTV_STREAM)
        elif activity_type.lower() == 'listening':
            activity = discord.Activity(type=discord.ActivityType.listening, name=status_msg)
        elif activity_type.lower() == 'watching':
            activity = discord.Activity(type=discord.ActivityType.watching, name=status_msg)
                
        if activity:
            await self.bot.change_presence(activity=activity)
            await ctx.send(f'Status updated to: {activity_type.capitalize()} {status_msg}!')
        else:
            await ctx.send(
                'Invalid activity type. Choose from: playing, streaming, listening, or \
                    watching, please!'
                )
    
    # Reset Himari's status to Online
    @commands.command(name='reset_status')
    async def reset_status(self, ctx):
        await self.bot.change_presence(activity=None)
        await ctx.send('Status reset to default!')
            
    # Joins a voice channel
    @commands.command(name='join')
    async def join(self, ctx):
        if not ctx.author.voice:
            await ctx.send("I can't join your voice chat if you're not in a channel!")
            return
            
        try:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"Yay! I joined {channel}!")
        except asyncio.TimeoutError:
            await ctx.send("It took too long to join the voice channel!")
        except discord.ClientException:
            await ctx.send("I'm already connected to voice!")
        except discord.Forbidden:
            await ctx.send("I don't have permission to join! Hmph!")
    
    # Leave the currently connected voice channel
    @commands.command(name='leave')
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Bye for now!")
        else:
            await ctx.send("Uhhh... I'm not in a voice channel. Awkward.")
            
    # Streams the audio from a Youtube URL using yt_dlp and FFmpegExtractAudio 
    @commands.command(name='play')
    async def play(self, ctx, url: str):
        if not ctx.voice_client:
            await ctx.send("I'm not in a voice channel! Use the `join` command first.")
            return
        
        try:
            async with ctx.typing():
                 # Create the YTDLSourceinstance and assign it to self.current_player
                 self.current_player = await YTDLSource.from_url(
                    url, loop=asyncio.get_running_loop(), stream=True
                )
                
            # Play the audio in the voice channel
            ctx.voice_client.play(
                self.current_player, 
                after=lambda e: print(f'Player error: {e}') if e else None
            )
                    
            # Set the title of the currently playing song
            self.currently_playing = self.current_player.title 
            await ctx.send(f'Now playing: **{self.current_player.title}**!')
                
        except youtube_dl.utils.DownloadError:
            await ctx.send("Hmmm... I couldn't find let alone stream that URL... Try a \
                           valid link, perhaps?")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command(name='now_playing')
    async def now_playing(self, ctx):
        if self.currently_playing:
            await ctx.send(f'Currently playing: **{self.currently_playing}**')
        else:
            await ctx.send("There's nothing playing right now.")
    
    # Pause the audio stream from youtube
    @commands.command(name="pause")
    async def pause(self,ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("I paused the playback for you!")
        else:
            await ctx.send("Ummmm... there's no song playing right now...")
       
    # Resume the audio stream from youtube
    @commands.command(name="resume")
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Alright, let's jam again!! Playback resumed!")
        elif ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.send("We're already jamming!! Playback is not paused!")
        else:
            await ctx.send(
                "I'm not streaming any audio. How can I resume what isn't playing?"
            )
    # Stops the audio stream from youtube 
    @commands.command(name='stop')
    async def stop(self, ctx):
        if not ctx.voice_client:
            await ctx.send("I'm not in a voice channel! Use the `join` command first.")
            return
            
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            if self.current_player:
                self.current_player.close()
            self.currently_playing = None
            self.current_player = None
            await ctx.send("Playback stopped!")
        else:
            await ctx.send("There's no audio playing!")
    
    # Cleanly disconnects and stops Himari
    @commands.command(name='shutdown')
    async def shutdown(self, ctx):
        await ctx.send("Shutting down gracefully... as a lady should.")
        if self.current_player:
            self.current_player.cleanup()
        await self.bot.close()     
    
    '''EVENTS'''
    # Event handler that lets us know Himari-chan has successfully logged in to Discord
    @commands.Cog.listener(once=True)
    async def on_ready(self):
        print(f'Hihihi! Himari is logged in as {self.bot.user} and ready!')
        # Set Himari's status
        await self.bot.change_presence(
            status=discord.Status.idle, 
            activity=discord.Game("3 Girls")
        )
    
    # Event handler listening for members to join the server
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        if guild.system_channel is not None:
            to_send = f'{member.mention} to {guild.name}!'
    
    # Event handler listening for messages to be sent
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return 
        
        if message.content.startswith('hello'):
            await message.channel.send(f'Hi, {message.author}!')
        
        print(f'Message from {message.author}: {message.content}')
    
    # Event handler listening for errors in command invocation
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.error(f'Error occurred in command {ctx.command}: {error}')
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please, provide all required arguments!')
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send('Grrr... Hinata, find Meido now! An error occurred during my \
                           command execution!')
        else:
            logging.exception(f"Unexpected error: {error}")
    
    #@commands.Cog.listener()
    #async def on_reaction_add(self, reaction, user):
        #TODO
    
    @commands.Cog.listener()
    async def on_disconnect(self):
        print("Disconnecting! I'm cleaning up resources!")
        if not self.bot.is_closed():
            await self.bot.close()
        else:
            print("Himari successfully disconnected already!")
    
    # For more info on setting up loggers visit the discord.py docs: 
    # https://discordpy.readthedocs.io/en/latest/logging.html
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    logging.getLogger('discord.http').setLevel(logging.INFO)
    
    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024, # 32 MiB
        backupCount=5,
)
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(
        '[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def setup(bot):
    bot.add_cog(Himari(bot))
