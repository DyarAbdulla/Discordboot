"""
Enhanced Language Detection - Supports multiple languages
"""

from typing import Tuple, Optional
import re

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from utils.kurdish_detector import KurdishDetector
    KURDISH_DETECTOR_AVAILABLE = True
except ImportError:
    KURDISH_DETECTOR_AVAILABLE = False


class LanguageDetector:
    """Enhanced language detection with Kurdish support"""
    
    # Language codes mapping
    LANGUAGE_NAMES = {
        "en": "English",
        "ku": "Kurdish",
        "ar": "Arabic",
        "tr": "Turkish",
        "fa": "Persian",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "ru": "Russian",
        "zh": "Mandarin"
    }
    
    # Language flags/emojis
    LANGUAGE_FLAGS = {
        "en": "🇬🇧",
        "ku": "🟥⬜🟩☀️",  # Kurdistan flag
        "ar": "🇸🇦",
        "tr": "🇹🇷",
        "fa": "🇮🇷",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "es": "🇪🇸",
        "ru": "🇷🇺",
        "zh": "🇨🇳"
    }
    
    @staticmethod
    def detect_language(text: str) -> Tuple[str, float]:
        """
        Detect language from text
        
        Args:
            text: Text to detect language for
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or len(text.strip()) < 3:
            return "en", 0.5
        
        # First check for Kurdish (has special detection)
        if KURDISH_DETECTOR_AVAILABLE:
            lang_result = KurdishDetector.detect_language(text)
            if lang_result[0] == "ku":
                kurdish_result = KurdishDetector.detect_kurdish(text)
                if kurdish_result:
                    return "ku", kurdish_result[1]
        
        # Use langdetect for other languages
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                languages = detect_langs(text)
                confidence = languages[0].prob if languages else 0.5
                return detected, confidence
            except LangDetectException:
                pass
        
        # Fallback: Simple heuristics
        return LanguageDetector._simple_detect(text)
    
    @staticmethod
    def _simple_detect(text: str) -> Tuple[str, float]:
        """Simple language detection using character patterns"""
        text_lower = text.lower()
        
        # Arabic script (Arabic, Kurdish Sorani, Persian)
        if re.search(r'[\u0600-\u06FF]', text):
            # Check for Kurdish Sorani specific characters
            if re.search(r'[ئەپژگچۆش]', text):
                return "ku", 0.7  # Kurdish Sorani
            # Check for Persian specific characters
            if re.search(r'[پچژگ]', text):
                return "fa", 0.7  # Persian
            return "ar", 0.6  # Arabic
        
        # Kurdish Kurmanji (Latin script)
        if re.search(r'[çşêîû]', text_lower):
            return "ku", 0.7  # Kurdish Kurmanji
        
        # Turkish
        if re.search(r'[çğıöşü]', text_lower):
            return "tr", 0.7
        
        # Cyrillic (Russian)
        if re.search(r'[\u0400-\u04FF]', text):
            return "ru", 0.7
        
        # Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh", 0.7
        
        # Default to English
        return "en", 0.5
    
    @staticmethod
    def get_language_name(code: str) -> str:
        """Get human-readable language name"""
        return LanguageDetector.LANGUAGE_NAMES.get(code, code.upper())
    
    @staticmethod
    def get_language_flag(code: str) -> str:
        """Get language flag emoji"""
        return LanguageDetector.LANGUAGE_FLAGS.get(code, "🌍")
    
    @staticmethod
    def is_kurdish(text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text is Kurdish and return dialect
        
        Returns:
            Tuple of (is_kurdish, dialect) where dialect is 'Sorani' or 'Kurmanji'
        """
        if not KURDISH_DETECTOR_AVAILABLE:
            return False, None
        
        lang_result = KurdishDetector.detect_language(text)
        if lang_result[0] != "ku":
            return False, None
        
        kurdish_result = KurdishDetector.detect_kurdish(text)
        if kurdish_result:
            return True, kurdish_result[0]
        
        return True, None


