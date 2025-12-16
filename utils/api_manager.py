"""
Multi-API Manager - Intelligent routing across multiple AI providers
Supports: Claude, Gemini, Groq, OpenRouter with smart routing and fallback
"""

import os
import asyncio
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

# API Provider Imports
try:
    from anthropic import AsyncAnthropic
    from anthropic._exceptions import APIConnectionError, APIError, APIStatusError
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False


class APIProvider(Enum):
    """API Provider enumeration"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"


class QueryType(Enum):
    """Query type for routing decisions"""
    SIMPLE = "simple"  # Greetings, basic questions
    SPEED_CRITICAL = "speed"  # Fast responses needed
    COMPLEX = "complex"  # Analysis, reasoning, coding
    IMAGE = "image"  # Image analysis
    TRANSLATION = "translation"  # Translation tasks


class APIManager:
    """Manages multiple AI API providers with intelligent routing"""
    
    def __init__(self):
        """Initialize API Manager with all available providers"""
        self.providers = {}
        self.provider_stats = {}
        self.cost_tracking = {}
        self.budget_limits = {}
        self.primary_provider = os.getenv("PRIMARY_API", "claude").lower()
        self.enable_fallback = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
        self.cost_optimization = os.getenv("COST_OPTIMIZATION", "true").lower() == "true"
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET", "50"))
        
        # Initialize providers
        print("[INFO] Initializing Multi-API Manager...")
        self._init_claude()
        self._init_gemini()
        self._init_groq()
        self._init_openrouter()
        
        # Log initialization summary
        active_count = sum(1 for p in self.providers.keys())
        print(f"[INFO] Multi-API routing active - {active_count} provider(s) available")
        if active_count > 0:
            print(f"[INFO] Available providers: {', '.join([p.value for p in self.providers.keys()])}")
        
        # Initialize stats tracking
        for provider in APIProvider:
            self.provider_stats[provider.value] = {
                "calls": 0,
                "errors": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0.0,
                "response_times": [],
                "last_used": None,
                "status": "unknown"
            }
            self.cost_tracking[provider.value] = {
                "daily": 0.0,
                "weekly": 0.0,
                "monthly": 0.0,
                "last_reset": datetime.now()
            }
    
    def _init_claude(self):
        """Initialize Claude API"""
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            print("[WARNING] CLAUDE_API_KEY not found")
            return
        
        if not CLAUDE_AVAILABLE:
            print("[WARNING] Anthropic library not installed")
            return
        
        try:
            self.providers[APIProvider.CLAUDE] = AsyncAnthropic(
                api_key=api_key,
                timeout=60.0,
                max_retries=0
            )
            self.provider_stats[APIProvider.CLAUDE.value]["status"] = "active"
            print("[INFO] Claude API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Claude: {e}")
            self.provider_stats[APIProvider.CLAUDE.value]["status"] = "error"
    
    def _init_gemini(self):
        """Initialize Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[WARNING] GEMINI_API_KEY not found")
            return
        
        if not GEMINI_AVAILABLE:
            print("[WARNING] google-generativeai library not installed")
            return
        
        try:
            genai.configure(api_key=api_key)
            self.providers[APIProvider.GEMINI] = genai.GenerativeModel("gemini-pro")
            self.provider_stats[APIProvider.GEMINI.value]["status"] = "active"
            print("[INFO] Gemini API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini: {e}")
            self.provider_stats[APIProvider.GEMINI.value]["status"] = "error"
    
    def _init_groq(self):
        """Initialize Groq API"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("[WARNING] GROQ_API_KEY not found")
            return
        
        if not GROQ_AVAILABLE:
            print("[WARNING] groq library not installed")
            return
        
        try:
            self.providers[APIProvider.GROQ] = Groq(api_key=api_key)
            self.provider_stats[APIProvider.GROQ.value]["status"] = "active"
            print("[INFO] Groq API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Groq: {e}")
            self.provider_stats[APIProvider.GROQ.value]["status"] = "error"
    
    def _init_openrouter(self):
        """Initialize OpenRouter API"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("[WARNING] OPENROUTER_API_KEY not found")
            return
        
        if not OPENROUTER_AVAILABLE:
            print("[WARNING] openai library not installed for OpenRouter")
            return
        
        try:
            self.providers[APIProvider.OPENROUTER] = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                timeout=60.0
            )
            self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "active"
            print("[INFO] OpenRouter API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize OpenRouter: {e}")
            self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "error"
    
    def _classify_query(self, query: str, messages: List[Dict]) -> QueryType:
        """
        Classify query type for routing
        
        Args:
            query: User query text
            messages: Conversation history
            
        Returns:
            QueryType enum
        """
        query_lower = query.lower()
        
        # Simple queries (greetings, basic questions)
        simple_keywords = ["hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye", 
                          "how are you", "what's up", "sup"]
        if any(keyword in query_lower for keyword in simple_keywords):
            return QueryType.SIMPLE
        
        # Translation queries
        if any(word in query_lower for word in ["translate", "translation", "ترجم", "wergêre"]):
            return QueryType.TRANSLATION
        
        # Complex queries (analysis, coding, reasoning)
        complex_keywords = ["explain", "analyze", "code", "program", "algorithm", 
                           "how does", "why", "compare", "difference", "implement"]
        if any(keyword in query_lower for keyword in complex_keywords):
            return QueryType.COMPLEX
        
        # Speed critical (short questions that need fast answers)
        if len(query) < 50 and "?" in query:
            return QueryType.SPEED_CRITICAL
        
        # Default to complex for safety
        return QueryType.COMPLEX
    
    def _get_provider_for_query(self, query_type: QueryType, has_image: bool = False) -> Optional[APIProvider]:
        """
        Select best provider for query type
        
        Args:
            query_type: Type of query
            has_image: Whether query includes image
            
        Returns:
            Best APIProvider or None
        """
        # Image analysis always uses Claude (best vision)
        if has_image:
            if APIProvider.CLAUDE in self.providers:
                return APIProvider.CLAUDE
            return None
        
        # Simple queries → Gemini (free/cheapest)
        if query_type == QueryType.SIMPLE:
            if APIProvider.GEMINI in self.providers:
                return APIProvider.GEMINI
            # Fallback to Groq if Gemini not available
            if APIProvider.GROQ in self.providers:
                return APIProvider.GROQ
        
        # Speed critical → Groq (fastest)
        if query_type == QueryType.SPEED_CRITICAL:
            if APIProvider.GROQ in self.providers:
                return APIProvider.GROQ
            # Fallback to Gemini
            if APIProvider.GEMINI in self.providers:
                return APIProvider.GEMINI
        
        # Complex → Claude (smartest)
        if query_type == QueryType.COMPLEX:
            if APIProvider.CLAUDE in self.providers:
                return APIProvider.CLAUDE
            # Fallback to OpenRouter
            if APIProvider.OPENROUTER in self.providers:
                return APIProvider.OPENROUTER
        
        # Translation → Any available
        if query_type == QueryType.TRANSLATION:
            # Try cheapest first
            if APIProvider.GEMINI in self.providers:
                return APIProvider.GEMINI
            if APIProvider.GROQ in self.providers:
                return APIProvider.GROQ
            if APIProvider.CLAUDE in self.providers:
                return APIProvider.CLAUDE
        
        # Default: Use primary provider or first available
        if self.primary_provider:
            try:
                primary = APIProvider(self.primary_provider)
                if primary in self.providers:
                    return primary
            except ValueError:
                pass
        
        # Return first available provider
        if self.providers:
            return list(self.providers.keys())[0]
        
        return None
    
    def _get_fallback_chain(self, primary: APIProvider) -> List[APIProvider]:
        """
        Get fallback chain for provider
        
        Args:
            primary: Primary provider
            
        Returns:
            List of providers in fallback order
        """
        chain = []
        
        # Claude fallback chain
        if primary == APIProvider.CLAUDE:
            chain = [APIProvider.GROQ, APIProvider.GEMINI, APIProvider.OPENROUTER]
        
        # Groq fallback chain
        elif primary == APIProvider.GROQ:
            chain = [APIProvider.GEMINI, APIProvider.CLAUDE, APIProvider.OPENROUTER]
        
        # Gemini fallback chain
        elif primary == APIProvider.GEMINI:
            chain = [APIProvider.GROQ, APIProvider.CLAUDE, APIProvider.OPENROUTER]
        
        # OpenRouter fallback chain
        elif primary == APIProvider.OPENROUTER:
            chain = [APIProvider.CLAUDE, APIProvider.GROQ, APIProvider.GEMINI]
        
        # Filter to only available providers
        return [p for p in chain if p in self.providers]
    
    def _calculate_cost(self, provider: APIProvider, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for API call
        
        Args:
            provider: API provider
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            
        Returns:
            Cost in USD
        """
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            APIProvider.CLAUDE: {"input": 0.25, "output": 1.25},  # Claude 3.5 Haiku
            APIProvider.GEMINI: {"input": 0.0, "output": 0.0},  # Free tier
            APIProvider.GROQ: {"input": 0.10, "output": 0.10},  # Approximate
            APIProvider.OPENROUTER: {"input": 0.15, "output": 0.15}  # Approximate
        }
        
        if provider not in pricing:
            return 0.0
        
        cost = (input_tokens / 1_000_000 * pricing[provider]["input"] + 
                output_tokens / 1_000_000 * pricing[provider]["output"])
        
        return cost
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        user_name: Optional[str] = None,
        detected_language: Optional[str] = None,
        has_image: bool = False,
        query: Optional[str] = None,
        **kwargs
    ) -> Dict[str, any]:
        """
        Generate response using intelligent routing
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt
            user_name: Optional user name
            detected_language: Detected language
            has_image: Whether query includes image
            query: User query text (for routing)
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary with 'response', 'success', 'provider', 'response_time', 'cost', etc.
        """
        start_time = time.time()
        
        # Classify query for routing
        if query:
            query_type = self._classify_query(query, messages)
        else:
            # Extract query from last user message
            last_user_msg = next((m for m in reversed(messages) if m.get("role") == "user"), None)
            query = last_user_msg.get("content", "") if last_user_msg else ""
            query_type = self._classify_query(query, messages)
        
        # Select primary provider
        primary_provider = self._get_provider_for_query(query_type, has_image)
        
        # Log routing decision
        if primary_provider:
            query_type_str = query_type.value
            print(f"[DEBUG] {query_type_str.capitalize()} query detected → Using {primary_provider.value.capitalize()}")
        
        if not primary_provider:
            return {
                "response": "I'm sorry, but no AI providers are currently available. Please check your API keys.",
                "success": False,
                "error": "No providers available",
                "provider": None,
                "response_time": 0.0,
                "cost": 0.0
            }
        
        # Check budget limits
        if self.cost_optimization:
            monthly_cost = self.cost_tracking[primary_provider.value]["monthly"]
            if monthly_cost >= self.monthly_budget * 0.9:
                # Switch to cheaper provider if budget high
                if primary_provider == APIProvider.CLAUDE:
                    if APIProvider.GEMINI in self.providers:
                        primary_provider = APIProvider.GEMINI
                    elif APIProvider.GROQ in self.providers:
                        primary_provider = APIProvider.GROQ
        
        # Try primary provider with fallback chain
        providers_to_try = [primary_provider]
        if self.enable_fallback:
            providers_to_try.extend(self._get_fallback_chain(primary_provider))
        
        last_error = None
        for idx, provider in enumerate(providers_to_try):
            try:
                if idx > 0:
                    print(f"[DEBUG] Fallback attempt {idx}: Trying {provider.value.capitalize()}")
                
                result = await self._call_provider(
                    provider=provider,
                    messages=messages,
                    system_prompt=system_prompt,
                    detected_language=detected_language,
                    has_image=has_image,
                    **kwargs
                )
                
                # Calculate response time and cost
                response_time = time.time() - start_time
                cost = self._calculate_cost(
                    provider,
                    result.get("input_tokens", 0),
                    result.get("output_tokens", 0)
                )
                
                # Update stats
                self._update_stats(provider, response_time, cost, result.get("input_tokens", 0) + result.get("output_tokens", 0))
                
                # Add provider info to result
                result["provider"] = provider.value
                result["response_time"] = response_time
                result["cost"] = cost
                result["query_type"] = query_type.value
                
                print(f"[DEBUG] {provider.value.capitalize()} API success! Response length: {len(result.get('response', ''))}")
                
                return result
                
            except Exception as e:
                last_error = e
                self.provider_stats[provider.value]["errors"] += 1
                print(f"[ERROR] {provider.value.capitalize()} failed: {e}")
                if idx < len(providers_to_try) - 1:
                    print(f"[DEBUG] Trying next provider in fallback chain...")
                continue
        
        # All providers failed
        return {
            "response": "I'm having trouble connecting to AI services right now. Please try again in a moment.",
            "success": False,
            "error": str(last_error) if last_error else "All providers failed",
            "provider": None,
            "response_time": time.time() - start_time,
            "cost": 0.0
        }
    
    async def _call_provider(
        self,
        provider: APIProvider,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        has_image: bool = False,
        **kwargs
    ) -> Dict[str, any]:
        """
        Call specific provider
        
        Args:
            provider: Provider to use
            messages: Messages
            system_prompt: System prompt
            detected_language: Detected language
            has_image: Whether has image
            **kwargs: Additional params
            
        Returns:
            Response dictionary
        """
        if provider == APIProvider.CLAUDE:
            return await self._call_claude(messages, system_prompt, detected_language, has_image, **kwargs)
        elif provider == APIProvider.GEMINI:
            return await self._call_gemini(messages, system_prompt, detected_language, **kwargs)
        elif provider == APIProvider.GROQ:
            return await self._call_groq(messages, system_prompt, detected_language, **kwargs)
        elif provider == APIProvider.OPENROUTER:
            return await self._call_openrouter(messages, system_prompt, detected_language, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _call_claude(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        has_image: bool = False,
        **kwargs
    ) -> Dict[str, any]:
        """Call Claude API"""
        client = self.providers[APIProvider.CLAUDE]
        
        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=kwargs.get("max_tokens", 300),
            temperature=kwargs.get("temperature", 0.7),
            system=system_prompt,
            messages=messages
        )
        
        response_text = response.content[0].text.strip()
        
        return {
            "response": response_text,
            "success": True,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
    
    async def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, any]:
        """Call Gemini API (runs in executor since it's sync)"""
        model = self.providers[APIProvider.GEMINI]
        
        # Convert messages format for Gemini
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Run sync call in executor
        loop = asyncio.get_event_loop()
        def _generate():
            return model.generate_content(
                prompt_parts,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_output_tokens": kwargs.get("max_tokens", 300)
                }
            )
        response = await loop.run_in_executor(None, _generate)
        
        response_text = response.text.strip()
        
        # Estimate tokens (Gemini doesn't provide exact counts in free tier)
        input_tokens = len(" ".join(prompt_parts)) // 4  # Rough estimate
        output_tokens = len(response_text) // 4
        
        return {
            "response": response_text,
            "success": True,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    
    async def _call_groq(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, any]:
        """Call Groq API (runs in executor since it's sync)"""
        client = self.providers[APIProvider.GROQ]
        
        # Format messages for Groq
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)
        
        # Run sync call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast model
                messages=formatted_messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 300)
            )
        )
        
        response_text = response.choices[0].message.content.strip()
        
        return {
            "response": response_text,
            "success": True,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens
        }
    
    async def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, any]:
        """Call OpenRouter API"""
        client = self.providers[APIProvider.OPENROUTER]
        
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)
        
        response = await client.chat.completions.create(
            model="anthropic/claude-3-haiku",  # Use Claude via OpenRouter
            messages=formatted_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 300)
        )
        
        response_text = response.choices[0].message.content.strip()
        
        return {
            "response": response_text,
            "success": True,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens
        }
    
    def _update_stats(self, provider: APIProvider, response_time: float, cost: float, tokens: int):
        """Update provider statistics"""
        stats = self.provider_stats[provider.value]
        stats["calls"] += 1
        stats["total_tokens"] += tokens
        stats["total_cost"] += cost
        stats["response_times"].append(response_time)
        stats["last_used"] = datetime.now()
        
        # Keep last 100 response times for average
        if len(stats["response_times"]) > 100:
            stats["response_times"] = stats["response_times"][-100:]
        
        # Calculate average response time
        stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
        
        # Update cost tracking
        cost_track = self.cost_tracking[provider.value]
        cost_track["daily"] += cost
        cost_track["weekly"] += cost
        cost_track["monthly"] += cost
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        return {
            "providers": self.provider_stats,
            "costs": self.cost_tracking,
            "available_providers": [p.value for p in self.providers.keys()],
            "primary_provider": self.primary_provider
        }
    
    def get_provider_status(self) -> Dict:
        """Get status of all providers"""
        status = {}
        for provider in APIProvider:
            stats = self.provider_stats[provider.value]
            status[provider.value] = {
                "available": provider in self.providers,
                "status": stats["status"],
                "calls": stats["calls"],
                "errors": stats["errors"],
                "success_rate": (stats["calls"] - stats["errors"]) / stats["calls"] * 100 if stats["calls"] > 0 else 0,
                "avg_response_time": stats["avg_response_time"],
                "total_cost": stats["total_cost"],
                "monthly_cost": self.cost_tracking[provider.value]["monthly"]
            }
        return status
    
    async def test_all_providers(self) -> Dict:
        """Test all available providers"""
        test_messages = [{"role": "user", "content": "Say hello"}]
        results = {}
        
        for provider in self.providers.keys():
            try:
                start = time.time()
                result = await self._call_provider(
                    provider=provider,
                    messages=test_messages,
                    system_prompt="You are a helpful assistant.",
                    detected_language="en"
                )
                response_time = time.time() - start
                
                results[provider.value] = {
                    "success": result["success"],
                    "response_time": response_time,
                    "response": result.get("response", "")[:50]  # First 50 chars
                }
            except Exception as e:
                results[provider.value] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def test_on_startup(self):
        """Test all providers on startup"""
        print("[INFO] Testing all API providers on startup...")
        results = await self.test_all_providers()
        
        for provider, result in results.items():
            if result.get("success"):
                print(f"[INFO] {provider.capitalize()} API test: ✅ Success ({result.get('response_time', 0):.2f}s)")
            else:
                print(f"[WARNING] {provider.capitalize()} API test: ❌ Failed - {result.get('error', 'Unknown error')}")
        
        return results

