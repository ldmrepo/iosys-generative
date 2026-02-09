"""JSON 유틸리티 테스트"""

import pytest
from src.utils.json_utils import extract_json_from_text, parse_json_safely


class TestExtractJsonFromText:
    """extract_json_from_text 함수 테스트"""

    def test_extract_from_code_block(self):
        """코드 블록에서 JSON 추출"""
        text = '''여기에 응답입니다.

```json
{"stem": "질문입니다", "correct_answer": "A"}
```

추가 설명입니다.'''
        result = extract_json_from_text(text)
        assert result is not None
        assert '"stem"' in result
        assert '"correct_answer"' in result

    def test_extract_from_code_block_without_json_marker(self):
        """json 마커 없는 코드 블록에서 추출"""
        text = '''응답:

```
{"stem": "질문", "choices": []}
```'''
        result = extract_json_from_text(text)
        assert result is not None
        assert '"stem"' in result

    def test_extract_raw_json_with_stem(self):
        """stem 키가 있는 raw JSON 추출"""
        text = '응답: {"stem": "질문입니다", "correct_answer": "B"}'
        result = extract_json_from_text(text)
        assert result is not None
        assert '"stem"' in result

    def test_extract_raw_json_with_is_valid(self):
        """is_valid 키가 있는 raw JSON 추출 (검증 응답)"""
        text = '검증 결과: {"is_valid": true, "failure_codes": []}'
        result = extract_json_from_text(text)
        assert result is not None
        assert '"is_valid"' in result

    def test_no_json_returns_none(self):
        """JSON이 없으면 None 반환"""
        text = "이것은 일반 텍스트입니다."
        result = extract_json_from_text(text)
        assert result is None

    def test_empty_text_returns_none(self):
        """빈 텍스트는 None 반환"""
        result = extract_json_from_text("")
        assert result is None


class TestParseJsonSafely:
    """parse_json_safely 함수 테스트"""

    def test_valid_json(self):
        """유효한 JSON 파싱"""
        json_str = '{"key": "value", "number": 123}'
        result = parse_json_safely(json_str)
        assert result is not None
        assert result["key"] == "value"
        assert result["number"] == 123

    def test_invalid_json_returns_none(self):
        """유효하지 않은 JSON은 None 반환"""
        result = parse_json_safely("{invalid json}")
        assert result is None

    def test_empty_string_returns_none(self):
        """빈 문자열은 None 반환"""
        result = parse_json_safely("")
        assert result is None

    def test_none_returns_none(self):
        """None 입력은 None 반환"""
        result = parse_json_safely(None)  # type: ignore
        assert result is None
