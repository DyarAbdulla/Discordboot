"""
Static Responses for dyarboot
All pre-written responses organized by category
"""

from datetime import datetime


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


def find_response(message: str) -> str:
    """
    Find appropriate response based on message content
    
    Args:
        message: User's message text
        
    Returns:
        Response string
    """
    # Convert to lowercase for case-insensitive matching
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

