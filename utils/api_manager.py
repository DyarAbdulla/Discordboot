"""
Multi-API Manager - Intelligent routing across multiple AI providers
Supports: Claude, Gemini 2.0 Flash Experimental, Groq, OpenRouter, DeepSeek R1 with smart routing and fallback
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
    DEEPSEEK = "deepseek"


class QueryType(Enum):
    """Query type for routing decisions"""
    SIMPLE = "simple"  # Greetings, basic questions
    SPEED_CRITICAL = "speed"  # Fast responses needed
    REASONING = "reasoning"  # Math, logic, step-by-step reasoning
    COMPLEX = "complex"  # Analysis, writing, general complex tasks
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
        # Get PRIMARY_API and clean it (handle malformed values)
        primary_api_raw = os.getenv("PRIMARY_API", "claude")
        # Clean malformed values like: ""claude"PRIMARY_API=claude" -> "claude"
        if primary_api_raw:
            # Remove extra quotes and duplicate text
            primary_api_raw = primary_api_raw.strip('"').strip("'")
            # If it contains "PRIMARY_API=", extract the value after =
            if "PRIMARY_API=" in primary_api_raw:
                primary_api_raw = primary_api_raw.split("PRIMARY_API=")[-1].strip('"').strip("'")
            # Take only the first word (in case of malformed input)
            primary_api_raw = primary_api_raw.split()[0] if primary_api_raw.split() else "claude"
        self.primary_provider = (primary_api_raw or "claude").lower()
        self.enable_fallback = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
        self.cost_optimization = os.getenv("COST_OPTIMIZATION", "true").lower() == "true"
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET", "50"))
        
        # Initialize providers
        print("[INFO] Initializing Multi-API Manager...")
        self._init_claude()
        self._init_gemini()
        self._init_groq()
        self._init_openrouter()
        self._init_deepseek()
        
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
    
    def _init_claude(self, max_retries: int = 3):
        """Initialize Claude API with retry logic"""
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            print("[WARNING] ❌ CLAUDE_API_KEY not found")
            self.provider_stats[APIProvider.CLAUDE.value]["status"] = "missing_key"
            return
        
        if not CLAUDE_AVAILABLE:
            print("[WARNING] ❌ Anthropic library not installed")
            self.provider_stats[APIProvider.CLAUDE.value]["status"] = "not_available"
            return
        
        for attempt in range(max_retries):
            try:
                self.providers[APIProvider.CLAUDE] = AsyncAnthropic(
                    api_key=api_key,
                    timeout=60.0,
                    max_retries=0
                )
                self.provider_stats[APIProvider.CLAUDE.value]["status"] = "initialized"
                print("[OK] ✅ Claude API initialized successfully")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] Claude initialization attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                    import time as time_module
                    time_module.sleep(1 * (attempt + 1))  # Progressive delay
                else:
                    print(f"[ERROR] ❌ Failed to initialize Claude after {max_retries} attempts: {e}")
                    self.provider_stats[APIProvider.CLAUDE.value]["status"] = "error"
    
    def _init_gemini(self, max_retries: int = 3):
        """Initialize Gemini 2.0 Flash Experimental API with retry logic"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[WARNING] ❌ GEMINI_API_KEY not found")
            self.provider_stats[APIProvider.GEMINI.value]["status"] = "missing_key"
            return
        
        if not GEMINI_AVAILABLE:
            print("[WARNING] ❌ google-generativeai library not installed")
            self.provider_stats[APIProvider.GEMINI.value]["status"] = "not_available"
            return
        
        for attempt in range(max_retries):
            try:
                genai.configure(api_key=api_key)
                self.providers[APIProvider.GEMINI] = genai.GenerativeModel("gemini-2.0-flash-exp")
                self.provider_stats[APIProvider.GEMINI.value]["status"] = "initialized"
                print("[OK] ✅ Gemini 2.0 Flash Experimental initialized successfully")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] Gemini initialization attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                    import time as time_module
                    time_module.sleep(1 * (attempt + 1))
                else:
                    print(f"[ERROR] ❌ Failed to initialize Gemini after {max_retries} attempts: {e}")
                    self.provider_stats[APIProvider.GEMINI.value]["status"] = "error"
    
    def _init_groq(self, max_retries: int = 3):
        """Initialize Groq API with retry logic"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("[WARNING] ❌ GROQ_API_KEY not found")
            self.provider_stats[APIProvider.GROQ.value]["status"] = "missing_key"
            return
        
        if not GROQ_AVAILABLE:
            print("[WARNING] ❌ groq library not installed")
            self.provider_stats[APIProvider.GROQ.value]["status"] = "not_available"
            return
        
        for attempt in range(max_retries):
            try:
                self.providers[APIProvider.GROQ] = Groq(api_key=api_key)
                self.provider_stats[APIProvider.GROQ.value]["status"] = "initialized"
                print("[OK] ✅ Groq API initialized successfully")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] Groq initialization attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                    import time as time_module
                    time_module.sleep(1 * (attempt + 1))
                else:
                    print(f"[ERROR] ❌ Failed to initialize Groq after {max_retries} attempts: {e}")
                    self.provider_stats[APIProvider.GROQ.value]["status"] = "error"
    
    def _init_openrouter(self, max_retries: int = 3):
        """Initialize OpenRouter API with retry logic"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("[WARNING] ❌ OPENROUTER_API_KEY not found")
            self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "missing_key"
            return
        
        if not OPENROUTER_AVAILABLE:
            print("[WARNING] ❌ openai library not installed for OpenRouter")
            self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "not_available"
            return
        
        for attempt in range(max_retries):
            try:
                self.providers[APIProvider.OPENROUTER] = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    timeout=60.0
                )
                self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "initialized"
                print("[OK] ✅ OpenRouter API initialized successfully")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] OpenRouter initialization attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                    import time as time_module
                    time_module.sleep(1 * (attempt + 1))
                else:
                    print(f"[ERROR] ❌ Failed to initialize OpenRouter after {max_retries} attempts: {e}")
                    self.provider_stats[APIProvider.OPENROUTER.value]["status"] = "error"
    
    def _init_deepseek(self, max_retries: int = 3):
        """Initialize DeepSeek R1 API (via direct API or OpenRouter) with retry logic"""
        # Try direct DeepSeek API first (if DEEPSEEK_API_KEY is provided)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        # PREFER: Direct DeepSeek API if DEEPSEEK_API_KEY is provided
        if deepseek_key and OPENROUTER_AVAILABLE:
            for attempt in range(max_retries):
                try:
                    self.providers[APIProvider.DEEPSEEK] = AsyncOpenAI(
                        base_url="https://api.deepseek.com/v1",
                        api_key=deepseek_key,
                        timeout=60.0
                    )
                    self.provider_stats[APIProvider.DEEPSEEK.value]["status"] = "initialized"
                    print("[OK] ✅ DeepSeek R1 API initialized (direct API)")
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] DeepSeek initialization attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                        import time as time_module
                        time_module.sleep(1 * (attempt + 1))
                    else:
                        print(f"[ERROR] ❌ Failed to initialize DeepSeek after {max_retries} attempts: {e}")
                        self.provider_stats[APIProvider.DEEPSEEK.value]["status"] = "error"
        
        # FALLBACK: Use OpenRouter if DEEPSEEK_API_KEY not provided
        if not deepseek_key and openrouter_key and OPENROUTER_AVAILABLE:
            # Reuse OpenRouter client for DeepSeek (same provider)
            if APIProvider.OPENROUTER in self.providers:
                # Use the same OpenRouter client
                self.providers[APIProvider.DEEPSEEK] = self.providers[APIProvider.OPENROUTER]
                self.provider_stats[APIProvider.DEEPSEEK.value]["status"] = "initialized"
                print("[OK] ✅ DeepSeek R1 API initialized via OpenRouter (fallback)")
                return
        
        # No keys found
        if not deepseek_key and not openrouter_key:
            print("[WARNING] ❌ DEEPSEEK_API_KEY or OPENROUTER_API_KEY not found")
            self.provider_stats[APIProvider.DEEPSEEK.value]["status"] = "missing_key"
        elif not OPENROUTER_AVAILABLE:
            print("[WARNING] ❌ openai library not installed for DeepSeek")
            self.provider_stats[APIProvider.DEEPSEEK.value]["status"] = "not_available"
    
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
        
        # Reasoning queries (math, logic, step-by-step) - Route to DeepSeek R1
        reasoning_keywords = [
            # Math
            "calculate", "solve", "equation", "math", "mathematical", "algebra", "calculus",
            "derivative", "integral", "differential", "solve for", "find x", "prove",
            "theorem", "formula", "quadratic", "polynomial", "matrix", "vector",
            # Logic & Reasoning
            "reasoning", "logic", "puzzle", "riddle", "step by step", "think through",
            "reason about", "logical", "deduce", "infer", "conclusion",
            # Coding & Algorithms
            "algorithm", "data structure", "complexity", "optimize", "debug", "trace",
            "binary search", "sorting", "recursion", "dynamic programming",
            # Problem-solving
            "how to solve", "figure out", "determine", "analyze step by step",
            "break down", "work through"
        ]
        if any(keyword in query_lower for keyword in reasoning_keywords):
            return QueryType.REASONING
        
        # Complex queries (analysis, coding, writing - but not pure reasoning)
        complex_keywords = ["explain", "analyze", "code", "program", "implement",
                           "how does", "why", "compare", "difference"]
        if any(keyword in query_lower for keyword in complex_keywords):
            # If it's clearly coding-related, prefer reasoning
            coding_keywords = ["code", "program", "implement", "algorithm", "debug"]
            if any(keyword in query_lower for keyword in coding_keywords):
                return QueryType.REASONING
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
        
        # Reasoning queries → DeepSeek R1 (best for math/logic/reasoning) ⭐
        if query_type == QueryType.REASONING:
            if APIProvider.DEEPSEEK in self.providers:
                return APIProvider.DEEPSEEK
            # Fallback to Claude for reasoning if DeepSeek not available
            if APIProvider.CLAUDE in self.providers:
                return APIProvider.CLAUDE
            # Fallback to OpenRouter
            if APIProvider.OPENROUTER in self.providers:
                return APIProvider.OPENROUTER
        
        # Simple queries → Gemini 2.0 Flash (free/fastest) ⚡
        if query_type == QueryType.SIMPLE:
            if APIProvider.GEMINI in self.providers:
                return APIProvider.GEMINI
            # Fallback to Groq if Gemini not available
            if APIProvider.GROQ in self.providers:
                return APIProvider.GROQ
        
        # Speed critical → Gemini 2.0 Flash (FASTEST: 0.3-0.5s) ⚡
        if query_type == QueryType.SPEED_CRITICAL:
            if APIProvider.GEMINI in self.providers:
                return APIProvider.GEMINI
            # Fallback to Groq (backup for speed)
            if APIProvider.GROQ in self.providers:
                return APIProvider.GROQ
        
        # Complex → Claude (best overall)
        if query_type == QueryType.COMPLEX:
            if APIProvider.CLAUDE in self.providers:
                return APIProvider.CLAUDE
            # Fallback to DeepSeek for complex tasks
            if APIProvider.DEEPSEEK in self.providers:
                return APIProvider.DEEPSEEK
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
            chain = [APIProvider.DEEPSEEK, APIProvider.GROQ, APIProvider.GEMINI, APIProvider.OPENROUTER]
        
        # DeepSeek fallback chain
        elif primary == APIProvider.DEEPSEEK:
            chain = [APIProvider.CLAUDE, APIProvider.GROQ, APIProvider.GEMINI, APIProvider.OPENROUTER]
        
        # Groq fallback chain
        elif primary == APIProvider.GROQ:
            chain = [APIProvider.GEMINI, APIProvider.DEEPSEEK, APIProvider.CLAUDE, APIProvider.OPENROUTER]
        
        # Gemini fallback chain
        elif primary == APIProvider.GEMINI:
            chain = [APIProvider.GROQ, APIProvider.DEEPSEEK, APIProvider.CLAUDE, APIProvider.OPENROUTER]
        
        # OpenRouter fallback chain
        elif primary == APIProvider.OPENROUTER:
            chain = [APIProvider.CLAUDE, APIProvider.DEEPSEEK, APIProvider.GROQ, APIProvider.GEMINI]
        
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
            APIProvider.OPENROUTER: {"input": 0.15, "output": 0.15},  # Approximate
            APIProvider.DEEPSEEK: {"input": 0.00014, "output": 0.00028}  # DeepSeek R1 via OpenRouter (very cheap!)
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
            if primary_provider == APIProvider.DEEPSEEK:
                provider_name = "DeepSeek R1"
                print(f"[DEBUG] 🧮 {query_type_str.capitalize()} query detected → Using {provider_name}")
            elif primary_provider == APIProvider.GEMINI:
                provider_name = "Gemini 2.0 Flash"
                print(f"[DEBUG] ⚡ {query_type_str.capitalize()} query detected → Using {provider_name}")
            else:
                provider_name = primary_provider.value.capitalize()
                print(f"[DEBUG] {query_type_str.capitalize()} query detected → Using {provider_name}")
        
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
                    # For reasoning queries, prefer DeepSeek (cheaper and better)
                    if query_type == QueryType.REASONING and APIProvider.DEEPSEEK in self.providers:
                        primary_provider = APIProvider.DEEPSEEK
                    elif APIProvider.GEMINI in self.providers:
                        primary_provider = APIProvider.GEMINI
                    elif APIProvider.DEEPSEEK in self.providers:
                        primary_provider = APIProvider.DEEPSEEK
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
                
                # Enhanced logging for DeepSeek and Gemini
                if provider == APIProvider.DEEPSEEK:
                    provider_name = "DeepSeek R1"
                    print(f"[DEBUG] 🧮 DeepSeek R1 API success! Response length: {len(result.get('response', ''))} | Cost: ${cost:.6f}")
                elif provider == APIProvider.GEMINI:
                    provider_name = "Gemini 2.0 Flash"
                    print(f"[DEBUG] ⚡ Gemini 2.0 Flash API success! Response length: {len(result.get('response', ''))} | Cost: ${cost:.6f}")
                else:
                    provider_name = provider.value.capitalize()
                    print(f"[DEBUG] {provider_name} API success! Response length: {len(result.get('response', ''))}")
                
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
        elif provider == APIProvider.DEEPSEEK:
            return await self._call_deepseek(messages, system_prompt, detected_language, **kwargs)
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
        """Call Gemini 2.0 Flash Experimental API (runs in executor since it's sync)"""
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
    
    async def _call_deepseek(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        detected_language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, any]:
        """Call DeepSeek R1 API (via OpenRouter or direct)"""
        client = self.providers[APIProvider.DEEPSEEK]
        
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)
        
        # Determine which model to use based on how DeepSeek was initialized
        # Check if we're using direct API or OpenRouter
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        
        # Check if this is the OpenRouter client (shared instance)
        if APIProvider.OPENROUTER in self.providers and self.providers[APIProvider.OPENROUTER] == client:
            # Using OpenRouter
            model_name = "deepseek/deepseek-r1"  # OpenRouter model ID
        elif deepseek_key:
            # Using direct DeepSeek API
            model_name = "deepseek-chat"  # Direct API model name
        else:
            # Fallback
            model_name = "deepseek/deepseek-r1"
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=formatted_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4000)  # DeepSeek supports longer outputs for reasoning
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
                self.provider_stats[provider]["status"] = "active"
            else:
                print(f"[WARNING] {provider.capitalize()} API test: ❌ Failed - {result.get('error', 'Unknown error')}")
                self.provider_stats[provider]["status"] = "error"
        
        return results
    
    async def health_check_provider(self, provider: APIProvider, max_retries: int = 3) -> Dict[str, any]:
        """
        Perform health check on a specific provider with retry logic
        
        Args:
            provider: Provider to check
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with 'success', 'response_time', 'error', 'attempts'
        """
        if provider not in self.providers:
            return {
                "success": False,
                "error": "Provider not initialized",
                "response_time": 0.0,
                "attempts": 0
            }
        
        last_error = None
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Simple test message
                test_messages = [{"role": "user", "content": "Say 'OK'"}]
                
                result = await self._call_provider(
                    provider=provider,
                    messages=test_messages,
                    system_prompt="You are a helpful assistant. Respond with 'OK'.",
                    detected_language="en"
                )
                
                response_time = time.time() - start_time
                
                if result.get("success"):
                    self.provider_stats[provider.value]["status"] = "active"
                    return {
                        "success": True,
                        "response_time": response_time,
                        "error": None,
                        "attempts": attempt + 1
                    }
                else:
                    last_error = result.get("error", "Unknown error")
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
        
        self.provider_stats[provider.value]["status"] = "error"
        return {
            "success": False,
            "error": str(last_error) if last_error else "Health check failed",
            "response_time": 0.0,
            "attempts": max_retries
        }
    
    async def health_check_all(self, max_retries: int = 3) -> Dict[str, Dict[str, any]]:
        """
        Perform health checks on all providers with retry logic
        
        Args:
            max_retries: Maximum retries per provider
            
        Returns:
            Dict mapping provider names to health check results
        """
        results = {}
        
        print("[INFO] Performing health checks on all API providers...")
        for provider in self.providers.keys():
            print(f"[INFO] Checking {provider.value.capitalize()}...")
            result = await self.health_check_provider(provider, max_retries)
            results[provider.value] = result
            
            if result["success"]:
                print(f"[OK] ✅ {provider.value.capitalize()} is healthy ({result['response_time']:.2f}s)")
            else:
                print(f"[ERROR] ❌ {provider.value.capitalize()} health check failed: {result.get('error', 'Unknown')}")
        
        return results

