"""
Claude API Handler for AI Boot
Handles all Claude API interactions with proper error handling and logging
"""

import os
import asyncio
from anthropic import AsyncAnthropic
from anthropic._exceptions import APIConnectionError, APIError, APIStatusError
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import hashlib
import time
import base64
import aiohttp
from io import BytesIO

# Import TokenCounter for prompt overflow prevention
try:
    from utils.token_counter import TokenCounter
    TOKEN_COUNTER_AVAILABLE = True
except ImportError:
    TOKEN_COUNTER_AVAILABLE = False
    print("[WARNING] TokenCounter not available - prompt overflow prevention disabled")


class ClaudeHandler:
    """Handles Claude API calls with error handling and logging"""
    
    def __init__(self):
        """Initialize Claude API handler"""
        api_key = os.getenv("CLAUDE_API_KEY")
        
        if not api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        
        # Initialize Anthropic async client with timeout configuration
        # Use longer timeouts to handle network issues better
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=60.0,  # 60 second timeout for requests
            max_retries=0  # We handle retries ourselves
        )
        self.model = "claude-3-5-haiku-20241022"  # Faster and cheaper than Sonnet
        
        # System prompt for friendly, professional but warm personality with multilingual support
        self.system_prompt = (
            "You are AI Boot, a friendly and helpful Discord bot assistant. "
            "You have a professional yet warm personality - be knowledgeable and reliable, but also approachable and friendly. "
            "Use emojis occasionally (😊, 👍, ✨, 💡) to add friendliness, but don't overuse them. "
            "Answer questions directly and completely. Don't ask for clarification - provide helpful answers based on context. "
            "Be conversational but get to the point quickly. Keep responses concise (max 300 tokens) and Discord-friendly.\n\n"
            
            "📝 RESPONSE FORMATTING:\n"
            "- Use bullet points (•) for lists when helpful\n"
            "- Structure longer responses with clear sections\n"
            "- Use line breaks for readability\n"
            "- Keep paragraphs short (2-3 sentences max)\n"
            "- Format code/technical terms with backticks when appropriate\n\n"
            
            "💬 CONVERSATION FLOW GUIDELINES:\n"
            "- Maintain natural conversation flow across multiple messages\n"
            "- Reference previous answers when relevant: 'As I mentioned earlier...', 'Building on what we discussed...'\n"
            "- If the user asks a follow-up question within 2 minutes, treat it as related to the previous topic\n"
            "- Ask relevant follow-up questions when appropriate to keep conversation engaging\n"
            "- Connect current questions to previous context naturally\n"
            "- If the user asks about something you already explained, briefly reference it: 'Like I said before...'\n"
            "- Maintain topic continuity - don't abruptly change subjects unless the user does\n"
            "- Remember the last 10 messages in the conversation for context\n\n"
            
            "🌍 MULTILINGUAL SUPPORT:\n"
            "You support Kurdish (Sorani and Kurmanji dialects), English, and Arabic.\n"
            "ALWAYS respond in the SAME LANGUAGE the user uses. Auto-detect their language and match it exactly.\n"
            "When a user speaks Kurdish, respond FULLY in Kurdish using the same dialect.\n"
            "For mixed languages, match the user's primary language preference.\n"
            "For error messages, use the user's detected language.\n\n"
            
            "🟥⬜🟩☀️ KURDISH LANGUAGE GUIDELINES (Kurdistan Flag: Red-White-Green with Sun):\n"
            "• Sorani (Central Kurdish): Uses Arabic script (ئە, پ, ژ, گ, چ, ۆ, ش)\n"
            "  Example: 'سڵاو، چۆنی؟' → Respond: 'سڵاو! من باشم، سوپاس. تۆ چۆنی؟'\n"
            "• Kurmanji (Northern Kurdish): Uses Latin script (ç, ş, ê, î, û)\n"
            "  Example: 'Merheba, çawa yî?' → Respond: 'Merheba! Ez baş im, spas. Tu çawa yî?'\n"
            "• Use culturally appropriate greetings and expressions\n"
            "• Be respectful and warm in Kurdish conversations\n"
            "• Common Sorani greetings: سڵاو (hello), چۆنی (how are you), سوپاس (thanks)\n"
            "• Common Kurmanji greetings: Merheba (hello), Çawa yî (how are you), Spas (thanks)\n"
            "• IMPORTANT: When showing language flags in translations, use 🟥⬜🟩☀️ for Kurdish (both Sorani and Kurmanji) to represent the Kurdistan flag colors (red, white, green with sun)\n\n"
            
            "KURDISH RESPONSE EXAMPLES:\n"
            "User: 'سڵاو' → Bot: 'سڵاو! بەخێربێیت. چۆن دەتوانم یارمەتیت بدەم؟'\n"
            "User: 'Merheba' → Bot: 'Merheba! Bi xêr hatî. Çawa dikarim alîkariya te bikim?'\n"
            "User: 'چۆنی؟' → Bot: 'من باشم، سوپاس بۆ پرسیارەکەت. تۆ چۆنی؟'\n"
            "User: 'Çawa yî?' → Bot: 'Ez baş im, spas ji bo pirsê te. Tu çawa yî?'\n\n"
            
            "When responding in Kurdish:\n"
            "- Use natural, conversational Kurdish\n"
            "- Match the dialect (Sorani/Kurmanji) the user is using\n"
            "- Include appropriate cultural expressions\n"
            "- Be warm and friendly as Kurdish culture values hospitality\n\n"
            
            "⚠️ ERROR HANDLING:\n"
            "If you encounter an error or can't provide an answer, respond in the user's language:\n"
            "- English: 'I'm having trouble connecting. Please try again in a moment.'\n"
            "- Kurdish (Sorani): 'ببورە، هەندێک کێشە هەیە. تکایە دواتر هەوڵ بدەوە.'\n"
            "- Kurdish (Kurmanji): 'Bibûre, hinek kêşe heye. Tika duar hewl bide.'\n"
            "- Arabic: 'أواجه مشكلة في الاتصال. يرجى المحاولة مرة أخرى في لحظة.'\n"
            "Never expose technical error details to users - keep messages friendly and simple."
        )
        
        # API usage tracking
        self.api_calls = 0
        self.api_errors = 0
        self.total_tokens = 0
        
        # Response cache for fallback (simple in-memory cache)
        self.response_cache: Dict[str, Dict] = {}
        self.cache_max_age = timedelta(hours=24)  # Cache for 24 hours
        
        # Last failed request for retry
        self.last_failed_request: Optional[Dict] = None
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        user_name: Optional[str] = None,
        summaries: Optional[List[str]] = None,
        detected_language: Optional[str] = None,
        kurdish_dialect: Optional[str] = None,
        user_facts: Optional[List[Dict[str, any]]] = None,
        follow_up_context: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate AI response using Claude API
        
        Args:
            messages: List of conversation messages [{"role": "user", "content": "..."}, ...]
            user_name: Optional user name for context
            summaries: Optional list of conversation summaries for long-term memory context
            
        Returns:
            Dictionary with 'response', 'success', 'error', 'tokens_used'
        """
        try:
            # Increment API call counter
            self.api_calls += 1
            
            # Build system prompt with context
            system_prompt = self.system_prompt
            
            # Add summaries (long-term memory) to system prompt
            # PREVENT OVERFLOW: Truncate summaries if they're too long
            if summaries:
                if TOKEN_COUNTER_AVAILABLE:
                    # Estimate base system prompt tokens
                    base_tokens = TokenCounter.estimate_tokens(system_prompt)
                    
                    # Truncate summaries to fit (reserve tokens for user name and messages)
                    max_summary_tokens = 2000  # Limit summaries to ~2000 tokens
                    truncated_summaries = TokenCounter.truncate_summaries_to_fit(
                        summaries=summaries,
                        max_tokens=max_summary_tokens,
                        reserve_tokens=100
                    )
                else:
                    # Fallback: just limit number of summaries
                    truncated_summaries = summaries[:5]  # Max 5 summaries
                
                if truncated_summaries:
                    system_prompt += "\n\nPrevious conversation summaries (for context):\n"
                    for summary in truncated_summaries:
                        system_prompt += f"- {summary}\n"
                    system_prompt += "\nUse these summaries to remember past conversations, but focus on the current conversation."
            
            # Add user name to system prompt if provided
            if user_name:
                system_prompt += f"\n\nThe user you're talking to is: {user_name}"
            
            # Add user facts for personalization
            if user_facts:
                facts_text = "\n\nThings I know about this user (use these to personalize responses):\n"
                for fact in user_facts[:15]:  # Limit to top 15 facts
                    facts_text += f"- {fact.get('fact_key', 'unknown').title()}: {fact.get('fact_value', '')}\n"
                system_prompt += facts_text
                system_prompt += "\nUse these facts naturally in your responses when relevant. Don't mention that you're using stored facts - just incorporate them naturally."
            
            # Add follow-up context if this is a follow-up question
            if follow_up_context:
                system_prompt += f"\n\n{follow_up_context}"
            
            # Add language detection context
            if detected_language == 'ku':
                if kurdish_dialect:
                    system_prompt += f"\n\nIMPORTANT: The user is speaking Kurdish ({kurdish_dialect} dialect). Respond FULLY in Kurdish using the {kurdish_dialect} dialect. Match their language exactly."
                else:
                    system_prompt += "\n\nIMPORTANT: The user is speaking Kurdish. Respond FULLY in Kurdish. Match their dialect (Sorani or Kurmanji) based on their script and expressions."
            elif detected_language:
                system_prompt += f"\n\nNote: User language detected as {detected_language}. Respond in the same language if appropriate."
            
            # PREVENT OVERFLOW: Truncate messages if they exceed token limit
            # Claude's context window is ~200k tokens, but we'll use a safer limit
            max_context_tokens = 100000  # Safe limit for Claude
            
            if TOKEN_COUNTER_AVAILABLE:
                system_tokens = TokenCounter.estimate_tokens(system_prompt)
                messages_tokens = TokenCounter.estimate_messages_tokens(messages)
                
                # If messages exceed limit, truncate oldest messages
                if messages_tokens + system_tokens > max_context_tokens:
                    reserve_tokens = system_tokens + 500  # Reserve for system + response
                    messages = TokenCounter.truncate_messages_to_fit(
                        messages=messages,
                        max_tokens=max_context_tokens,
                        system_prompt_tokens=0,  # Already accounted
                        reserve_tokens=reserve_tokens
                    )
                    print(f"[WARNING] Truncated messages to prevent overflow. Using {len(messages)} messages.")
            
            # Check cache first
            cache_key = self._get_cache_key(messages, system_prompt)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                print(f"[INFO] Using cached response for similar request")
                return {
                    "response": cached_response["response"],
                    "success": True,
                    "error": None,
                    "tokens_used": cached_response.get("tokens_used", 0),
                    "cached": True
                }
            
            # Try API call with retries
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # Exponential backoff: 1s, 2s, 4s
                    if attempt > 0:
                        wait_time = 2 ** (attempt - 1)
                        print(f"[INFO] Retrying API call (attempt {attempt + 1}/{max_retries}) after {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    
                    # Call Claude API (async)
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=300,  # Keep responses concise for Discord (reduced from 400)
                        temperature=0.7,  # Balanced creativity - professional but warm
                        system=system_prompt,
                        messages=messages
                    )
                    
                    # Extract response text
                    response_text = response.content[0].text.strip()
                    
                    # Track token usage (separate input/output for accurate cost calculation)
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    tokens_used = input_tokens + output_tokens
                    self.total_tokens += tokens_used
                    
                    # Cache successful response
                    self._cache_response(cache_key, response_text, tokens_used)
                    
                    # Clear last failed request on success
                    self.last_failed_request = None
                    
                    # Log successful API call
                    self._log_api_call(user_name, True, tokens_used)
                    
                    return {
                        "response": response_text,
                        "success": True,
                        "error": None,
                        "tokens_used": tokens_used,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "retry_attempt": attempt + 1 if attempt > 0 else None
                    }
                
                except APIConnectionError as e:
                    # Handle connection errors specifically
                    last_error = e
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    print(f"[ERROR] Claude API connection error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    print(f"[ERROR] This might be a network issue. Retrying...")
                    
                    # Connection errors are retryable - continue to next attempt
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"[ERROR] All {max_retries} retry attempts failed due to connection errors")
                        print(f"[ERROR] Please check your network connection and Railway deployment status")
                
                except APIStatusError as e:
                    # Handle HTTP status errors (401, 403, 429, 500, etc.)
                    last_error = e
                    error_type = type(e).__name__
                    error_msg = str(e)
                    status_code = getattr(e, 'status_code', None)
                    
                    print(f"[ERROR] Claude API status error (attempt {attempt + 1}/{max_retries}): {error_type}: {error_msg}")
                    
                    # Don't retry on authentication errors
                    if status_code in [401, 403]:
                        print(f"[ERROR] Authentication error - API key may be invalid or expired")
                        print(f"[ERROR] Please check your CLAUDE_API_KEY in Railway environment variables")
                        break
                    
                    # Don't retry on client errors (4xx) except 429 (rate limit)
                    if status_code and 400 <= status_code < 500 and status_code != 429:
                        print(f"[ERROR] Client error ({status_code}) - not retrying")
                        break
                    
                    # Retry on rate limits and server errors
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"[ERROR] All {max_retries} retry attempts failed")
                
                except APIError as e:
                    # Handle other API errors
                    last_error = e
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    print(f"[ERROR] Claude API error (attempt {attempt + 1}/{max_retries}): {error_type}: {error_msg}")
                    
                    # Continue to next retry attempt
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"[ERROR] All {max_retries} retry attempts failed")
                
                except Exception as e:
                    # Handle any other unexpected errors
                    last_error = e
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    print(f"[ERROR] Claude API call failed (attempt {attempt + 1}/{max_retries}): {error_type}: {error_msg}")
                    
                    # Don't retry on certain errors (e.g., invalid API key)
                    if "authentication" in error_msg.lower() or "api key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                        print(f"[ERROR] Authentication error - API key may be invalid or expired")
                        print(f"[ERROR] Please check your CLAUDE_API_KEY in Railway environment variables")
                        break
                    
                    # Continue to next retry attempt
                    if attempt < max_retries - 1:
                        continue
                    else:
                        # All retries failed
                        print(f"[ERROR] All {max_retries} retry attempts failed")
            
            # All retries failed - try to use cached response
            fallback_response = self._get_any_cached_response()
            if fallback_response:
                print(f"[INFO] Using fallback cached response after all retries failed")
                return {
                    "response": fallback_response["response"],
                    "success": True,
                    "error": None,
                    "tokens_used": 0,
                    "cached": True,
                    "fallback": True
                }
            
            # Store last failed request for manual retry
            self.last_failed_request = {
                "messages": messages,
                "system_prompt": system_prompt,
                "user_name": user_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Increment error counter
            self.api_errors += 1
            
            # Log failed API call with full error details
            error_msg = str(last_error) if last_error else "Unknown error"
            error_type = type(last_error).__name__ if last_error else "UnknownError"
            print(f"[ERROR] Claude API call failed after {max_retries} retries!")
            print(f"[ERROR] Error type: {error_type}")
            print(f"[ERROR] Error message: {error_msg}")
            import traceback
            print(f"[ERROR] Traceback:")
            traceback.print_exc()
            self._log_api_call(user_name, False, 0, f"{error_type}: {error_msg}")
            
            # Generate user-friendly error message based on detected language
            user_friendly_error = self._get_user_friendly_error(detected_language, kurdish_dialect)
            
            # Return error details
            return {
                "response": user_friendly_error,  # Provide user-friendly message instead of None
                "success": False,
                "error": f"{error_type}: {error_msg}",
                "tokens_used": 0,
                "retry_attempts": max_retries,
                "user_friendly": True
            }
        except Exception as e:
            # Catch any unexpected errors in the outer try block
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"[ERROR] Unexpected error in generate_response: {error_type}: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Generate user-friendly error message (use default language since we don't have context)
            user_friendly_error = self._get_user_friendly_error(None, None)
            
            return {
                "response": user_friendly_error,  # Provide user-friendly message
                "success": False,
                "error": f"{error_type}: {error_msg}",
                "tokens_used": 0,
                "user_friendly": True
            }
    
    async def generate_question_suggestions(
        self,
        user_question: str,
        bot_answer: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_facts: Optional[List[Dict[str, any]]] = None,
        detected_language: Optional[str] = None,
        kurdish_dialect: Optional[str] = None
    ) -> List[str]:
        """
        Generate 3 related question suggestions based on current topic and context
        
        Args:
            user_question: The question the user asked
            bot_answer: The answer the bot provided
            conversation_history: Optional recent conversation history
            user_facts: Optional user facts/interests
            detected_language: Optional detected language
            kurdish_dialect: Optional Kurdish dialect
            
        Returns:
            List of 3 suggested questions (empty list if generation fails)
        """
        try:
            # Build prompt for question suggestions
            suggestion_prompt = (
                "Generate exactly 3 related questions that a user might want to ask "
                "after receiving this answer. Make questions:\n"
                "- Directly related to the topic\n"
                "- Natural and conversational\n"
                "- Based on common follow-up questions\n"
                "- Relevant to what was just discussed\n"
                "- Easy to understand\n\n"
                "Format: Return ONLY the 3 questions, one per line, starting with '❓' or '?'.\n"
                "Do NOT include any other text, explanations, or formatting.\n"
                "Example format:\n"
                "❓ What are the types of AI?\n"
                "❓ How is AI used in real life?\n"
                "❓ What's the difference between AI and machine learning?\n"
            )
            
            # Build context
            context_messages = []
            
            # Add user question and bot answer
            context_messages.append({
                "role": "user",
                "content": f"User asked: {user_question}"
            })
            context_messages.append({
                "role": "assistant",
                "content": f"I answered: {bot_answer[:500]}"  # Limit answer length
            })
            
            # Add recent conversation context if available
            if conversation_history:
                # Get last few user questions for context
                user_questions = [
                    msg["content"] for msg in conversation_history[-6:]
                    if msg.get("role") == "user"
                ]
                if user_questions:
                    context_messages.append({
                        "role": "user",
                        "content": f"Previous questions: {', '.join(user_questions[-3:])}"
                    })
            
            # Add user interests if available
            if user_facts:
                interests = [
                    fact.get("fact_value", "") for fact in user_facts[:5]
                    if fact.get("fact_key", "") in ["likes", "loves", "interests", "hobby"]
                ]
                if interests:
                    context_messages.append({
                        "role": "user",
                        "content": f"User interests: {', '.join(interests)}"
                    })
            
            # Add instruction
            context_messages.append({
                "role": "user",
                "content": suggestion_prompt
            })
            
            # Build system prompt
            system_prompt = (
                "You are a helpful assistant that generates relevant follow-up questions. "
                "Generate exactly 3 questions that are natural, related to the topic, "
                "and would help users explore the subject further."
            )
            
            # Add language context
            if detected_language == 'ku':
                if kurdish_dialect:
                    system_prompt += f"\n\nIMPORTANT: Generate questions in Kurdish ({kurdish_dialect} dialect)."
                else:
                    system_prompt += "\n\nIMPORTANT: Generate questions in Kurdish."
            elif detected_language:
                system_prompt += f"\n\nGenerate questions in {detected_language}."
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=200,  # Short response for suggestions
                system=system_prompt,
                messages=context_messages
            )
            
            # Extract suggestions
            suggestions_text = response.content[0].text.strip()
            
            # Parse suggestions (one per line)
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Remove emoji prefixes if present
                line = line.lstrip('❓?•-').strip()
                if line and len(line) > 10:  # Valid question
                    suggestions.append(line)
                    if len(suggestions) >= 3:
                        break
            
            # Ensure we have exactly 3 suggestions
            while len(suggestions) < 3 and len(suggestions) > 0:
                # Duplicate last suggestion if needed (shouldn't happen, but safety)
                suggestions.append(suggestions[-1])
            
            return suggestions[:3] if len(suggestions) >= 3 else []
        
        except Exception as e:
            print(f"[ERROR] Failed to generate question suggestions: {e}")
            return []
    
    def _get_cache_key(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """
        Generate cache key from messages and system prompt
        
        Args:
            messages: List of messages
            system_prompt: System prompt
            
        Returns:
            Cache key string
        """
        # Use last user message for cache key (most relevant)
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        if not last_user_message:
            last_user_message = str(messages[-1].get("content", "")) if messages else ""
        
        # Create hash from last message + system prompt
        cache_string = f"{last_user_message[:200]}_{system_prompt[:100]}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """
        Get cached response if available and not expired
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached response dict or None
        """
        if cache_key not in self.response_cache:
            return None
        
        cached = self.response_cache[cache_key]
        cache_time = datetime.fromisoformat(cached["timestamp"])
        
        # Check if cache is expired
        if datetime.now() - cache_time > self.cache_max_age:
            del self.response_cache[cache_key]
            return None
        
        return cached
    
    def _cache_response(self, cache_key: str, response: str, tokens_used: int):
        """
        Cache a successful response
        
        Args:
            cache_key: Cache key
            response: Response text
            tokens_used: Tokens used
        """
        self.response_cache[cache_key] = {
            "response": response,
            "tokens_used": tokens_used,
            "timestamp": datetime.now().isoformat()
        }
        
        # Limit cache size (keep last 100)
        if len(self.response_cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(
                self.response_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_cache[:-100]:
                del self.response_cache[key]
    
    def _get_user_friendly_error(
        self, 
        detected_language: Optional[str] = None, 
        kurdish_dialect: Optional[str] = None
    ) -> str:
        """
        Get user-friendly error message in the user's language
        
        Args:
            detected_language: Detected user language
            kurdish_dialect: Kurdish dialect if applicable
            
        Returns:
            User-friendly error message
        """
        if detected_language == 'ku':
            if kurdish_dialect == 'Sorani':
                return "ببورە، هەندێک کێشە هەیە لە دەستگەیشتن. تکایە دواتر هەوڵ بدەوە. 😊"
            else:
                return "Bibûre, hinek kêşe heye li destgeştinê. Tika duar hewl bide. 😊"
        elif detected_language == 'ar':
            return "أواجه مشكلة في الاتصال. يرجى المحاولة مرة أخرى في لحظة. 😊"
        else:
            # Default to English
            return "I'm having trouble connecting. Please try again in a moment. 😊"
    
    def _get_any_cached_response(self) -> Optional[Dict]:
        """
        Get any cached response as fallback
        
        Returns:
            Most recent cached response or None
        """
        if not self.response_cache:
            return None
        
        # Get most recent cached response
        sorted_cache = sorted(
            self.response_cache.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        )
        
        if sorted_cache:
            return sorted_cache[0][1]
        
        return None
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Describe this image in detail. What do you see?",
        user_name: Optional[str] = None,
        detected_language: Optional[str] = None,
        kurdish_dialect: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analyze an image using Claude's vision API
        
        Args:
            image_url: URL of the image to analyze
            prompt: Prompt/question about the image
            user_name: Optional user name
            detected_language: Optional detected language
            kurdish_dialect: Optional Kurdish dialect
            
        Returns:
            Dictionary with 'response', 'success', 'error', 'tokens_used'
        """
        try:
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return {
                            "response": None,
                            "success": False,
                            "error": f"Failed to download image: HTTP {resp.status}",
                            "tokens_used": 0
                        }
                    image_data = await resp.read()
            
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine media type from URL or content type
            media_type = "image/jpeg"  # Default
            if image_url.endswith('.png') or 'png' in image_url.lower():
                media_type = "image/png"
            elif image_url.endswith('.gif') or 'gif' in image_url.lower():
                media_type = "image/gif"
            elif image_url.endswith('.webp') or 'webp' in image_url.lower():
                media_type = "image/webp"
            
            # Build system prompt
            system_prompt = (
                "You are AI Boot, a helpful Discord bot assistant with vision capabilities. "
                "Analyze images carefully and provide detailed, accurate descriptions. "
                "If asked to read text, extract all visible text accurately. "
                "Identify objects, people, scenes, and any notable details. "
                "Be specific and descriptive."
            )
            
            # Add language context
            if detected_language == 'ku':
                if kurdish_dialect:
                    system_prompt += f"\n\nIMPORTANT: Respond in Kurdish ({kurdish_dialect} dialect)."
                else:
                    system_prompt += "\n\nIMPORTANT: Respond in Kurdish."
            elif detected_language:
                system_prompt += f"\n\nRespond in {detected_language}."
            
            # Build messages with image
            messages = [
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
            
            # Call Claude API with vision
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,  # More tokens for image descriptions
                system=system_prompt,
                messages=messages
            )
            
            # Extract response
            response_text = response.content[0].text.strip()
            
            # Track token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens
            self.total_tokens += tokens_used
            
            # Log API call
            self._log_api_call(user_name, True, tokens_used)
            
            return {
                "response": response_text,
                "success": True,
                "error": None,
                "tokens_used": tokens_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"[ERROR] Image analysis failed: {error_type}: {error_msg}")
            import traceback
            traceback.print_exc()
            
            self.api_errors += 1
            self._log_api_call(user_name, False, 0, f"{error_type}: {error_msg}")
            
            return {
                "response": None,
                "success": False,
                "error": f"{error_type}: {error_msg}",
                "tokens_used": 0
            }
    
    async def analyze_multiple_images(
        self,
        image_urls: List[str],
        prompt: str = "Describe these images. What do you see in each?",
        user_name: Optional[str] = None,
        detected_language: Optional[str] = None,
        kurdish_dialect: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analyze multiple images at once
        
        Args:
            image_urls: List of image URLs
            prompt: Prompt/question about the images
            user_name: Optional user name
            detected_language: Optional detected language
            kurdish_dialect: Optional Kurdish dialect
            
        Returns:
            Dictionary with 'response', 'success', 'error', 'tokens_used'
        """
        try:
            # Download all images
            image_contents = []
            async with aiohttp.ClientSession() as session:
                for image_url in image_urls:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            continue
                        image_data = await resp.read()
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        
                        # Determine media type
                        media_type = "image/jpeg"
                        if image_url.endswith('.png') or 'png' in image_url.lower():
                            media_type = "image/png"
                        elif image_url.endswith('.gif') or 'gif' in image_url.lower():
                            media_type = "image/gif"
                        elif image_url.endswith('.webp') or 'webp' in image_url.lower():
                            media_type = "image/webp"
                        
                        image_contents.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        })
            
            if not image_contents:
                return {
                    "response": None,
                    "success": False,
                    "error": "Failed to download any images",
                    "tokens_used": 0
                }
            
            # Build system prompt
            system_prompt = (
                "You are AI Boot, a helpful Discord bot assistant with vision capabilities. "
                f"Analyze {len(image_contents)} image(s) carefully. "
                "Provide detailed descriptions for each image. "
                "If asked to read text, extract all visible text accurately. "
                "Identify objects, people, scenes, and any notable details."
            )
            
            # Add language context
            if detected_language == 'ku':
                if kurdish_dialect:
                    system_prompt += f"\n\nIMPORTANT: Respond in Kurdish ({kurdish_dialect} dialect)."
                else:
                    system_prompt += "\n\nIMPORTANT: Respond in Kurdish."
            elif detected_language:
                system_prompt += f"\n\nRespond in {detected_language}."
            
            # Build messages with all images
            content = image_contents.copy()
            content.append({
                "type": "text",
                "text": prompt
            })
            
            messages = [{
                "role": "user",
                "content": content
            }]
            
            # Call Claude API with vision
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=800,  # More tokens for multiple images
                system=system_prompt,
                messages=messages
            )
            
            # Extract response
            response_text = response.content[0].text.strip()
            
            # Track token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens
            self.total_tokens += tokens_used
            
            # Log API call
            self._log_api_call(user_name, True, tokens_used)
            
            return {
                "response": response_text,
                "success": True,
                "error": None,
                "tokens_used": tokens_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "images_analyzed": len(image_contents)
            }
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"[ERROR] Multi-image analysis failed: {error_type}: {error_msg}")
            import traceback
            traceback.print_exc()
            
            self.api_errors += 1
            self._log_api_call(user_name, False, 0, f"{error_type}: {error_msg}")
            
            return {
                "response": None,
                "success": False,
                "error": f"{error_type}: {error_msg}",
                "tokens_used": 0
            }
    
    async def retry_last_failed_request(self) -> Dict[str, any]:
        """
        Manually retry the last failed request
        
        Returns:
            Result dictionary
        """
        if not self.last_failed_request:
            return {
                "success": False,
                "error": "No failed request to retry"
            }
        
        print(f"[INFO] Retrying last failed request...")
        
        # Retry with the stored parameters
        return await self.generate_response(
            messages=self.last_failed_request["messages"],
            user_name=self.last_failed_request.get("user_name"),
            summaries=None,
            detected_language=None,
            kurdish_dialect=None,
            user_facts=None,
            follow_up_context=None
        )
    
    def _log_api_call(
        self,
        user_name: Optional[str],
        success: bool,
        tokens: int,
        error: Optional[str] = None
    ):
        """Log API call for tracking and cost analysis"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user_name,
                "success": success,
                "tokens": tokens,
                "error": error
            }
            
            # Append to log file
            with open("api_usage.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging API call: {e}")
    
    async def test_api_key(self) -> Dict[str, any]:
        """
        Tests the Claude API key by making a simple, non-conversational request.
        Returns:
            Dict with 'success' (bool) and 'error' (str, if any).
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                system="You are a helpful assistant.",
                messages=[{"role": "user", "content": "Hello"}]
            )
            if response.content and response.content[0].text:
                return {"success": True, "error": None}
            else:
                return {"success": False, "error": "Empty response from API test."}
        except APIConnectionError as e:
            error_msg = str(e)
            print(f"[ERROR] Claude API key test failed: APIConnectionError: {error_msg}")
            return {"success": False, "error": f"Connection error: {error_msg}"}
        except APIStatusError as e:
            error_msg = str(e)
            status_code = getattr(e, 'status_code', None)
            print(f"[ERROR] Claude API key test failed: APIStatusError ({status_code}): {error_msg}")
            return {"success": False, "error": f"API error ({status_code}): {error_msg}"}
        except APIError as e:
            error_msg = str(e)
            print(f"[ERROR] Claude API key test failed: APIError: {error_msg}")
            return {"success": False, "error": f"API error: {error_msg}"}
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"[ERROR] Claude API key test failed: {error_type}: {error_msg}")
            return {"success": False, "error": f"{error_type}: {error_msg}"}
    
    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "total_calls": self.api_calls,
            "total_errors": self.api_errors,
            "total_tokens": self.total_tokens,
            "success_rate": (
                (self.api_calls - self.api_errors) / self.api_calls * 100
                if self.api_calls > 0 else 0
            )
        }
