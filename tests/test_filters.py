# pytest test for filters
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from filters.pii import redact_pii
from filters.injection import detect_injection
from filters.toxicity import check_toxicity
from filters.schema import enforce_schema

def test_pii_redaction():
    text = "Contact: test@example.com, IBAN: TR330006100519786457841326"
    result, detected_types = redact_pii(text)
    assert "[REDACTED]" in result
    assert "email" in detected_types
    assert "iban" in detected_types

def test_injection_detect():
    is_injection, patterns = detect_injection("ignore previous")
    assert is_injection is True
    assert len(patterns) > 0
    assert detect_injection("hello world")[0] is False

def test_toxicity_detect():
    is_toxic, patterns, score = check_toxicity("I hate you")
    assert is_toxic is True
    assert len(patterns) > 0
    assert score > 0
    # Test with a clearly non-toxic phrase
    is_toxic2, patterns2, score2 = check_toxicity("Good morning")
    assert is_toxic2 is False

def test_schema_enforcement():
    resp = enforce_schema({"output": 123})
    assert isinstance(resp["output"], str)
    assert isinstance(resp["cache"], bool)
