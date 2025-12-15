"""
Discord Embed Helper
Provides utilities for creating beautiful Discord embeds with consistent colors
"""

import discord
from typing import Optional


# Discord brand colors
class EmbedColors:
    """Discord brand colors for embeds"""
    BLUE = 0x5865F2      # Info/help (#5865F2)
    GREEN = 0x57F287     # Success (#57F287)
    RED = 0xED4245       # Error (#ED4245)
    PURPLE = 0xEB459E    # AI responses (#EB459E)
    YELLOW = 0xFEE75C    # Warning
    WHITE = 0xFFFFFF     # Default


class EmbedHelper:
    """Helper class for creating Discord embeds"""
    
    @staticmethod
    def create_ai_response_embed(
        content: str,
        user_name: Optional[str] = None,
        user_avatar: Optional[str] = None,
        response_time: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an embed for AI responses
        
        Args:
            content: Response content
            user_name: Optional user name
            user_avatar: Optional user avatar URL
            response_time: Optional response time string
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            description=content,
            color=EmbedColors.PURPLE
        )
        
        if user_name:
            embed.set_author(
                name=f"Response to {user_name}",
                icon_url=user_avatar
            )
        
        if response_time:
            embed.set_footer(text=f"⏱️ {response_time}")
        
        return embed
    
    @staticmethod
    def create_error_embed(
        title: str = "❌ Error",
        description: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an error embed
        
        Args:
            title: Error title
            description: Error description
            error_details: Optional detailed error message
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description or "An error occurred while processing your request.",
            color=EmbedColors.RED
        )
        
        if error_details:
            embed.add_field(
                name="Details",
                value=error_details[:1024],  # Discord field limit
                inline=False
            )
        
        return embed
    
    @staticmethod
    def create_success_embed(
        title: str = "✅ Success",
        description: Optional[str] = None,
        details: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a success embed
        
        Args:
            title: Success title
            description: Success description
            details: Optional additional details
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description or "Operation completed successfully!",
            color=EmbedColors.GREEN
        )
        
        if details:
            embed.add_field(
                name="Details",
                value=details[:1024],
                inline=False
            )
        
        return embed
    
    @staticmethod
    def create_info_embed(
        title: str,
        description: Optional[str] = None,
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an info embed
        
        Args:
            title: Embed title
            description: Embed description
            fields: List of (name, value, inline) tuples
            footer: Footer text
            thumbnail: Thumbnail URL
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=EmbedColors.BLUE
        )
        
        if fields:
            for field in fields:
                if len(field) == 2:
                    name, value = field
                    inline = False
                else:
                    name, value, inline = field
                embed.add_field(name=name, value=value, inline=inline)
        
        if footer:
            embed.set_footer(text=footer)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        return embed
    
    @staticmethod
    def split_long_content(content: str, max_length: int = 4096) -> list:
        """
        Split long content into chunks that fit Discord embed limits
        
        Args:
            content: Content to split
            max_length: Maximum length per chunk
            
        Returns:
            List of content chunks
        """
        if len(content) <= max_length:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Try to split at sentence boundaries
        sentences = content.split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


