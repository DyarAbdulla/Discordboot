"""
API Management Commands - Slash commands for API management
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime
import time

try:
    from utils.embed_helper import EmbedHelper, EmbedColors
    EMBED_HELPER_AVAILABLE = True
except ImportError:
    EMBED_HELPER_AVAILABLE = False


class APICommands(commands.Cog):
    """API management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="api-status", description="Show all API health status")
    async def api_status_command(self, interaction: discord.Interaction):
        """Show API status"""
        if not hasattr(self.bot, 'api_manager') or not self.bot.api_manager:
            await interaction.response.send_message(
                "❌ API Manager not available!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self._api_status(interaction)
    
    @app_commands.command(name="api-test", description="Test all APIs and report")
    async def api_test_command(self, interaction: discord.Interaction):
        """Test all APIs"""
        if not hasattr(self.bot, 'api_manager') or not self.bot.api_manager:
            await interaction.response.send_message(
                "❌ API Manager not available!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self._api_test(interaction)
    
    @app_commands.command(name="api-costs", description="Show API costs today/week/month")
    async def api_costs_command(self, interaction: discord.Interaction):
        """Show API costs"""
        if not hasattr(self.bot, 'api_manager') or not self.bot.api_manager:
            await interaction.response.send_message(
                "❌ API Manager not available!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self._api_costs(interaction)
    
    async def _api_status(self, interaction: discord.Interaction):
        """Show API status"""
        status = self.bot.api_manager.get_provider_status()
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="🔌 API Status",
                description="Current status of all API providers"
            )
            
            for provider, info in status.items():
                status_emoji = "✅" if info["available"] else "❌"
                status_text = "Active" if info["available"] else "Unavailable"
                
                if info["status"] == "active":
                    status_text = "🟢 Active"
                elif info["status"] == "error":
                    status_text = "🔴 Error"
                else:
                    status_text = "⚪ Unknown"
                
                response_time_str = f"{info['avg_response_time']:.2f}s" if info['avg_response_time'] > 0 else "N/A"
                value = (
                    f"**Status**: {status_text}\n"
                    f"**Calls**: {info['calls']:,}\n"
                    f"**Errors**: {info['errors']:,}\n"
                    f"**Success Rate**: {info['success_rate']:.1f}%\n"
                    f"**Response Time**: {response_time_str}\n"
                    f"**Monthly Cost**: ${info['monthly_cost']:.2f}"
                )
                
                embed.add_field(
                    name=f"{status_emoji} {provider.capitalize()}",
                    value=value,
                    inline=True
                )
            
            await interaction.followup.send(embed=embed)
        else:
            text = "**🔌 API Status**\n\n"
            for provider, info in status.items():
                text += f"**{provider.capitalize()}**: "
                text += "✅ Available" if info["available"] else "❌ Unavailable"
                text += f" | Calls: {info['calls']:,} | Success: {info['success_rate']:.1f}%\n"
            await interaction.followup.send(text)
    
    async def _api_costs(self, interaction: discord.Interaction):
        """Show API costs"""
        stats = self.bot.api_manager.get_stats()
        costs = stats["costs"]
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="💰 API Costs",
                description="Cost breakdown by provider"
            )
            
            total_monthly = 0.0
            for provider, cost_data in costs.items():
                monthly = cost_data["monthly"]
                total_monthly += monthly
                
                embed.add_field(
                    name=f"💵 {provider.capitalize()}",
                    value=(
                        f"**Daily**: ${cost_data['daily']:.2f}\n"
                        f"**Weekly**: ${cost_data['weekly']:.2f}\n"
                        f"**Monthly**: ${monthly:.2f}"
                    ),
                    inline=True
                )
            
            embed.add_field(
                name="📊 Total Monthly",
                value=f"${total_monthly:.2f}",
                inline=False
            )
            
            # Budget info
            budget = self.bot.config.get("monthly_budget", 50)
            usage_percent = (total_monthly / budget * 100) if budget > 0 else 0
            
            if usage_percent >= 90:
                color = EmbedColors.ERROR
            elif usage_percent >= 75:
                color = EmbedColors.WARNING
            else:
                color = EmbedColors.SUCCESS
            
            embed.color = color
            embed.add_field(
                name="🎯 Budget",
                value=f"${total_monthly:.2f} / ${budget:.2f} ({usage_percent:.1f}%)",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            text = "**💰 API Costs**\n\n"
            for provider, cost_data in costs.items():
                text += f"**{provider}**: ${cost_data['monthly']:.2f}/month\n"
            await interaction.followup.send(text)
    
    async def _api_test(self, interaction: discord.Interaction):
        """Test all APIs"""
        await interaction.followup.send("🧪 Testing all APIs... This may take a moment.")
        
        results = await self.bot.api_manager.test_all_providers()
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="🧪 API Test Results",
                description="Test results for all providers"
            )
            
            for provider, result in results.items():
                if result["success"]:
                    emoji = "✅"
                    value = (
                        f"**Status**: Success\n"
                        f"**Response Time**: {result.get('response_time', 0):.2f}s\n"
                        f"**Response**: {result.get('response', 'N/A')[:100]}"
                    )
                else:
                    emoji = "❌"
                    value = f"**Status**: Failed\n**Error**: {result.get('error', 'Unknown')[:200]}"
                
                embed.add_field(
                    name=f"{emoji} {provider.capitalize()}",
                    value=value,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        else:
            text = "**🧪 API Test Results**\n\n"
            for provider, result in results.items():
                status = "✅ Success" if result["success"] else f"❌ Failed: {result.get('error', 'Unknown')}"
                text += f"**{provider}**: {status}\n"
            await interaction.followup.send(text)
    
    async def _api_stats(self, interaction: discord.Interaction):
        """Show API statistics"""
        stats = self.bot.api_manager.get_stats()
        provider_stats = stats["providers"]
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_info_embed(
                title="📊 API Statistics",
                description="Detailed usage statistics"
            )
            
            for provider, data in provider_stats.items():
                if data["calls"] > 0:
                    embed.add_field(
                        name=f"📈 {provider.capitalize()}",
                        value=(
                            f"**Total Calls**: {data['calls']:,}\n"
                            f"**Total Tokens**: {data['total_tokens']:,}\n"
                            f"**Total Cost**: ${data['total_cost']:.2f}\n"
                            f"**Avg Response**: {data['avg_response_time']:.2f}s\n"
                            f"**Error Rate**: {data['errors'] / data['calls'] * 100:.1f}%"
                        ),
                        inline=True
                    )
            
            await interaction.followup.send(embed=embed)
        else:
            text = "**📊 API Statistics**\n\n"
            for provider, data in provider_stats.items():
                if data["calls"] > 0:
                    text += f"**{provider}**: {data['calls']:,} calls, ${data['total_cost']:.2f} cost\n"
            await interaction.followup.send(text)
    
    @app_commands.command(name="api-switch", description="Switch primary API provider")
    @app_commands.describe(provider="Provider to switch to")
    @app_commands.choices(provider=[
        app_commands.Choice(name="Claude", value="claude"),
        app_commands.Choice(name="Gemini", value="gemini"),
        app_commands.Choice(name="Groq", value="groq"),
        app_commands.Choice(name="OpenRouter", value="openrouter")
    ])
    async def api_switch(
        self,
        interaction: discord.Interaction,
        provider: app_commands.Choice[str]
    ):
        """Switch primary API provider"""
        # Only allow bot owner
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message(
                "❌ Only the bot owner can switch API providers!",
                ephemeral=True
            )
            return
        
        if not hasattr(self.bot, 'api_manager') or not self.bot.api_manager:
            await interaction.response.send_message(
                "❌ API Manager not available!",
                ephemeral=True
            )
            return
        
        # Check if provider is available
        status = self.bot.api_manager.get_provider_status()
        if not status.get(provider.value, {}).get("available", False):
            await interaction.response.send_message(
                f"❌ {provider.value.capitalize()} is not available! Check your API keys.",
                ephemeral=True
            )
            return
        
        # Switch provider
        self.bot.api_manager.primary_provider = provider.value
        self.bot.config["primary_api"] = provider.value
        
        if EMBED_HELPER_AVAILABLE:
            embed = EmbedHelper.create_success_embed(
                title="✅ API Switched",
                description=f"Primary API provider changed to **{provider.value.capitalize()}**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"✅ Primary API switched to {provider.value.capitalize()}",
                ephemeral=True
            )


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(APICommands(bot))


