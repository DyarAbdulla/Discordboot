"""
Kurdish Language Detector
Detects Sorani and Kurmanji dialects of Kurdish
"""

import re
from typing import Optional, Tuple, Dict


class KurdishDetector:
    """Detects Kurdish language (Sorani and Kurmanji dialects)"""
    
    # Common Kurdish words and patterns (Sorani - Central Kurdish)
    SORANI_PATTERNS = [
        # Common words
        r'\b(سڵاو|سڵاوات|چۆنی|چۆنیت|چۆنیتن|بێژە|بێژەیت|بێژەیتن|'
        r'سوپاس|سوپاسگوزارم|نوێ|نوێی|نوێیت|نوێیتن|'
        r'بەڕێز|بەڕێزان|خۆش|خۆشەویست|دۆست|دۆستان|'
        r'بەخێربێیت|بەخێربێن|بەخێربێنن|'
        r'بەڕێز|بەڕێزان|خۆش|خۆشەویست|دۆست|دۆستان)\b',
        
        # Common phrases
        r'(چی|چۆن|کەی|لە کوێ|بۆ چی|بۆ چۆن|'
        r'ئایا|ئەگەر|کاتێک|کاتێک|ئێستا|ئێستا|'
        r'دەتوانم|دەتوانیت|دەتوانن|ناتوانم|ناتوانیت|'
        r'دەم|دەیت|دەن|نەم|نەیت|نەن)\b',
        
        # Kurdish-specific characters (Arabic script)
        r'[ئەپژگچۆش]',  # Kurdish-specific letters
        
        # Common endings
        r'(یت|یتن|م|ن|مان|تان|یان|ە|ێ|ی)\b',
    ]
    
    # Common Kurdish words and patterns (Kurmanji - Northern Kurdish)
    KURMANJI_PATTERNS = [
        # Common words
        r'\b(merheba|silav|çawa|çawan|çima|çi|'
        r'baş|rind|spas|spasxwe|'
        r'bi xêr hatî|bi xêr hatin|'
        r'heval|dost|dostan|'
        r'ez|tu|ew|em|hûn|ew)\b',
        
        # Common phrases
        r'(çi|çawa|kengî|li ku|ji bo çi|'
        r'gelo|heke|dema|niha|'
        r'dikarim|dikarî|dikarin|nikarim|nikarî|'
        r'dim|dî|din|nem|nî|nin)\b',
        
        # Kurdish-specific Latin characters
        r'[çÇşŞêÊîÎûÛ]',  # Kurdish-specific Latin letters
    ]
    
    # Kurdish greetings (both dialects)
    KURDISH_GREETINGS = {
        'sorani': [
            'سڵاو', 'سڵاوات', 'چۆنی', 'چۆنیت', 'چۆنیتن',
            'بەخێربێیت', 'بەخێربێن', 'بەخێربێنن',
            'بەیانی باش', 'ئێوارە باش', 'شەو باش'
        ],
        'kurmanji': [
            'merheba', 'silav', 'çawa', 'çawan',
            'bi xêr hatî', 'bi xêr hatin',
            'baş be', 'baş bû', 'roj baş', 'şev baş'
        ]
    }
    
    # Kurdish expressions
    KURDISH_EXPRESSIONS = {
        'sorani': {
            'thanks': ['سوپاس', 'سوپاسگوزارم', 'زۆر سوپاس'],
            'welcome': ['بەخێربێیت', 'بەخێربێن'],
            'goodbye': ['خوات لەگەڵ', 'بەخێربیت', 'خوات لەگەڵ بێت'],
            'yes': ['بەڵێ', 'ئێ', 'بەڵێ'],
            'no': ['نەخێر', 'نا'],
            'please': ['تکایە', 'تکایە'],
            'sorry': ['ببورە', 'ببورە'],
            'how_are_you': ['چۆنی', 'چۆنیت', 'چۆنیتن'],
            'good': ['باش', 'خۆش', 'نوێ'],
            'bad': ['خراپ', 'ناخۆش']
        },
        'kurmanji': {
            'thanks': ['spas', 'spasxwe', 'gelek spas'],
            'welcome': ['bi xêr hatî', 'bi xêr hatin'],
            'goodbye': ['bi xatirê te', 'bi xatirê we', 'xatirê te'],
            'yes': ['erê', 'belê', 'a'],
            'no': ['na', 'ne'],
            'please': ['ji kerema xwe', 'ji kerema we'],
            'sorry': ['bebor', 'bebore'],
            'how_are_you': ['çawa yî', 'çawa ne', 'çawan'],
            'good': ['baş', 'rind', 'xweş'],
            'bad': ['xirab', 'ne baş']
        }
    }
    
    @staticmethod
    def detect_kurdish(text: str) -> Optional[Tuple[str, float]]:
        """
        Detect if text is Kurdish and which dialect
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (dialect, confidence) or None if not Kurdish
            dialect: 'sorani', 'kurmanji', or 'kurdish' (general)
            confidence: 0.0 to 1.0
        """
        if not text or len(text.strip()) < 2:
            return None
        
        text_lower = text.lower()
        text_original = text
        
        # Check for Kurdish greetings first (high confidence)
        sorani_greeting_score = 0
        kurmanji_greeting_score = 0
        
        for greeting in KurdishDetector.KURDISH_GREETINGS['sorani']:
            if greeting in text_original or greeting.lower() in text_lower:
                sorani_greeting_score += 3
        
        for greeting in KurdishDetector.KURDISH_GREETINGS['kurmanji']:
            if greeting in text_lower:
                kurmanji_greeting_score += 3
        
        # Pattern matching for Sorani (Arabic script)
        sorani_score = sorani_greeting_score
        for pattern in KurdishDetector.SORANI_PATTERNS:
            matches = len(re.findall(pattern, text_original, re.IGNORECASE))
            sorani_score += matches
        
        # Pattern matching for Kurmanji (Latin script)
        kurmanji_score = kurmanji_greeting_score
        for pattern in KurdishDetector.KURMANJI_PATTERNS:
            matches = len(re.findall(pattern, text_lower))
            kurmanji_score += matches
        
        # Check for Kurdish-specific characters
        # Arabic script characters (Sorani)
        arabic_kurdish_chars = re.findall(r'[ئەپژگچۆش]', text_original)
        if arabic_kurdish_chars:
            sorani_score += len(arabic_kurdish_chars) * 2
        
        # Latin Kurdish characters (Kurmanji)
        latin_kurdish_chars = re.findall(r'[çÇşŞêÊîÎûÛ]', text)
        if latin_kurdish_chars:
            kurmanji_score += len(latin_kurdish_chars) * 2
        
        # Calculate confidence
        total_score = sorani_score + kurmanji_score
        
        if total_score == 0:
            return None
        
        # Determine dialect
        if sorani_score > kurmanji_score:
            confidence = min(0.95, 0.5 + (sorani_score / max(len(text.split()), 10)))
            return ('sorani', confidence)
        elif kurmanji_score > sorani_score:
            confidence = min(0.95, 0.5 + (kurmanji_score / max(len(text.split()), 10)))
            return ('kurmanji', confidence)
        else:
            # Mixed or general Kurdish
            confidence = min(0.9, 0.4 + (total_score / max(len(text.split()), 10)))
            return ('kurdish', confidence)
    
    @staticmethod
    def detect_language(text: str) -> Tuple[str, float]:
        """
        Detect language of text (Kurdish or other)
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
            language_code: 'ku' (Kurdish), 'en' (English), or 'ar' (Arabic)
        """
        if not text:
            return ('en', 0.0)
        
        # Check for Kurdish
        kurdish_result = KurdishDetector.detect_kurdish(text)
        if kurdish_result:
            dialect, confidence = kurdish_result
            return ('ku', confidence)
        
        # Check for Arabic (common in mixed Kurdish-Arabic)
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        if arabic_chars > len(text) * 0.3:
            return ('ar', 0.7)
        
        # Default to English
        return ('en', 0.5)
    
    @staticmethod
    def get_kurdish_greeting(dialect: str = 'sorani') -> str:
        """Get a random Kurdish greeting"""
        import random
        greetings = KurdishDetector.KURDISH_GREETINGS.get(dialect, KurdishDetector.KURDISH_GREETINGS['sorani'])
        return random.choice(greetings)
    
    @staticmethod
    def get_kurdish_expression(expression_type: str, dialect: str = 'sorani') -> str:
        """Get a Kurdish expression"""
        expressions = KurdishDetector.KURDISH_EXPRESSIONS.get(dialect, {})
        exprs = expressions.get(expression_type, [])
        if exprs:
            import random
            return random.choice(exprs)
        return ""




