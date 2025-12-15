"""
Discord Embed Helper
Provides utilities for creating beautiful Discord embeds with consistent colors
"""

import discord
from typing import Optional, List, Tuple
from datetime import datetime


# Discord brand colors
class EmbedColors:
    """Discord brand colors for embeds"""
    PRIMARY = 0x5865F2    # Discord Blurple - Primary/AI responses (#5865F2)
    SUCCESS = 0x57F287   # Success (#57F287)
    ERROR = 0xED4245     # Error (#ED4245)
    WARNING = 0xFEE75C   # Warning (#FEE75C)
    INFO = 0x5865F2      # Info/Blue (#5865F2)
    KURDISH = 0xEB459E   # Kurdish/Special - Pink (#EB459E)
    BLUE = 0x5865F2      # Info/help (#5865F2) - Alias
    GREEN = 0x57F287     # Success (#57F287) - Alias
    RED = 0xED4245       # Error (#ED4245) - Alias
    PURPLE = 0xEB459E    # AI responses (#EB459E) - Alias
    YELLOW = 0xFEE75C    # Warning - Alias
    WHITE = 0xFFFFFF     # Default


class EmbedHelper:
    """Helper class for creating Discord embeds"""
    
    @staticmethod
    def create_ai_response_embed(
        content: str,
        user_name: Optional[str] = None,
        user_avatar: Optional[str] = None,
        response_time: Optional[str] = None,
        api_provider: Optional[str] = None,
        cached: bool = False,
        detected_language: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an embed for AI responses
        
        Args:
            content: Response content
            user_name: Optional user name
            user_avatar: Optional user avatar URL
            response_time: Optional response time string
            api_provider: Optional API provider name (claude, gemini, groq, etc.)
            cached: Whether response was cached
            detected_language: Optional detected language
            
        Returns:
            Discord embed
        """
        # Choose color based on provider or default
        color = EmbedColors.PRIMARY
        if api_provider == "gemini":
            color = EmbedColors.INFO
        elif api_provider == "groq":
            color = EmbedColors.SUCCESS
        elif detected_language == "ku":
            color = EmbedColors.KURDISH
        
        embed = discord.Embed(
            description=content,
            color=color,
            timestamp=datetime.now()
        )
        
        # Set title with emoji
        if cached:
            embed.title = "⚡ AI Response (Cached)"
        else:
            embed.title = "🤖 AI Response"
        
        if user_name:
            embed.set_author(
                name=f"Response to {user_name}",
                icon_url=user_avatar
            )
        
        # Build footer with API info and response time
        footer_parts = []
        if api_provider:
            provider_emoji = {
                "claude": "🧠",
                "gemini": "💎",
                "groq": "⚡",
                "openrouter": "🌐"
            }.get(api_provider.lower(), "🤖")
            footer_parts.append(f"{provider_emoji} Powered by {api_provider.capitalize()}")
        
        if response_time:
            footer_parts.append(f"⏱️ {response_time}")
        
        if cached:
            footer_parts.append("⚡ Cached")
        
        if detected_language:
            lang_flags = {
                "ku": "🟥⬜🟩☀️",
                "ar": "🇸🇦",
                "en": "🇬🇧",
                "tr": "🇹🇷",
                "fa": "🇮🇷"
            }
            flag = lang_flags.get(detected_language, "🌍")
            footer_parts.append(f"{flag} {detected_language.upper()}")
        
        if footer_parts:
            embed.set_footer(text=" • ".join(footer_parts))
        
        return embed
    
    @staticmethod
    def create_error_embed(
        title: str = "❌ Error",
        description: Optional[str] = None,
        error_details: Optional[str] = None,
        suggested_action: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an error embed
        
        Args:
            title: Error title
            description: Error description
            error_details: Optional detailed error message
            suggested_action: Optional suggested action to fix
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description or "An error occurred while processing your request.",
            color=EmbedColors.ERROR,
            timestamp=datetime.now()
        )
        
        if error_details:
            embed.add_field(
                name="🔍 Details",
                value=error_details[:1024],  # Discord field limit
                inline=False
            )
        
        if suggested_action:
            embed.add_field(
                name="💡 Suggested Action",
                value=suggested_action[:1024],
                inline=False
            )
        
        embed.set_footer(text="If this persists, contact the bot owner")
        
        return embed
    
    @staticmethod
    def create_success_embed(
        title: str = "✅ Success",
        description: Optional[str] = None,
        details: Optional[str] = None,
        fields: Optional[List[Tuple[str, str, bool]]] = None
    ) -> discord.Embed:
        """
        Create a success embed
        
        Args:
            title: Success title
            description: Success description
            details: Optional additional details
            fields: Optional list of (name, value, inline) tuples
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description or "Operation completed successfully!",
            color=EmbedColors.SUCCESS,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="📋 Details",
                value=details[:1024],
                inline=False
            )
        
        if fields:
            for field in fields:
                if len(field) == 2:
                    name, value = field
                    inline = False
                else:
                    name, value, inline = field
                embed.add_field(name=name, value=value[:1024], inline=inline)
        
        return embed
    
    @staticmethod
    def create_info_embed(
        title: str,
        description: Optional[str] = None,
        fields: Optional[List[Tuple[str, str, bool]]] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        color: Optional[int] = None
    ) -> discord.Embed:
        """
        Create an info embed
        
        Args:
            title: Embed title
            description: Embed description
            fields: List of (name, value, inline) tuples
            footer: Footer text
            thumbnail: Thumbnail URL
            color: Optional custom color
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or EmbedColors.INFO,
            timestamp=datetime.now()
        )
        
        if fields:
            for field in fields:
                if len(field) == 2:
                    name, value = field
                    inline = False
                else:
                    name, value, inline = field
                embed.add_field(name=name, value=value[:1024], inline=inline)
        
        if footer:
            embed.set_footer(text=footer)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        return embed
    
    @staticmethod
    def create_warning_embed(
        title: str = "⚠️ Warning",
        description: Optional[str] = None,
        details: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a warning embed
        
        Args:
            title: Warning title
            description: Warning description
            details: Optional additional details
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description or "Please note the following:",
            color=EmbedColors.WARNING,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="📝 Details",
                value=details[:1024],
                inline=False
            )
        
        return embed
    
    @staticmethod
    def create_translation_embed(
        original_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        detected_language: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a translation result embed
        
        Args:
            original_text: Original text
            translated_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            detected_language: Detected language
            
        Returns:
            Discord embed
        """
        lang_names = {
            "en": "English",
            "ku": "Kurdish",
            "ar": "Arabic",
            "tr": "Turkish",
            "fa": "Persian",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
            "zh": "Mandarin"
        }
        
        source_name = lang_names.get(source_lang, source_lang.upper())
        target_name = lang_names.get(target_lang, target_lang.upper())
        
        embed = discord.Embed(
            title="🌍 Translation",
            color=EmbedColors.KURDISH if target_lang == "ku" else EmbedColors.INFO,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f"📝 {source_name}",
            value=original_text[:1024],
            inline=False
        )
        
        embed.add_field(
            name=f"✨ {target_name}",
            value=translated_text[:1024],
            inline=False
        )
        
        if detected_language:
            embed.set_footer(text=f"Detected: {detected_language.upper()}")
        
        return embed
    
    @staticmethod
    def create_image_analysis_embed(
        description: str,
        details: Optional[str] = None,
        detected_language: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an image analysis result embed
        
        Args:
            description: Image description
            details: Optional additional details
            detected_language: Detected language
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title="🖼️ Image Analysis",
            description=description[:4096],
            color=EmbedColors.PRIMARY,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="🔍 Details",
                value=details[:1024],
                inline=False
            )
        
        if detected_language:
            embed.set_footer(text=f"Language: {detected_language.upper()}")
        
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



