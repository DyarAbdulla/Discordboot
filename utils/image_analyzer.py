"""
Image Analyzer - Analyze images using vision APIs
"""

import os
import base64
import aiohttp
from typing import Optional
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


class ImageAnalyzer:
    """Handles image analysis using AI vision APIs"""
    
    def __init__(self):
        """Initialize image analyzer"""
        self.use_openai = os.getenv("USE_OPENAI", "true").lower() == "true"
        
        if self.use_openai:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
            else:
                self.openai_client = None
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = AsyncAnthropic(api_key=api_key)
            else:
                self.anthropic_client = None
    
    async def analyze_image(self, image_url: str, prompt: str = "Describe this image in detail.") -> str:
        """
        Analyze an image and return description
        
        Args:
            image_url: URL of the image
            prompt: Prompt for analysis
            
        Returns:
            Image description
        """
        if self.use_openai and self.openai_client:
            return await self._analyze_openai(image_url, prompt)
        elif not self.use_openai and self.anthropic_client:
            return await self._analyze_anthropic(image_url, prompt)
        else:
            return "Image analysis is not available. Please check your API keys."
    
    async def _analyze_openai(self, image_url: str, prompt: str) -> str:
        """Analyze image using OpenAI vision API"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing image: {str(e)}"
    
    async def _analyze_anthropic(self, image_url: str, prompt: str) -> str:
        """Analyze image using Anthropic Claude vision API"""
        try:
            # Download image and convert to base64
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    image_data = await resp.read()
            
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine media type
            media_type = "image/jpeg"
            if image_url.endswith('.png'):
                media_type = "image/png"
            elif image_url.endswith('.gif'):
                media_type = "image/gif"
            elif image_url.endswith('.webp'):
                media_type = "image/webp"
            
            response = await self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return response.content[0].text
        except Exception as e:
            return f"Error analyzing image: {str(e)}"

