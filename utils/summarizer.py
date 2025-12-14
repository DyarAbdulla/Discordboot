"""
Conversation Summarizer
Creates summaries of old conversations for long-term memory
"""

from typing import List, Dict, Optional
from datetime import datetime
from claude_handler import ClaudeHandler


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
        user_name: Optional[str] = None
    ) -> str:
        """
        Summarize a list of messages
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_name: Optional user name for context
            
        Returns:
            Summary text
        """
        if not messages:
            return "No conversation to summarize."
        
        # Prepare messages for summarization
        summary_messages = [
            {"role": "system", "content": self.summarization_prompt}
        ] + messages
        
        # Add instruction to summarize
        summary_messages.append({
            "role": "user",
            "content": "Please summarize this conversation in 2-3 sentences, focusing on key topics and important context."
        })
        
        # Call Claude API for summarization
        result = await self.claude_handler.generate_response(
            messages=summary_messages,
            user_name=user_name
        )
        
        if result["success"]:
            return result["response"]
        else:
            # Fallback: create simple summary
            user_msgs = [m["content"] for m in messages if m["role"] == "user"]
            assistant_msgs = [m["content"] for m in messages if m["role"] == "assistant"]
            
            return (
                f"Conversation with {len(user_msgs)} user messages and {len(assistant_msgs)} bot responses. "
                f"Topics discussed: {', '.join(user_msgs[:3])}..."
            )

