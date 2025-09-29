# Enhanced PII redaction filter
import re
from typing import List, Tuple

# Enhanced regex patterns
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\b(?:\+90|0)?[5][0-9]{9}\b|\b(?:\+1)?[2-9]\d{2}[2-9]\d{6}\b"  # Turkish and US phones
IBAN_REGEX = r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b"
CREDIT_CARD_REGEX = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
TC_KIMLIK_REGEX = r"\b\d{11}\b"  # Turkish ID
VERGI_NO_REGEX = r"\b\d{10}\b"  # Turkish tax number
SSN_REGEX = r"\b\d{3}-\d{2}-\d{4}\b"  # US Social Security Number
PASSPORT_REGEX = r"\b[A-Z]{1,2}\d{6,9}\b"  # Passport numbers
LICENSE_PLATE_REGEX = r"\b\d{2}[A-Z]{1,3}\d{2,4}\b"  # Turkish license plates

# Turkish specific patterns
TURKISH_PHONE_REGEX = r"\b(?:\+90|0)?[5][0-9]{9}\b"
TURKISH_IBAN_REGEX = r"\bTR\d{2}\d{4}[A-Z0-9]{16}\b"

# Obfuscation-aware/normalized patterns (lightweight ML-like support)
# Obfuscated emails like: name [at] domain [dot] com or name (at) domain dot com
OBFUSCATED_EMAIL_REGEX = (
    r"(?i)\b([a-z0-9._%+-]+)\s*(?:\[?\s*at\s*\]?|\(\s*at\s*\)|\sat\s)\s*"
    r"([a-z0-9.-]+)\s*(?:\[?\s*dot\s*\]?|\(\s*dot\s*\)|\sdot\s*|\.)\s*([a-z]{2,})\b"
)

# TR IBAN with spaces between digits: e.g., TR 33 0006 1005 1978 6457 841 326
SPACED_TR_IBAN_REGEX = r"(?i)\bTR\s*(?:\d\s*){24}\b"

# Turkish phones with flexible spacing: 0 532 123 45 67 or +90 532 123 4567
FLEX_TURKISH_PHONE_REGEX = r"\b(?:\+90\s*|0\s*)?5\s*(?:\d\s*){9}\b"

PII_PATTERNS = [
    (EMAIL_REGEX, "email"),
    (PHONE_REGEX, "phone"),
    (IBAN_REGEX, "iban"),
    (CREDIT_CARD_REGEX, "credit_card"),
    (TC_KIMLIK_REGEX, "tc_kimlik"),
    (VERGI_NO_REGEX, "vergi_no"),
    (SSN_REGEX, "ssn"),
    (PASSPORT_REGEX, "passport"),
    (LICENSE_PLATE_REGEX, "license_plate"),
    (TURKISH_PHONE_REGEX, "turkish_phone"),
    (TURKISH_IBAN_REGEX, "turkish_iban")
]

# Extended patterns to catch obfuscations and spacing variants
PII_PATTERNS_EXTENDED = [
    (OBFUSCATED_EMAIL_REGEX, "email"),
    (SPACED_TR_IBAN_REGEX, "turkish_iban"),
    (FLEX_TURKISH_PHONE_REGEX, "turkish_phone"),
]

REDACTION_TEXT = "[REDACTED]"

def redact_pii(text: str) -> Tuple[str, List[str]]:
    """
    Redact PII from text and return redacted text with detected PII types
    
    Args:
        text: Input text to redact
        
    Returns:
        Tuple of (redacted_text, detected_pii_types)
    """
    redacted_text = text
    detected_types = []
    
    # 1) Standard patterns
    for pattern, pii_type in PII_PATTERNS:
        matches = re.findall(pattern, redacted_text, re.IGNORECASE)
        if matches:
            detected_types.append(pii_type)
            redacted_text = re.sub(pattern, REDACTION_TEXT, redacted_text, flags=re.IGNORECASE)

    # 2) Extended patterns (obfuscation/spacing) — lightweight ML-like enhancement
    for pattern, pii_type in PII_PATTERNS_EXTENDED:
        matches = re.findall(pattern, redacted_text, re.IGNORECASE)
        if matches:
            if pii_type not in detected_types:
                detected_types.append(pii_type)
            redacted_text = re.sub(pattern, REDACTION_TEXT, redacted_text, flags=re.IGNORECASE)
    
    return redacted_text, detected_types

def validate_pii_pattern(text: str, pattern: str) -> bool:
    """
    Validate if text matches a PII pattern
    
    Args:
        text: Text to validate
        pattern: Regex pattern to match
        
    Returns:
        True if pattern matches
    """
    return bool(re.search(pattern, text, re.IGNORECASE))

def get_pii_stats(text: str) -> dict:
    """
    Get statistics about PII in text
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with PII statistics
    """
    stats = {}
    for pattern, pii_type in PII_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        stats[pii_type] = len(matches)
    
    stats['total_pii'] = sum(stats.values())
    return stats
