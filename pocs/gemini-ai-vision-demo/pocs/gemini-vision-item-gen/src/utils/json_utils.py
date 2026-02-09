"""JSON 유틸리티"""

import json
import re
from typing import Optional


def extract_json_from_text(text: str) -> Optional[str]:
    """텍스트에서 JSON 블록 추출

    Args:
        text: JSON이 포함된 텍스트

    Returns:
        추출된 JSON 문자열 또는 None
    """
    # ```json ... ``` 패턴 찾기
    pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    match = re.search(pattern, text)
    if match:
        return match.group(1)

    # 중괄호로 시작하는 JSON (stem 키 포함)
    pattern = r'\{[\s\S]*?"stem"[\s\S]*?\}'
    match = re.search(pattern, text)
    if match:
        return match.group(0)

    # is_valid 키 포함 (검증 응답용)
    pattern = r'\{[\s\S]*?"is_valid"[\s\S]*?\}'
    match = re.search(pattern, text)
    if match:
        return match.group(0)

    return None


def parse_json_safely(json_str: str) -> Optional[dict]:
    """JSON 문자열을 안전하게 파싱

    Args:
        json_str: JSON 문자열

    Returns:
        파싱된 딕셔너리 또는 None
    """
    if not json_str:
        return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
