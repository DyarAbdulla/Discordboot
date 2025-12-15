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
            "You are summarizing a conversation between a Discord bot and a user. "
            "Create a comprehensive summary that includes:\n\n"
            "1. **Main Summary** (2-3 sentences):\n"
            "   - Key topics discussed\n"
            "   - Important information shared\n"
            "   - User preferences or context\n"
            "   - Any ongoing conversations or plans\n\n"
            "2. **Key Topics** (list 3-5 main topics):\n"
            "   - Extract the main subjects discussed\n"
            "   - Use bullet points\n\n"
            "3. **Important Information** (extract critical details):\n"
            "   - Names, dates, preferences mentioned\n"
            "   - Decisions made or plans discussed\n"
            "   - Any actionable items\n\n"
            "Format your response as:\n"
            "SUMMARY: [main summary]\n\n"
            "KEY TOPICS:\n- [topic 1]\n- [topic 2]\n- [topic 3]\n\n"
            "IMPORTANT INFO:\n- [info 1]\n- [info 2]\n\n"
            "Keep it factual and useful. Do NOT include personal details unless relevant."
        )
    
    async def summarize_messages(
        self,
        messages: List[Dict[str, str]],
        user_name: Optional[str] = None,
        max_tokens: int = 100000,  # Claude's context window
        extract_details: bool = True  # Extract key topics and important info
    ) -> Dict[str, any]:
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
        if extract_details:
            instruction_content = (
                "Please provide a comprehensive summary of this conversation including:\n"
                "1. A main summary (2-3 sentences)\n"
                "2. Key topics discussed (3-5 bullet points)\n"
                "3. Important information extracted (names, dates, preferences, decisions)\n\n"
                "Format as: SUMMARY: [text]\n\nKEY TOPICS:\n- [topic]\n\nIMPORTANT INFO:\n- [info]"
            )
        else:
            instruction_content = "Please summarize this conversation in 2-3 sentences, focusing on key topics and important context."
        
        instruction_msg = {
            "role": "user",
            "content": instruction_content
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
            summary_text = result["response"]
            
            if extract_details:
                # Parse the structured summary
                parsed = self._parse_summary(summary_text)
                return parsed
            else:
                return {
                    "summary": summary_text,
                    "key_topics": [],
                    "important_info": []
                }
        else:
            # Fallback: create simple summary
            fallback = self._create_fallback_summary(messages)
            return {
                "summary": fallback,
                "key_topics": [],
                "important_info": []
            }
    
    def _parse_summary(self, summary_text: str) -> Dict[str, any]:
        """
        Parse structured summary into components
        
        Args:
            summary_text: Raw summary text from Claude
            
        Returns:
            Dictionary with 'summary', 'key_topics', 'important_info'
        """
        result = {
            "summary": "",
            "key_topics": [],
            "important_info": []
        }
        
        # Try to parse structured format
        lines = summary_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if line.upper().startswith('SUMMARY:'):
                result["summary"] = line.replace('SUMMARY:', '').strip()
                current_section = "summary"
            elif 'KEY TOPICS' in line.upper():
                current_section = "topics"
            elif 'IMPORTANT INFO' in line.upper() or 'IMPORTANT INFORMATION' in line.upper():
                current_section = "info"
            elif line.startswith('-') or line.startswith('•'):
                # Bullet point
                content = line.lstrip('- •').strip()
                if current_section == "topics" and content:
                    result["key_topics"].append(content)
                elif current_section == "info" and content:
                    result["important_info"].append(content)
            elif current_section == "summary" and not result["summary"]:
                # First line after SUMMARY: label
                result["summary"] = line
            elif current_section == "summary" and result["summary"]:
                # Continue summary text
                result["summary"] += " " + line
        
        # If parsing failed, use entire text as summary
        if not result["summary"]:
            result["summary"] = summary_text[:500]  # Limit length
        
        return result
    
    def _create_fallback_summary(self, messages: List[Dict[str, str]]) -> Dict[str, any]:
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
        
        summary_text = (
            f"Conversation with {len(user_msgs)} user messages and {len(assistant_msgs)} bot responses. "
            f"Topics discussed: {', '.join(topics[:3])}..."
        )
        
        return {
            "summary": summary_text,
            "key_topics": topics[:3],
            "important_info": []
        }

