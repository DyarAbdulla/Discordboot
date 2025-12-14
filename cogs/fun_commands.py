"""
Fun Commands Cog - Joke, quote, and meme commands
"""

import discord
from discord.ext import commands
import aiohttp
import random
from typing import Optional


class FunCommands(commands.Cog):
    """Handles fun commands like jokes, quotes, and memes"""
    
    def __init__(self, bot):
        """
        Initialize fun commands cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a fake noodle? An impasta!",
            "Why did the math book look so sad? Because it had too many problems!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't programmers like nature? It has too many bugs!",
            "How do you comfort a JavaScript bug? You console it!",
            "Why do Python developers prefer dark mode? Because light attracts bugs!",
            "What's a programmer's favorite hangout place? Foo Bar!"
        ]
        
        self.quotes = [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs",
            "Life is what happens to you while you're busy making other plans. - John Lennon",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "It is during our darkest moments that we must focus to see the light. - Aristotle",
            "The only impossible journey is the one you never begin. - Tony Robbins",
            "In the middle of difficulty lies opportunity. - Albert Einstein",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
            "The way to get started is to quit talking and begin doing. - Walt Disney",
            "Don't let yesterday take up too much of today. - Will Rogers"
        ]
    
    @commands.command(name="joke")
    async def joke_command(self, ctx: commands.Context):
        """
        Tell a random joke
        
        Args:
            ctx: Command context
        """
        joke = random.choice(self.jokes)
        
        embed = discord.Embed(
            title="😄 Joke",
            description=joke,
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="quote")
    async def quote_command(self, ctx: commands.Context):
        """
        Get an inspirational quote
        
        Args:
            ctx: Command context
        """
        quote = random.choice(self.quotes)
        
        embed = discord.Embed(
            title="💭 Inspirational Quote",
            description=quote,
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="meme")
    async def meme_command(self, ctx: commands.Context):
        """
        Get a random meme from Reddit
        
        Args:
            ctx: Command context
        """
        subreddits = ["memes", "dankmemes", "wholesomememes", "ProgrammerHumor"]
        subreddit = random.choice(subreddits)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=50"
                headers = {"User-Agent": "DiscordBot/1.0"}
                
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = [
                            post["data"] for post in data["data"]["children"]
                            if post["data"]["post_hint"] == "image" and not post["data"]["over_18"]
                        ]
                        
                        if posts:
                            post = random.choice(posts)
                            
                            embed = discord.Embed(
                                title=post["title"][:256],
                                url=f"https://reddit.com{post['permalink']}",
                                color=discord.Color.orange()
                            )
                            embed.set_image(url=post["url"])
                            embed.set_footer(text=f"r/{subreddit} • 👍 {post['ups']}")
                            
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send("Couldn't find a suitable meme. Try again!")
                    else:
                        await ctx.send("Couldn't fetch memes right now. Try again later!")
        except Exception as e:
            await ctx.send("Oops! Something went wrong fetching a meme. Try again!")
            if self.bot.config.get("enable_logging", True):
                print(f"Meme command error: {e}")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(FunCommands(bot))

