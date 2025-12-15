"""
Static Responses for dyarboot
All pre-written responses organized by category
Includes Kurdish (Sorani and Kurmanji) support
"""

from datetime import datetime

# Import Kurdish detector for language-aware responses
try:
    from utils.kurdish_detector import KurdishDetector
    KURDISH_DETECTOR_AVAILABLE = True
except ImportError:
    KURDISH_DETECTOR_AVAILABLE = False


# Dictionary of keywords and their responses
RESPONSES = {
    # Greetings
    "greetings": {
        "keywords": ["hello", "hi", "hey"],
        "response": "Hello! 👋 How can I help you today?"
    },
    "good_morning": {
        "keywords": ["good morning"],
        "response": "Good morning! Hope you have a great day! ☀️"
    },
    "how_are_you": {
        "keywords": ["how are you"],
        "response": "I'm doing great! Thanks for asking. How about you? 😊"
    },
    
    # Questions
    "name": {
        "keywords": ["what is your name", "who are you", "what's your name"],
        "response": "My name is dyarboot! I'm here to help you. 🤖"
    },
    "help": {
        "keywords": ["help", "what can you do", "how can you help"],
        "response": "I can chat with you! Try saying hello, ask me questions, or use !commands for more options."
    },
    "capabilities": {
        "keywords": ["what can you do", "what do you do"],
        "response": "I can chat with you, answer simple questions, and have fun conversations! Try asking me something!"
    },
    
    # Fun responses
    "joke": {
        "keywords": ["joke", "funny", "tell me a joke"],
        "response": "Why did the chicken cross the road? To get to the other side! 🐔😄"
    },
    "thanks": {
        "keywords": ["thank", "thanks", "appreciate"],
        "response": "You're welcome! Happy to help! 😊"
    },
    "goodbye": {
        "keywords": ["bye", "goodbye", "see you", "later"],
        "response": "Goodbye! See you later! 👋"
    },
    
    # General topics
    "weather": {
        "keywords": ["weather", "rain", "sunny", "temperature"],
        "response": "I can't check the weather yet, but I hope it's nice where you are! ☀️"
    },
    "time": {
        "keywords": ["time", "what time", "clock"],
        "response": f"I don't have a clock, but I hope you're having a good time! ⏰ (Current time: {datetime.now().strftime('%I:%M %p')})"
    },
    
    # Default response (used when no keywords match)
    "default": {
        "keywords": [],
        "response": "I heard you! I'm still learning, but I'm here to chat! Try asking me something simple or use !help for more options."
    }
}

# Kurdish responses (Sorani - Central Kurdish)
KURDISH_SORANI_RESPONSES = {
    "greetings": {
        "keywords": ["سڵاو", "سڵاوات", "چۆنی", "چۆنیت"],
        "response": "سڵاو! بەخێربێیت 👋 چۆن دەتوانم یارمەتیت بدەم؟"
    },
    "good_morning": {
        "keywords": ["بەیانی باش", "بەیانی"],
        "response": "بەیانی باش! هیوادارم ڕۆژێکی باشت هەبێت! ☀️"
    },
    "how_are_you": {
        "keywords": ["چۆنی", "چۆنیت", "چۆنیتن"],
        "response": "من باشم، سوپاس بۆ پرسیارەکەت! تۆ چۆنی؟ 😊"
    },
    "thanks": {
        "keywords": ["سوپاس", "سوپاسگوزارم", "زۆر سوپاس"],
        "response": "سوپاسگوزارم! خۆشحاڵم کە یارمەتیت دابێت! 😊"
    },
    "goodbye": {
        "keywords": ["خوات لەگەڵ", "بەخێربیت", "خوات لەگەڵ بێت"],
        "response": "خوات لەگەڵ! دواتر دیت! 👋"
    },
    "default": {
        "keywords": [],
        "response": "بیستمت! هێشتا فێردەبم، بەڵام لێرەم بۆ گفتوگۆ! تکایە شتێکی ساکار بپرسە یان !help بەکاربهێنە."
    }
}

# Kurdish responses (Kurmanji - Northern Kurdish)
KURDISH_KURMANJI_RESPONSES = {
    "greetings": {
        "keywords": ["merheba", "silav", "çawa", "çawan"],
        "response": "Merheba! Bi xêr hatî 👋 Çawa dikarim alîkariya te bikim?"
    },
    "good_morning": {
        "keywords": ["roj baş", "baş be"],
        "response": "Roj baş! Hêvî dikim rojek baş te hebe! ☀️"
    },
    "how_are_you": {
        "keywords": ["çawa yî", "çawa ne", "çawan"],
        "response": "Ez baş im, spas ji bo pirsê te! Tu çawa yî? 😊"
    },
    "thanks": {
        "keywords": ["spas", "spasxwe", "gelek spas"],
        "response": "Spasxwe! Kêfxweş im ku alîkariya te kirim! 😊"
    },
    "goodbye": {
        "keywords": ["bi xatirê te", "bi xatirê we", "xatirê te"],
        "response": "Bi xatirê te! Paşê te dibînim! 👋"
    },
    "default": {
        "keywords": [],
        "response": "Bihîstîm! Hîn hêj hîn dibim, lê li vir im ji bo axaftinê! Ji kerema xwe tiştek hêsan bipirse an !help bikar bîne."
    }
}


def find_response(message: str, detected_language: str = None, kurdish_dialect: str = None) -> str:
    """
    Find appropriate response based on message content
    
    Args:
        message: User's message text
        detected_language: Detected language code ('ku', 'en', 'ar')
        kurdish_dialect: Kurdish dialect ('sorani', 'kurmanji')
        
    Returns:
        Response string
    """
    # Detect Kurdish if not provided
    if KURDISH_DETECTOR_AVAILABLE and detected_language is None:
        lang_result = KurdishDetector.detect_language(message)
        detected_language = lang_result[0]
        if detected_language == 'ku':
            kurdish_result = KurdishDetector.detect_kurdish(message)
            if kurdish_result:
                kurdish_dialect, _ = kurdish_result
    
    # Handle Kurdish responses
    if detected_language == 'ku':
        if kurdish_dialect == 'sorani':
            responses_dict = KURDISH_SORANI_RESPONSES
        elif kurdish_dialect == 'kurmanji':
            responses_dict = KURDISH_KURMANJI_RESPONSES
        else:
            # Default to Sorani if dialect unknown
            responses_dict = KURDISH_SORANI_RESPONSES
        
        message_lower = message.lower()
        message_original = message
        
        # Check each response category
        for category, data in responses_dict.items():
            # Skip default category
            if category == "default":
                continue
            
            # Check if any keyword matches
            for keyword in data["keywords"]:
                if keyword in message_lower or keyword in message_original:
                    return data["response"]
        
        # No match found, return default Kurdish response
        return responses_dict["default"]["response"]
    
    # English/Arabic responses (original logic)
    message_lower = message.lower()
    
    # Check each response category
    for category, data in RESPONSES.items():
        # Skip default category
        if category == "default":
            continue
        
        # Check if any keyword matches
        for keyword in data["keywords"]:
            if keyword in message_lower:
                return data["response"]
    
    # No match found, return default response
    return RESPONSES["default"]["response"]


def get_reaction(message: str) -> str:
    """
    Get appropriate reaction emoji based on message content
    
    Args:
        message: User's message text
        
    Returns:
        Emoji string or None
    """
    message_lower = message.lower()
    
    # Positive messages get 👍
    if any(word in message_lower for word in ["thank", "thanks", "good", "great", "awesome", "love"]):
        return "👍"
    
    # Questions get ❓
    if "?" in message:
        return "❓"
    
    # Fun messages get ❤️
    if any(word in message_lower for word in ["joke", "funny", "haha", "lol"]):
        return "❤️"
    
    # Default reaction
    return "👋"

