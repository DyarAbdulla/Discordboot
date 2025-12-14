"""
Context Manager for maintaining conversation history
Manages per-channel conversation context with message limits
Uses smart summarization to preserve context instead of deleting old messages
"""

from typing import Dict, List, Optional
from collections import defaultdict
import json
import os


class ContextManager:
    """Manages conversation context per channel with smart summarization"""
    
    def __init__(self, max_messages: int = 15, summarize_threshold: float = 0.8):
        """
        Initialize context manager
        
        Args:
            max_messages: Maximum number of messages to keep in context
            summarize_threshold: When to trigger summarization (0.0-1.0)
                                At 0.8, summarizes when 80% full
        """
        self.max_messages = max_messages
        self.summarize_threshold = summarize_threshold
        # Store context per channel: {channel_id: list of messages}
        # Using list instead of deque to allow summarization
        self.contexts: Dict[int, List[Dict]] = defaultdict(list)
        # Store user preferences per server: {server_id: {user_id: preferences}}
        self.user_preferences: Dict[int, Dict[int, Dict]] = defaultdict(dict)
        # Store API handler reference for summarization
        self.api_handler = None
    
    def set_api_handler(self, api_handler):
        """
        Set API handler for summarization
        
        Args:
            api_handler: APIHandler instance
        """
        self.api_handler = api_handler
    
    async def _should_summarize(self, channel_id: int) -> bool:
        """
        Check if we should summarize old messages
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if summarization should occur
        """
        current_count = len(self.contexts[channel_id])
        threshold_count = int(self.max_messages * self.summarize_threshold)
        return current_count >= threshold_count
    
    async def _summarize_old_messages(self, channel_id: int) -> Optional[str]:
        """
        Summarize old messages in the context
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Summary text or None if summarization failed
        """
        if not self.api_handler:
            return None
        
        messages = self.contexts[channel_id]
        if len(messages) < 3:  # Need at least a few messages to summarize
            return None
        
        # Calculate how many messages to summarize
        # Keep the most recent messages, summarize the older ones
        messages_to_keep = int(self.max_messages * 0.4)  # Keep 40% of recent messages
        messages_to_summarize = len(messages) - messages_to_keep
        
        if messages_to_summarize < 2:
            return None
        
        # Get old messages to summarize (excluding any existing summaries)
        old_messages = []
        summary_count = 0
        for msg in messages[:messages_to_summarize]:
            if msg.get("role") == "system" and "summary" in msg.get("content", "").lower():
                summary_count += 1
            else:
                old_messages.append(msg)
        
        if len(old_messages) < 2:
            return None
        
        try:
            # Create summary prompt
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in old_messages
            ])
            
            summary_prompt = (
                "Please provide a concise summary of the following conversation. "
                "Focus on the main topics, key decisions, and important context. "
                "Keep it brief but informative:\n\n" + conversation_text
            )
            
            # Generate summary
            summary = await self.api_handler.generate_response(
                messages=[{"role": "user", "content": summary_prompt}],
                personality="professional",
                system_prompt=(
                    "You are a helpful assistant that creates concise conversation summaries. "
                    "Focus on preserving important context and key information."
                )
            )
            
            return summary
        except Exception as e:
            print(f"Error summarizing messages: {e}")
            return None
    
    async def add_message(
        self,
        channel_id: int,
        role: str,
        content: str,
        user_id: Optional[int] = None,
        auto_summarize: bool = True
    ):
        """
        Add a message to conversation context
        Automatically summarizes old messages when threshold is reached
        
        Args:
            channel_id: Discord channel ID
            role: Message role ('user' or 'assistant')
            content: Message content
            user_id: Optional user ID for tracking
            auto_summarize: Whether to automatically summarize when needed
        """
        message = {
            "role": role,
            "content": content
        }
        
        if user_id:
            message["user_id"] = user_id
        
        # Add message
        self.contexts[channel_id].append(message)
        
        # Check if we need to summarize
        if auto_summarize and await self._should_summarize(channel_id):
            summary = await self._summarize_old_messages(channel_id)
            
        if summary:
            # Calculate how many messages to remove
            # Keep 40% of recent messages, summarize the rest
            messages_to_keep = max(3, int(self.max_messages * 0.4))  # Keep at least 3 messages
            current_messages = self.contexts[channel_id]
            messages_to_remove = len(current_messages) - messages_to_keep
            
            if messages_to_remove > 0:
                # Separate old messages (to be summarized) from recent ones (to keep)
                old_messages = current_messages[:messages_to_remove]
                recent_messages = current_messages[messages_to_remove:]
                
                # Check if there's already a summary at the start
                existing_summaries = []
                other_messages = []
                for msg in old_messages:
                    if msg.get("role") == "system" and "summary" in msg.get("content", "").lower():
                        existing_summaries.append(msg)
                    else:
                        other_messages.append(msg)
                
                # Create new summary message
                summary_message = {
                    "role": "system",
                    "content": f"[Previous conversation summary: {summary}]"
                }
                
                # Combine: existing summaries (if any), new summary, then recent messages
                self.contexts[channel_id] = existing_summaries + [summary_message] + recent_messages
                
                # Ensure we don't exceed max_messages
                if len(self.contexts[channel_id]) > self.max_messages:
                    # Remove oldest messages if still over limit (but keep summaries)
                    excess = len(self.contexts[channel_id]) - self.max_messages
                    # Don't remove summary messages, remove from the end of old messages
                    removed = 0
                    new_context = []
                    for msg in self.contexts[channel_id]:
                        if removed < excess and msg.get("role") != "system":
                            removed += 1
                            continue
                        new_context.append(msg)
                    self.contexts[channel_id] = new_context
    
    def get_context(self, channel_id: int) -> List[Dict[str, str]]:
        """
        Get conversation context for a channel
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            List of message dictionaries
        """
        context = list(self.contexts[channel_id])
        # Convert system summary messages to user messages for API compatibility
        # Remove user_id from context before sending to API
        formatted_context = []
        for msg in context:
            formatted_msg = {"role": msg["role"], "content": msg["content"]}
            # Some APIs don't support system messages well, convert to user message
            if formatted_msg["role"] == "system":
                formatted_msg["role"] = "user"
            formatted_context.append(formatted_msg)
        
        return formatted_context
    
    def clear_context(self, channel_id: int):
        """
        Clear conversation context for a channel
        
        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.contexts:
            self.contexts[channel_id].clear()
    
    def get_user_preference(self, server_id: int, user_id: int, key: str, default=None):
        """
        Get a user preference
        
        Args:
            server_id: Discord server ID
            user_id: Discord user ID
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        if server_id in self.user_preferences:
            if user_id in self.user_preferences[server_id]:
                return self.user_preferences[server_id][user_id].get(key, default)
        return default
    
    def set_user_preference(self, server_id: int, user_id: int, key: str, value):
        """
        Set a user preference
        
        Args:
            server_id: Discord server ID
            user_id: Discord user ID
            key: Preference key
            value: Preference value
        """
        if server_id not in self.user_preferences:
            self.user_preferences[server_id] = {}
        if user_id not in self.user_preferences[server_id]:
            self.user_preferences[server_id][user_id] = {}
        
        self.user_preferences[server_id][user_id][key] = value
    
    def save_preferences(self, filepath: str = "preferences.json"):
        """
        Save user preferences to file
        
        Args:
            filepath: Path to save preferences
        """
        try:
            # Convert defaultdict to regular dict for JSON serialization
            preferences = {
                str(server_id): {
                    str(user_id): prefs
                    for user_id, prefs in users.items()
                }
                for server_id, users in self.user_preferences.items()
            }
            
            with open(filepath, 'w') as f:
                json.dump(preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def load_preferences(self, filepath: str = "preferences.json"):
        """
        Load user preferences from file
        
        Args:
            filepath: Path to load preferences from
        """
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r') as f:
                preferences = json.load(f)
            
            # Convert back to proper format
            for server_id_str, users in preferences.items():
                server_id = int(server_id_str)
                for user_id_str, prefs in users.items():
                    user_id = int(user_id_str)
                    self.user_preferences[server_id][user_id] = prefs
        except Exception as e:
            print(f"Error loading preferences: {e}")

