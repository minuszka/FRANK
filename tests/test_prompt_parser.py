from app.services.image_prompt_service import normalize_image_payload, parse_image_json


def test_parse_image_json_extracts_embedded_object() -> None:
    raw = """
    Sure, here is JSON:
    {"action":"generate_image","prompt":"cyberpunk cat","width":1024,"height":1024}
    """
    parsed = parse_image_json(raw)
    assert parsed is not None
    assert parsed["prompt"] == "cyberpunk cat"


def test_normalize_image_payload_applies_defaults() -> None:
    defaults = {
        "width": 1024,
        "height": 1024,
        "steps": 28,
        "guidance": 4.0,
        "negative_prompt": "blurry",
        "output_format": "png",
    }
    payload = {"prompt": "old sailor portrait", "steps": 9999, "guidance": -2}
    normalized = normalize_image_payload(payload, defaults, "fallback text")
    assert normalized["prompt"] == "old sailor portrait"
    assert normalized["steps"] == 120
    assert normalized["guidance"] == 1.0
    assert normalized["negative_prompt"] == "blurry"

