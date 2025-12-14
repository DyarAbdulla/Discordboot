"""
API Handler for AI services (OpenAI and Anthropic Claude)
Handles all API calls and response formatting
"""

import os
import asyncio
from typing import Optional, Dict, List
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


class APIHandler:
    """Handles API calls to OpenAI or Anthropic Claude"""
    
    def __init__(self):
        """Initialize API handler with credentials from environment"""
        self.use_openai = os.getenv("USE_OPENAI", "true").lower() == "true"
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        
        # Initialize OpenAI client
        if self.use_openai:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            # Initialize Anthropic client
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.anthropic_client = AsyncAnthropic(api_key=api_key)
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        personality: str = "friendly",
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate AI response from conversation history
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            personality: Bot personality (friendly, professional, funny, helpful)
            system_prompt: Optional custom system prompt
            
        Returns:
            Generated response text
        """
        # Build system prompt based on personality
        if system_prompt is None:
            system_prompt = self._get_personality_prompt(personality)
        
        try:
            if self.use_openai:
                return await self._generate_openai_response(messages, system_prompt)
            else:
                return await self._generate_anthropic_response(messages, system_prompt)
        except Exception as e:
            raise Exception(f"API Error: {str(e)}")
    
    async def _generate_openai_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> str:
        """Generate response using OpenAI API"""
        # Prepare messages with system prompt
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)
        
        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=formatted_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    async def _generate_anthropic_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> str:
        """Generate response using Anthropic Claude API"""
        # Anthropic API call (async)
        response = await self.anthropic_client.messages.create(
            model=self.anthropic_model,
            max_tokens=1000,
            system=system_prompt,
            messages=messages
        )
        
        return response.content[0].text.strip()
    
    def _get_personality_prompt(self, personality: str) -> str:
        """
        Get system prompt based on personality type
        
        Args:
            personality: Personality type (friendly, professional, funny, helpful)
            
        Returns:
            System prompt string
        """
        prompts = {
            "friendly": (
                "You are a friendly and conversational AI assistant in a Discord server. "
                "Be warm, approachable, and engaging. Use casual language when appropriate, "
                "but remain helpful and informative. Show genuine interest in conversations."
            ),
            "professional": (
                "You are a professional AI assistant in a Discord server. "
                "Be courteous, precise, and maintain a formal tone. Provide clear, "
                "well-structured responses. Focus on accuracy and helpfulness."
            ),
            "funny": (
                "You are a humorous and entertaining AI assistant in a Discord server. "
                "Be witty, use humor appropriately, and keep conversations light-hearted. "
                "Make jokes when suitable, but still be helpful and informative."
            ),
            "helpful": (
                "You are a helpful and knowledgeable AI assistant in a Discord server. "
                "Focus on providing clear, accurate answers. Be patient and thorough. "
                "Break down complex topics and offer step-by-step guidance when needed."
            )
        }
        
        return prompts.get(personality.lower(), prompts["friendly"])
    
    async def summarize_conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        Summarize a long conversation
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Summary text
        """
        summary_prompt = (
            "Please provide a brief summary of the following conversation. "
            "Highlight the main topics discussed and key points."
        )
        
        summary_messages = [
            {"role": "user", "content": summary_prompt},
            {"role": "user", "content": "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in messages[-20:]
            ])}
        ]
        
        return await self.generate_response(
            summary_messages,
            personality="professional",
            system_prompt="You are a helpful assistant that summarizes conversations concisely."
        )

