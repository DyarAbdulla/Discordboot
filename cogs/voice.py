"""
Voice Channel Support - Text-to-speech for voice channels
"""

import discord
from discord.ext import commands
import pyttsx3
import io
import asyncio
from typing import Optional
import os


class VoiceSupport(commands.Cog):
    """Handles voice channel support with text-to-speech"""
    
    def __init__(self, bot):
        """
        Initialize voice support cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.voice_clients = {}
        self.tts_engine = None
        
        # Initialize TTS engine
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.8)  # Volume
        except Exception as e:
            print(f"Warning: Could not initialize TTS engine: {e}")
    
    @commands.command(name="join")
    async def join_voice(self, ctx: commands.Context):
        """
        Join the voice channel the user is in
        
        Args:
            ctx: Command context
        """
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel!")
            return
        
        channel = ctx.author.voice.channel
        
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        
        await ctx.send(f"✅ Joined {channel.name}!")
    
    @commands.command(name="leave")
    async def leave_voice(self, ctx: commands.Context):
        """
        Leave the voice channel
        
        Args:
            ctx: Command context
        """
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Left the voice channel!")
        else:
            await ctx.send("❌ I'm not in a voice channel!")
    
    @commands.command(name="speak")
    async def speak_command(self, ctx: commands.Context, *, text: str):
        """
        Convert text to speech and play in voice channel
        
        Args:
            ctx: Command context
            text: Text to speak
        """
        if not ctx.voice_client:
            await ctx.send("❌ I need to be in a voice channel! Use `!join` first.")
            return
        
        if not self.tts_engine:
            await ctx.send("❌ Text-to-speech is not available on this system.")
            return
        
        try:
            # Generate speech
            await ctx.send("🔊 Speaking...")
            
            # Save to file
            audio_file = "temp_speech.wav"
            self.tts_engine.save_to_file(text, audio_file)
            self.tts_engine.runAndWait()
            
            # Play audio
            if os.path.exists(audio_file):
                source = discord.FFmpegPCMAudio(audio_file)
                ctx.voice_client.play(source)
                
                # Wait for playback to finish
                while ctx.voice_client.is_playing():
                    await asyncio.sleep(0.5)
                
                # Clean up
                os.remove(audio_file)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
            if os.path.exists("temp_speech.wav"):
                os.remove("temp_speech.wav")
    
    async def speak_text(self, voice_client: discord.VoiceClient, text: str):
        """
        Speak text in voice channel (internal method)
        
        Args:
            voice_client: Voice client to use
            text: Text to speak
        """
        if not self.tts_engine or not voice_client:
            return
        
        try:
            audio_file = "temp_speech.wav"
            self.tts_engine.save_to_file(text, audio_file)
            self.tts_engine.runAndWait()
            
            if os.path.exists(audio_file):
                source = discord.FFmpegPCMAudio(audio_file)
                voice_client.play(source)
                
                while voice_client.is_playing():
                    await asyncio.sleep(0.5)
                
                os.remove(audio_file)
        except Exception as e:
            print(f"Error in speak_text: {e}")
            if os.path.exists("temp_speech.wav"):
                os.remove("temp_speech.wav")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(VoiceSupport(bot))

