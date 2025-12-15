"""
Fun Engagement Commands - Jokes, stories, riddles, quizzes, and games
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import random
import asyncio

try:
    from utils.embed_helper import EmbedHelper, EmbedColors
    EMBED_HELPER_AVAILABLE = True
except ImportError:
    EMBED_HELPER_AVAILABLE = False


class FunCommands(commands.Cog):
    """Fun engagement commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_riddles = {}  # {user_id: {"question": str, "answer": str, "hints": int}}
        self.active_quizzes = {}  # {user_id: {"questions": list, "current": int, "score": int}}
    
    @app_commands.command(name="joke", description="Get a random AI-generated joke")
    async def joke(self, interaction: discord.Interaction):
        """Generate a joke"""
        await interaction.response.defer()
        
        # Use Gemini for jokes (cheaper/free)
        if self.bot.api_manager:
            try:
                result = await self.bot.api_manager.generate_response(
                    messages=[{"role": "user", "content": "Tell me a funny joke. Keep it clean and appropriate for Discord."}],
                    system_prompt="You are a friendly comedian. Tell clean, family-friendly jokes that are funny and appropriate.",
                    query="joke",
                    detected_language="en"
                )
                
                if result["success"]:
                    joke_text = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="😄 Joke",
                            description=joke_text,
                            color=EmbedColors.KURDISH
                        )
                        embed.set_footer(text=f"⚡ Powered by {result['provider'].capitalize()}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"😄 **Joke**\n\n{joke_text}")
                    return
            except Exception as e:
                print(f"[ERROR] Joke generation failed: {e}")
        
        # Fallback to static jokes
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "What do you call a fake noodle? An impasta!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What's the best thing about Switzerland? I don't know, but the flag is a big plus!"
        ]
        joke = random.choice(jokes)
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="😄 Joke",
                description=joke,
                color=EmbedColors.KURDISH
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"😄 **Joke**\n\n{joke}")
    
    @app_commands.command(name="story", description="Generate a creative story")
    @app_commands.describe(topic="Topic or theme for the story (optional)")
    async def story(self, interaction: discord.Interaction, topic: Optional[str] = None):
        """Generate a creative story"""
        await interaction.response.defer()
        
        prompt = f"Write a short, creative story (2-3 paragraphs). Make it engaging and interesting."
        if topic:
            prompt += f" Topic: {topic}"
        
        if self.bot.api_manager:
            try:
                result = await self.bot.api_manager.generate_response(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a creative storyteller. Write engaging, imaginative stories that captivate readers.",
                    query=prompt,
                    detected_language="en"
                )
                
                if result["success"]:
                    story_text = result["response"]
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="📖 Story" + (f" - {topic}" if topic else ""),
                            description=story_text[:4096],
                            color=EmbedColors.PRIMARY
                        )
                        embed.set_footer(text=f"⚡ Powered by {result['provider'].capitalize()}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"📖 **Story**\n\n{story_text[:2000]}")
                    return
            except Exception as e:
                print(f"[ERROR] Story generation failed: {e}")
        
        await interaction.followup.send("I'm having trouble generating a story right now. Please try again later!")
    
    @app_commands.command(name="riddle", description="Get a riddle to solve")
    async def riddle(self, interaction: discord.Interaction):
        """Get a riddle"""
        await interaction.response.defer()
        
        riddles = [
            {"q": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "a": "echo"},
            {"q": "The more you take, the more you leave behind. What am I?", "a": "footsteps"},
            {"q": "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?", "a": "map"},
            {"q": "What has keys but no locks, space but no room, and you can enter but not go inside?", "a": "keyboard"},
            {"q": "I'm tall when I'm young, and short when I'm old. What am I?", "a": "candle"}
        ]
        
        riddle_data = random.choice(riddles)
        user_id = str(interaction.user.id)
        self.active_riddles[user_id] = {
            "question": riddle_data["q"],
            "answer": riddle_data["a"].lower(),
            "hints": 0
        }
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="🧩 Riddle",
                description=riddle_data["q"],
                color=EmbedColors.WARNING
            )
            embed.set_footer(text="Reply with your answer! Use /riddle-hint for a hint.")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"🧩 **Riddle**\n\n{riddle_data['q']}\n\n*Reply with your answer!*")
    
    @app_commands.command(name="riddle-hint", description="Get a hint for the current riddle")
    async def riddle_hint(self, interaction: discord.Interaction):
        """Get a hint for the current riddle"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.active_riddles:
            await interaction.response.send_message(
                "You don't have an active riddle! Use `/riddle` to get one.",
                ephemeral=True
            )
            return
        
        riddle = self.active_riddles[user_id]
        riddle["hints"] += 1
        
        answer = riddle["answer"]
        if riddle["hints"] == 1:
            hint = f"The answer starts with '{answer[0].upper()}' and has {len(answer)} letters."
        elif riddle["hints"] == 2:
            hint = f"The answer is: {answer[0].upper()}{'*' * (len(answer) - 1)}"
        else:
            hint = f"The answer is: **{answer.upper()}**"
        
        await interaction.response.send_message(f"💡 **Hint {riddle['hints']}:** {hint}", ephemeral=True)
    
    @app_commands.command(name="fact", description="Get a random interesting fact")
    async def fact(self, interaction: discord.Interaction):
        """Get a random fact"""
        facts = [
            "Honey never spoils. Archaeologists have found 3000-year-old honey that's still edible!",
            "Octopuses have three hearts and blue blood.",
            "A group of flamingos is called a 'flamboyance'.",
            "Bananas are berries, but strawberries aren't!",
            "Sharks have been around longer than trees.",
            "A day on Venus is longer than its year.",
            "Wombat poop is cube-shaped!",
            "There are more possible games of chess than atoms in the observable universe."
        ]
        
        fact = random.choice(facts)
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="💡 Did You Know?",
                description=fact,
                color=EmbedColors.INFO
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"💡 **Did You Know?**\n\n{fact}")
    
    @app_commands.command(name="quote", description="Get an inspirational quote")
    async def quote(self, interaction: discord.Interaction):
        """Get an inspirational quote"""
        quotes = [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "It is during our darkest moments that we must focus to see the light. - Aristotle",
            "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill"
        ]
        
        quote = random.choice(quotes)
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="💬 Inspirational Quote",
                description=quote,
                color=EmbedColors.PRIMARY
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"💬 **Quote**\n\n{quote}")
    
    @app_commands.command(name="trivia", description="Start a trivia quiz")
    @app_commands.describe(category="Quiz category")
    @app_commands.choices(category=[
        app_commands.Choice(name="General Knowledge", value="general"),
        app_commands.Choice(name="Science", value="science"),
        app_commands.Choice(name="History", value="history"),
        app_commands.Choice(name="Technology", value="tech")
    ])
    async def trivia(self, interaction: discord.Interaction, category: Optional[app_commands.Choice[str]] = None):
        """Start a trivia quiz"""
        await interaction.response.defer()
        
        cat = category.value if category else "general"
        
        # Generate trivia questions using AI
        if self.bot.api_manager:
            try:
                prompt = f"Generate 5 trivia questions about {cat}. Format: Question? A) Option1 B) Option2 C) Option3 D) Option4. Answer: X"
                result = await self.bot.api_manager.generate_response(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a trivia master. Generate engaging trivia questions with multiple choice answers.",
                    query=prompt,
                    detected_language="en"
                )
                
                if result["success"]:
                    # Parse questions (simplified - in production, better parsing needed)
                    questions_text = result["response"]
                    user_id = str(interaction.user.id)
                    self.active_quizzes[user_id] = {
                        "questions": [questions_text],
                        "current": 0,
                        "score": 0
                    }
                    
                    if EMBED_HELPER_AVAILABLE:
                        embed = EmbedHelper.create_info_embed(
                            title="🎯 Trivia Quiz",
                            description=f"**Category:** {cat.capitalize()}\n\n{questions_text[:2000]}",
                            color=EmbedColors.SUCCESS
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"🎯 **Trivia Quiz - {cat.capitalize()}**\n\n{questions_text[:2000]}")
                    return
            except Exception as e:
                print(f"[ERROR] Trivia generation failed: {e}")
        
        # Fallback
        await interaction.followup.send("I'm having trouble generating trivia right now. Please try again later!")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(FunCommands(bot))
