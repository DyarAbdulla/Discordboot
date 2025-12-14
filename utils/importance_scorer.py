"""
Importance Scorer - Calculates importance scores for messages and summaries
Critical information (user preferences, important topics) gets higher scores
"""

import re
from typing import Dict, List
from datetime import datetime


class ImportanceScorer:
    """
    Scores messages and summaries based on importance
    Higher scores = more important = persist longer
    """
    
    # Keywords that indicate important information
    PREFERENCE_KEYWORDS = [
        "prefer", "preference", "like", "dislike", "favorite", "favourite",
        "always", "never", "usually", "typically", "always want",
        "my name is", "i am", "i'm", "call me", "i go by", "name is",
        "i speak", "language", "i use", "i work with", "remember that"
    ]
    
    CRITICAL_KEYWORDS = [
        "important", "remember", "don't forget", "always remember",
        "critical", "essential", "must", "need to know",
        "allergy", "medical", "health", "emergency"
    ]
    
    QUESTION_KEYWORDS = [
        "how", "what", "why", "when", "where", "who", "which",
        "explain", "tell me", "help me", "can you"
    ]
    
    @staticmethod
    def score_message(message: Dict[str, str], is_user_message: bool = True) -> float:
        """
        Score a message based on importance indicators
        
        Args:
            message: Message dict with 'role' and 'content'
            is_user_message: Whether this is a user message (user messages are more important)
            
        Returns:
            Importance score (0.0 to 1.0, higher = more important)
        """
        content = message.get("content", "").lower()
        role = message.get("role", "")
        
        score = 0.5  # Base score
        
        # User messages are generally more important
        if is_user_message or role == "user":
            score += 0.1
        
        # Check for preference keywords
        preference_count = sum(1 for keyword in ImportanceScorer.PREFERENCE_KEYWORDS if keyword in content)
        if preference_count > 0:
            score += 0.3  # Preferences are important
            if preference_count > 1:
                score += 0.1  # Multiple preferences = very important
        
        # Check for critical keywords
        critical_count = sum(1 for keyword in ImportanceScorer.CRITICAL_KEYWORDS if keyword in content)
        if critical_count > 0:
            score += 0.4  # Critical information
            if critical_count > 1:
                score += 0.2  # Multiple critical indicators
        
        # Questions might be important (user seeking help)
        if any(keyword in content for keyword in ImportanceScorer.QUESTION_KEYWORDS):
            score += 0.1
        
        # Length can indicate importance (longer = more detailed = potentially more important)
        if len(content) > 200:
            score += 0.05
        
        # Cap at 1.0
        return min(1.0, score)
    
    @staticmethod
    def score_summary(summary_text: str, message_count: int, age_days: float) -> float:
        """
        Score a summary based on content and age
        
        Args:
            summary_text: Summary text
            message_count: Number of messages summarized
            age_days: Age of summary in days
            
        Returns:
            Importance score (0.0 to 1.0)
        """
        content = summary_text.lower()
        score = 0.5  # Base score
        
        # Check for preference mentions
        if any(keyword in content for keyword in ImportanceScorer.PREFERENCE_KEYWORDS):
            score += 0.3
        
        # Check for critical information
        if any(keyword in content for keyword in ImportanceScorer.CRITICAL_KEYWORDS):
            score += 0.4
        
        # More messages summarized = potentially more important conversation
        if message_count > 50:
            score += 0.1
        
        # Age decay (older summaries are less important, but critical info persists)
        # Critical info (score > 0.8) decays slower
        if score > 0.8:
            age_decay = min(0.2, age_days * 0.01)  # Slow decay for critical info
        else:
            age_decay = min(0.3, age_days * 0.02)  # Normal decay
        
        score -= age_decay
        
        # Ensure minimum score
        return max(0.1, score)
    
    @staticmethod
    def extract_preferences(messages: List[Dict[str, str]]) -> List[str]:
        """
        Extract user preferences from messages
        
        Args:
            messages: List of message dicts
            
        Returns:
            List of preference strings
        """
        preferences = []
        
        for msg in messages:
            if msg.get("role") != "user":
                continue
            
            content = msg.get("content", "").lower()
            
            # Look for preference patterns
            for keyword in ImportanceScorer.PREFERENCE_KEYWORDS:
                if keyword in content:
                    # Extract sentence containing preference
                    sentences = re.split(r'[.!?]+', msg.get("content", ""))
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            preferences.append(sentence.strip())
                            break
        
        return preferences[:5]  # Limit to 5 most recent preferences

