"""
Slash Commands Cog - Modern Discord slash commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional


class SlashCommands(commands.Cog):
    """Handles Discord slash commands"""
    
    def __init__(self, bot):
        """
        Initialize slash commands cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="Your question")
    async def ask_slash(self, interaction: discord.Interaction, question: str):
        """Slash command to ask questions"""
        await interaction.response.defer()
        
        # Get conversation cog
        conversation_cog = self.bot.get_cog("Conversation")
        if not conversation_cog:
            await interaction.followup.send("❌ Conversation system not available!")
            return
        
        # Check rate limit
        if not conversation_cog._check_rate_limit(interaction.user.id):
            await interaction.followup.send("I'm being rate limited. Please wait a moment before asking again.")
            return
        
        try:
            server_id = interaction.guild.id if interaction.guild else None
            
            response = await conversation_cog._generate_response(
                channel_id=interaction.channel.id,
                user_message=question,
                user_id=interaction.user.id,
                server_id=server_id
            )
            
            # Truncate if too long
            max_length = self.bot.config.get("max_message_length", 2000)
            if len(response) > max_length:
                response = response[:max_length-3] + "..."
            
            await interaction.followup.send(response)
        except Exception as e:
            await interaction.followup.send("I'm having trouble connecting to my AI brain, please try again!")
    
    @app_commands.command(name="clear", description="Clear conversation history for this channel")
    async def clear_slash(self, interaction: discord.Interaction):
        """Slash command to clear conversation history"""
        conversation_cog = self.bot.get_cog("Conversation")
        if conversation_cog and conversation_cog.context_manager:
            conversation_cog.context_manager.clear_context(interaction.channel.id)
        
        await interaction.response.send_message("✅ Conversation history cleared for this channel!", ephemeral=True)
    
    @app_commands.command(name="personality", description="Change bot's personality")
    @app_commands.describe(personality="Personality type")
    @app_commands.choices(personality=[
        app_commands.Choice(name="Friendly", value="friendly"),
        app_commands.Choice(name="Professional", value="professional"),
        app_commands.Choice(name="Funny", value="funny"),
        app_commands.Choice(name="Helpful", value="helpful")
    ])
    async def personality_slash(
        self,
        interaction: discord.Interaction,
        personality: app_commands.Choice[str]
    ):
        """Slash command to change personality"""
        conversation_cog = self.bot.get_cog("Conversation")
        if conversation_cog and conversation_cog.context_manager and interaction.guild:
            conversation_cog.context_manager.set_user_preference(
                interaction.guild.id,
                interaction.user.id,
                "personality",
                personality.value
            )
            conversation_cog.context_manager.save_preferences()
        
        await interaction.response.send_message(
            f"✅ Personality changed to **{personality.value.capitalize()}**!",
            ephemeral=True
        )
    
    @app_commands.command(name="status", description="Show bot statistics")
    async def status_slash(self, interaction: discord.Interaction):
        """Slash command to show bot status"""
        commands_cog = self.bot.get_cog("BotCommands")
        if commands_cog:
            await commands_cog.status_command(await self.bot.get_context(interaction))
        else:
            await interaction.response.send_message("Status command not available", ephemeral=True)


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(SlashCommands(bot))

