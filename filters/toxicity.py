# Enhanced toxicity detection filter
import re
from typing import List, Dict, Tuple

# Enhanced toxic keywords and patterns
TOXIC_KEYWORDS = [
    # Direct insults
    "hate", "stupid", "idiot", "moron", "dumb", "fool", "loser",
    "kill", "die", "death", "suicide", "murder", "violence",
    "ugly", "disgusting", "gross", "pathetic", "worthless",
    
    # Profanity (basic level)
    "damn", "hell", "crap", "suck", "sucks",
    
    # Threats
    "threat", "harm", "hurt", "attack", "destroy", "ruin",
    
    # Discrimination
    "racist", "sexist", "homophobic", "discriminate",
    
    # Self-harm
    "cut", "bleed", "pain", "suffer", "torture"
]

# Context-aware toxic patterns
TOXIC_PATTERNS = [
    r"i\s+hate\s+(?:you|this|that|everything)",
    r"you\s+are\s+(?:stupid|an\s+idiot|dumb|worthless)",
    r"(?:kill|die|death)\s+(?:yourself|you)",
    r"(?:go\s+)?(?:die|kill\s+yourself)",
    r"i\s+want\s+(?:to\s+)?(?:die|kill|hurt)",
    r"(?:you\s+)?(?:suck|are\s+pathetic)",
    r"(?:fuck|damn)\s+(?:you|this|that)",
    r"i\s+(?:hate|despise|loathe)\s+(?:you|this|that)",
    r"(?:you\s+)?(?:are\s+)?(?:ugly|disgusting|gross)",
    r"(?:i\s+)?(?:wish\s+)?(?:you\s+)?(?:were\s+)?(?:dead|gone)"
]

# Severity levels
SEVERITY_KEYWORDS = {
    "low": ["damn", "hell", "crap", "suck"],
    "medium": ["hate", "stupid", "idiot", "ugly", "disgusting"],
    "high": ["kill", "die", "death", "murder", "suicide", "violence"]
}

def check_toxicity(text: str) -> Tuple[bool, List[str], float]:
    """
    Enhanced toxicity detection with severity scoring
    
    Args:
        text: Input text to analyze
        
    Returns:
        Tuple of (is_toxic, detected_patterns, toxicity_score)
    """
    text_lower = text.lower()
    detected_patterns = []
    toxicity_score = 0.0
    
    # Method 1: Keyword matching with severity
    for keyword in TOXIC_KEYWORDS:
        if keyword in text_lower:
            detected_patterns.append(f"keyword:{keyword}")
            # Assign severity score
            if keyword in SEVERITY_KEYWORDS["high"]:
                toxicity_score += 0.8
            elif keyword in SEVERITY_KEYWORDS["medium"]:
                toxicity_score += 0.5
            else:
                toxicity_score += 0.3
    
    # Method 2: Pattern matching
    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, text_lower):
            detected_patterns.append(f"pattern:{pattern}")
            toxicity_score += 0.6
    
    # Method 3: Context analysis
    # Check for threatening language
    threatening_words = ["threat", "harm", "hurt", "attack", "destroy"]
    threat_count = sum(1 for word in threatening_words if word in text_lower)
    if threat_count > 0:
        detected_patterns.append("threatening_language")
        toxicity_score += threat_count * 0.4
    
    # Method 4: Intensity analysis
    intensity_words = ["really", "very", "extremely", "absolutely", "completely"]
    intensity_count = sum(1 for word in intensity_words if word in text_lower)
    if intensity_count > 0 and toxicity_score > 0:
        toxicity_score += intensity_count * 0.2
    
    # Method 5: Repetition analysis
    words = text_lower.split()
    if len(words) > 5:
        toxic_word_count = sum(1 for word in words if word in TOXIC_KEYWORDS)
        if toxic_word_count > 1:
            detected_patterns.append("repeated_toxicity")
            toxicity_score += toxic_word_count * 0.3
    
    # Method 6: Caps lock analysis
    caps_ratio = sum(1 for c in text if c.isupper()) / max(1, len(text))
    if caps_ratio > 0.5 and toxicity_score > 0:
        detected_patterns.append("excessive_caps")
        toxicity_score += 0.2
    
    # Method 7: Punctuation analysis
    exclamation_count = text.count("!")
    if exclamation_count > 2 and toxicity_score > 0:
        detected_patterns.append("excessive_exclamation")
        toxicity_score += exclamation_count * 0.1
    
    # Cap toxicity score at 1.0
    toxicity_score = min(toxicity_score, 1.0)
    
    # Determine if toxic: use slightly higher threshold and avoid pure keyword flips
    # Aim to reduce false positives on benign sentences that contain single weak keywords
    threshold = 0.4
    is_toxic = toxicity_score >= threshold
    
    return is_toxic, detected_patterns, toxicity_score

def get_toxicity_stats(text: str) -> Dict[str, any]:
    """
    Get detailed toxicity analysis statistics
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary with toxicity statistics
    """
    is_toxic, patterns, score = check_toxicity(text)
    
    # Count severity levels
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for pattern in patterns:
        if "keyword:" in pattern:
            keyword = pattern.split(":")[1]
            for level, keywords in SEVERITY_KEYWORDS.items():
                if keyword in keywords:
                    severity_counts[level] += 1
    
    return {
        "is_toxic": is_toxic,
        "toxicity_score": score,
        "detected_patterns": patterns,
        "pattern_count": len(patterns),
        "severity_counts": severity_counts,
        "text_length": len(text),
        "word_count": len(text.split()),
        "caps_ratio": sum(1 for c in text if c.isupper()) / max(1, len(text)),
        "exclamation_count": text.count("!")
    }

def get_toxicity_level(score: float) -> str:
    """
    Get toxicity level based on score
    
    Args:
        score: Toxicity score (0-1)
        
    Returns:
        Toxicity level string
    """
    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "medium"
    elif score >= 0.3:
        return "low"
    else:
        return "minimal"
