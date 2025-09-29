# Enhanced prompt injection detection filter
import re
from typing import List, Dict, Tuple

# Enhanced suspicious keywords and patterns
SUSPICIOUS_KEYWORDS = [
    "ignore previous", "forget everything", "reset", "clear memory",
    "system prompt", "system message", "as an ai", "as a language model",
    "you are now", "pretend to be", "roleplay", "act as",
    "jailbreak", "dan mode", "developer mode", "admin mode",
    "bypass", "override", "disregard", "skip",
    "new instructions", "updated instructions", "final instructions",
    "confidential", "secret", "private", "internal",
    "human:", "user:", "assistant:", "system:",
    "prompt injection", "prompt hacking", "ai manipulation"
]

# Advanced patterns
INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?|messages?)",
    r"(?:forget|clear|reset)\s+(?:everything|all|memory)",
    r"you\s+are\s+now\s+(?:a|an)\s+\w+",
    r"pretend\s+(?:to\s+be|you\s+are)",
    r"act\s+as\s+(?:if\s+)?(?:you\s+are\s+)?(?:a|an)\s+\w+",
    r"roleplay\s+as\s+(?:a|an)\s+\w+",
    r"(?:jailbreak|dan)\s+mode",
    r"(?:developer|admin|debug)\s+mode",
    r"bypass\s+(?:all\s+)?(?:safety|security|restrictions?)",
    r"override\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?)",
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?)",
    r"skip\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?)",
    r"new\s+(?:instructions?|prompts?|rules?)",
    r"updated\s+(?:instructions?|prompts?|rules?)",
    r"final\s+(?:instructions?|prompts?|rules?)",
    r"(?:confidential|secret|private|internal)\s+(?:information|data|prompt)",
    r"(?:human|user|assistant|system):\s*",
    r"prompt\s+(?:injection|hacking|manipulation)",
    r"ai\s+(?:manipulation|hacking|jailbreak)"
]

# Context-aware patterns
CONTEXT_PATTERNS = [
    r"if\s+(?:you\s+)?(?:were|are)\s+(?:a|an)\s+\w+",
    r"imagine\s+(?:you\s+)?(?:are|were)\s+(?:a|an)\s+\w+",
    r"suppose\s+(?:you\s+)?(?:are|were)\s+(?:a|an)\s+\w+",
    r"what\s+if\s+(?:you\s+)?(?:are|were)\s+(?:a|an)\s+\w+",
    r"hypothetically\s+(?:you\s+)?(?:are|were)\s+(?:a|an)\s+\w+"
]

def detect_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Enhanced injection detection with multiple methods
    
    Args:
        text: Input text to analyze
        
    Returns:
        Tuple of (is_injection, detected_patterns)
    """
    text_lower = text.lower()
    detected_patterns = []
    
    # Method 1: Keyword matching
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in text_lower:
            detected_patterns.append(f"keyword:{keyword}")
    
    # Method 2: Regex pattern matching
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            detected_patterns.append(f"pattern:{pattern}")
    
    # Method 3: Context analysis
    for pattern in CONTEXT_PATTERNS:
        if re.search(pattern, text_lower):
            detected_patterns.append(f"context:{pattern}")
    
    # Method 4: Length and structure analysis
    if len(text) > 500 and any(word in text_lower for word in ["instruction", "prompt", "system"]):
        detected_patterns.append("length_structure")
    
    # Method 5: Multiple question marks or exclamation marks
    if text.count("?") > 3 or text.count("!") > 3:
        detected_patterns.append("excessive_punctuation")
    
    # Method 6: Repeated phrases
    words = text_lower.split()
    if len(words) > 10:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        if max(word_counts.values()) > len(words) * 0.3:  # 30% repetition
            detected_patterns.append("excessive_repetition")
    
    # Method 7: Binary classifier simulation (placeholder for real model)
    injection_score = calculate_injection_score(text, detected_patterns)
    
    is_injection = len(detected_patterns) > 0 or injection_score > 0.7
    
    return is_injection, detected_patterns

def calculate_injection_score(text: str, patterns: List[str]) -> float:
    """
    Calculate injection probability score
    
    Args:
        text: Input text
        patterns: Detected patterns
        
    Returns:
        Score between 0 and 1
    """
    score = 0.0
    
    # Base score from patterns
    score += len(patterns) * 0.1
    
    # Length penalty
    if len(text) > 1000:
        score += 0.2
    
    # Suspicious word density
    suspicious_words = ["ignore", "forget", "reset", "bypass", "override", "jailbreak"]
    word_count = sum(1 for word in suspicious_words if word in text.lower())
    score += word_count * 0.15
    
    # Cap at 1.0
    return min(score, 1.0)

def get_injection_stats(text: str) -> Dict[str, any]:
    """
    Get detailed injection analysis statistics
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary with injection statistics
    """
    is_injection, patterns = detect_injection(text)
    score = calculate_injection_score(text, patterns)
    
    return {
        "is_injection": is_injection,
        "injection_score": score,
        "detected_patterns": patterns,
        "pattern_count": len(patterns),
        "text_length": len(text),
        "word_count": len(text.split())
    }
