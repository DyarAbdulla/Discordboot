"""
Conversation Summarizer
Creates summaries of old conversations for long-term memory
Uses the same Claude API as regular conversations
"""

from typing import List, Dict, Optional
from datetime import datetime
from claude_handler import ClaudeHandler
from utils.token_counter import TokenCounter


class ConversationSummarizer:
    """
    Summarizes old conversations using Claude API
    This creates long-term memory from past interactions
    """
    
    def __init__(self, claude_handler: ClaudeHandler):
        """
        Initialize summarizer
        
        Args:
            claude_handler: Claude API handler instance
        """
        self.claude_handler = claude_handler
        self.summarization_prompt = (
            "You are summarizing a past conversation between a Discord bot and a user. "
            "Create a concise summary (2-3 sentences) that captures:\n"
            "- Key topics discussed\n"
            "- Important information shared\n"
            "- User preferences or context\n"
            "- Any ongoing conversations or plans\n\n"
            "Keep it factual and useful for future context. "
            "Do NOT include personal details unless relevant to the conversation."
        )
    
    async def summarize_messages(
        self,
        messages: List[Dict[str, str]],
        user_name: Optional[str] = None,
        max_tokens: int = 100000  # Claude's context window
    ) -> str:
        """
        Summarize a list of messages using Claude API
        
        PREVENTS PROMPT OVERFLOW: Automatically truncates messages if they exceed token limits.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_name: Optional user name for context
            max_tokens: Maximum tokens allowed (default: Claude's context window)
            
        Returns:
            Summary text
        """
        if not messages:
            return "No conversation to summarize."
        
        # Estimate tokens for system prompt
        system_prompt_tokens = TokenCounter.estimate_tokens(self.summarization_prompt)
        
        # Estimate tokens for instruction message
        instruction_msg = {
            "role": "user",
            "content": "Please summarize this conversation in 2-3 sentences, focusing on key topics and important context."
        }
        instruction_tokens = TokenCounter.estimate_message_tokens(instruction_msg)
        
        # Truncate messages to fit within token limit
        # Reserve tokens for system prompt, instruction, and response
        reserve_tokens = system_prompt_tokens + instruction_tokens + 500  # 500 for response
        truncated_messages = TokenCounter.truncate_messages_to_fit(
            messages=messages,
            max_tokens=max_tokens,
            system_prompt_tokens=0,  # System prompt handled separately
            reserve_tokens=reserve_tokens
        )
        
        if not truncated_messages:
            # If we can't fit any messages, create a simple fallback
            return self._create_fallback_summary(messages)
        
        # Prepare messages for summarization
        summary_messages = [
            {"role": "system", "content": self.summarization_prompt}
        ] + truncated_messages
        
        # Add instruction to summarize
        summary_messages.append(instruction_msg)
        
        # Call Claude API for summarization (same API as regular conversations)
        result = await self.claude_handler.generate_response(
            messages=summary_messages,
            user_name=user_name,
            summaries=None  # No summaries needed for summarization
        )
        
        if result["success"]:
            return result["response"]
        else:
            # Fallback: create simple summary
            return self._create_fallback_summary(messages)
    
    def _create_fallback_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Create a simple fallback summary when API fails
        
        Args:
            messages: List of messages
            
        Returns:
            Simple summary text
        """
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        assistant_msgs = [m["content"] for m in messages if m["role"] == "assistant"]
        
        # Get first few topics
        topics = []
        for msg in user_msgs[:5]:
            words = msg.split()[:5]  # First 5 words
            if words:
                topics.append(" ".join(words))
        
        return (
            f"Conversation with {len(user_msgs)} user messages and {len(assistant_msgs)} bot responses. "
            f"Topics discussed: {', '.join(topics[:3])}..."
        )

