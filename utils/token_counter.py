"""
Token Counter - Estimate token counts for Claude API
Prevents prompt overflow by estimating tokens before API calls
"""

import re
from typing import List, Dict


class TokenCounter:
    """
    Estimates token counts for Claude API messages
    Uses approximate counting: ~4 characters per token (Claude's average)
    """
    
    # Average characters per token for Claude (approximate)
    CHARS_PER_TOKEN = 4
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for a text string
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Rough estimation: ~4 characters per token
        # This is Claude's approximate ratio
        char_count = len(text)
        token_estimate = char_count / TokenCounter.CHARS_PER_TOKEN
        
        # Add overhead for message formatting (~10 tokens per message)
        return int(token_estimate) + 10
    
    @staticmethod
    def estimate_message_tokens(message: Dict[str, str]) -> int:
        """
        Estimate tokens for a single message dict
        
        Args:
            message: Message dict with 'role' and 'content'
            
        Returns:
            Estimated token count
        """
        content = message.get("content", "")
        role = message.get("role", "")
        
        # Count content tokens
        content_tokens = TokenCounter.estimate_tokens(content)
        
        # Add role overhead (~5 tokens)
        role_tokens = 5
        
        return content_tokens + role_tokens
    
    @staticmethod
    def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
        """
        Estimate total tokens for a list of messages
        
        Args:
            messages: List of message dicts
            
        Returns:
            Total estimated token count
        """
        total = 0
        for message in messages:
            total += TokenCounter.estimate_message_tokens(message)
        return total
    
    @staticmethod
    def estimate_system_prompt_tokens(system_prompt: str) -> int:
        """
        Estimate tokens for system prompt
        
        Args:
            system_prompt: System prompt text
            
        Returns:
            Estimated token count
        """
        return TokenCounter.estimate_tokens(system_prompt)
    
    @staticmethod
    def truncate_messages_to_fit(
        messages: List[Dict[str, str]],
        max_tokens: int,
        system_prompt_tokens: int = 0,
        reserve_tokens: int = 200  # Reserve for response
    ) -> List[Dict[str, str]]:
        """
        Truncate messages to fit within token limit
        
        Args:
            messages: List of messages to truncate
            max_tokens: Maximum total tokens allowed
            system_prompt_tokens: Tokens used by system prompt
            reserve_tokens: Tokens to reserve for response
            
        Returns:
            Truncated list of messages (oldest messages removed first)
        """
        available_tokens = max_tokens - system_prompt_tokens - reserve_tokens
        
        if available_tokens <= 0:
            return []  # No room for messages
        
        # Start from the end (most recent messages)
        truncated = []
        current_tokens = 0
        
        # Add messages from newest to oldest until we hit the limit
        for message in reversed(messages):
            msg_tokens = TokenCounter.estimate_message_tokens(message)
            
            if current_tokens + msg_tokens <= available_tokens:
                truncated.insert(0, message)  # Insert at beginning to maintain order
                current_tokens += msg_tokens
            else:
                break  # Can't fit more messages
        
        return truncated
    
    @staticmethod
    def truncate_summaries_to_fit(
        summaries: List[str],
        max_tokens: int,
        reserve_tokens: int = 100
    ) -> List[str]:
        """
        Truncate summaries to fit within token limit
        
        Args:
            summaries: List of summary strings
            max_tokens: Maximum tokens allowed
            reserve_tokens: Tokens to reserve for other content
            
        Returns:
            Truncated list of summaries (oldest removed first)
        """
        available_tokens = max_tokens - reserve_tokens
        
        if available_tokens <= 0:
            return []
        
        truncated = []
        current_tokens = 0
        
        for summary in summaries:
            summary_tokens = TokenCounter.estimate_tokens(summary)
            
            if current_tokens + summary_tokens <= available_tokens:
                truncated.append(summary)
                current_tokens += summary_tokens
            else:
                break
        
        return truncated







