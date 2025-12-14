"""
Moderation - Auto-moderate toxic messages using Perspective API
"""

import os
import aiohttp
from typing import Dict, Optional
from perspective import PerspectiveAPI


class Moderation:
    """Handles message moderation"""
    
    def __init__(self):
        """Initialize moderation"""
        self.perspective_api_key = os.getenv("PERSPECTIVE_API_KEY")
        self.enabled = bool(self.perspective_api_key)
        
        if self.enabled:
            try:
                self.perspective = PerspectiveAPI(self.perspective_api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Perspective API: {e}")
                self.enabled = False
        else:
            self.perspective = None
    
    async def check_toxicity(self, text: str) -> Dict[str, float]:
        """
        Check message toxicity
        
        Args:
            text: Message text to check
            
        Returns:
            Dictionary with toxicity scores
        """
        if not self.enabled:
            return {}
        
        try:
            response = await self.perspective.analyze(
                text=text,
                requested_attributes={
                    "TOXICITY": {},
                    "SEVERE_TOXICITY": {},
                    "IDENTITY_ATTACK": {},
                    "INSULT": {},
                    "PROFANITY": {},
                    "THREAT": {}
                }
            )
            
            scores = {}
            for attr in response["attributeScores"]:
                scores[attr.lower()] = response["attributeScores"][attr]["summaryScore"]["value"]
            
            return scores
        except Exception as e:
            print(f"Error checking toxicity: {e}")
            return {}
    
    async def is_toxic(self, text: str, threshold: float = 0.7) -> bool:
        """
        Check if message is toxic
        
        Args:
            text: Message text
            threshold: Toxicity threshold (0.0-1.0)
            
        Returns:
            True if message is toxic
        """
        scores = await self.check_toxicity(text)
        
        if not scores:
            return False
        
        # Check if any score exceeds threshold
        toxicity_score = scores.get("toxicity", 0)
        severe_toxicity = scores.get("severe_toxicity", 0)
        
        return toxicity_score >= threshold or severe_toxicity >= threshold
    
    async def get_moderation_action(self, text: str) -> Optional[str]:
        """
        Get recommended moderation action
        
        Args:
            text: Message text
            
        Returns:
            Action recommendation or None
        """
        scores = await self.check_toxicity(text)
        
        if not scores:
            return None
        
        max_score = max(scores.values()) if scores else 0
        
        if max_score >= 0.9:
            return "delete"
        elif max_score >= 0.7:
            return "warn"
        else:
            return None

