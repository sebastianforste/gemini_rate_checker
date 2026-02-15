import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gemini_rate_checker import classify_model_response, extract_testable_models, serialize_results


def test_classify_model_response_mappings():
    assert classify_model_response(200) == (True, "OK")
    assert classify_model_response(429) == (False, "Rate Limit (429)")
    assert classify_model_response(503) == (False, "Error 503")


def test_extract_testable_models_filters_gemma_and_unsupported():
    payload = {
        "models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemma-3-27b-it", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
        ]
    }

    assert extract_testable_models(payload) == [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
    ]


def test_serialize_results_shapes_output():
    rows = [
        (True, "models/gemini-2.5-flash", "OK"),
        (False, "models/gemini-2.0-flash", "Rate Limit (429)"),
    ]
    assert serialize_results(rows) == [
        {"success": True, "model": "models/gemini-2.5-flash", "status": "OK"},
        {"success": False, "model": "models/gemini-2.0-flash", "status": "Rate Limit (429)"},
    ]
