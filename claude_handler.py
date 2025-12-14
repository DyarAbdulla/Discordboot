"""
Claude API Handler for AI Boot
Handles all Claude API interactions with proper error handling and logging
"""

import os
import asyncio
from anthropic import AsyncAnthropic
from typing import List, Dict, Optional
from datetime import datetime
import json


class ClaudeHandler:
    """Handles Claude API calls with error handling and logging"""
    
    def __init__(self):
        """Initialize Claude API handler"""
        api_key = os.getenv("CLAUDE_API_KEY")
        
        if not api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        
        # Initialize Anthropic async client
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"  # Faster and cheaper than Sonnet
        
        # System prompt for friendly, helpful personality
        self.system_prompt = (
            "You are AI Boot, a friendly Discord bot. "
            "Be helpful, conversational, and fun! "
            "Keep responses natural and engaging - not robotic. "
            "Use casual language when appropriate. "
            "Keep responses concise (under 400 tokens) and Discord-friendly. "
            "Use emojis occasionally but naturally. "
            "Be enthusiastic and show genuine interest in conversations!"
        )
        
        # API usage tracking
        self.api_calls = 0
        self.api_errors = 0
        self.total_tokens = 0
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        user_name: Optional[str] = None,
        summaries: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Generate AI response using Claude API
        
        Args:
            messages: List of conversation messages [{"role": "user", "content": "..."}, ...]
            user_name: Optional user name for context
            summaries: Optional list of conversation summaries for long-term memory context
            
        Returns:
            Dictionary with 'response', 'success', 'error', 'tokens_used'
        """
        try:
            # Increment API call counter
            self.api_calls += 1
            
            # Build system prompt with context
            system_prompt = self.system_prompt
            
            # Add summaries (long-term memory) to system prompt
            if summaries:
                system_prompt += "\n\nPrevious conversation summaries (for context):\n"
                for summary in summaries:
                    system_prompt += f"- {summary}\n"
                system_prompt += "\nUse these summaries to remember past conversations, but focus on the current conversation."
            
            # Add user name to system prompt if provided
            if user_name:
                system_prompt += f"\n\nThe user you're talking to is: {user_name}"
            
            # Call Claude API (async)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=400,  # Keep responses concise for Discord
                system=system_prompt,
                messages=messages
            )
            
            # Extract response text
            response_text = response.content[0].text.strip()
            
            # Track token usage
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            self.total_tokens += tokens_used
            
            # Log successful API call
            self._log_api_call(user_name, True, tokens_used)
            
            return {
                "response": response_text,
                "success": True,
                "error": None,
                "tokens_used": tokens_used
            }
        
        except Exception as e:
            # Increment error counter
            self.api_errors += 1
            
            # Log failed API call with full error details
            error_msg = str(e)
            print(f"[ERROR] Claude API call failed: {error_msg}")
            self._log_api_call(user_name, False, 0, error_msg)
            
            # Return error details for debugging
            return {
                "response": None,
                "success": False,
                "error": error_msg,
                "tokens_used": 0
            }
    
    def _log_api_call(
        self,
        user_name: Optional[str],
        success: bool,
        tokens: int,
        error: Optional[str] = None
    ):
        """Log API call for tracking and cost analysis"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user_name,
                "success": success,
                "tokens": tokens,
                "error": error
            }
            
            # Append to log file
            with open("api_usage.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging API call: {e}")
    
    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "total_calls": self.api_calls,
            "total_errors": self.api_errors,
            "total_tokens": self.total_tokens,
            "success_rate": (
                (self.api_calls - self.api_errors) / self.api_calls * 100
                if self.api_calls > 0 else 0
            )
        }
