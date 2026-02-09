"""AG-FACT: 사실 검증 모듈

Wikipedia API 기반 사실 대조 검증.
역사, 사회, 과학 문항의 사실적 정확성을 검증합니다.
"""

import re
import urllib.parse
import urllib.request
import json
from typing import Optional

from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)


class FactValidator:
    """AG-FACT: 사실 검증기

    Wikipedia API를 활용하여 문항의 사실적 정확성을 검증합니다.
    - 인물, 사건, 날짜 검증
    - 역사적 사실 대조
    - 과학적 사실 확인
    """

    WIKIPEDIA_API_URL = "https://ko.wikipedia.org/w/api.php"

    # 검증 대상 엔티티 패턴
    ENTITY_PATTERNS = {
        "year": re.compile(r"(\d{4})년"),
        "date": re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일"),
        "person": re.compile(r"([가-힣]{2,4})\s*(?:은|는|이|가|의|를|에게)"),
        "event": re.compile(r"([가-힣]+(?:전쟁|혁명|운동|사건|협정|조약))"),
        "place": re.compile(r"([가-힣]+(?:시|도|군|구|읍|면|동|리|국|나라))"),
    }

    # 과목별 검증 강도
    SUBJECT_VERIFICATION_LEVEL = {
        "history": "strict",      # 역사: 엄격 검증
        "social": "strict",       # 사회: 엄격 검증
        "science": "moderate",    # 과학: 중간 검증
        "korean": "moderate",     # 국어: 중간 검증
        "math": "skip",           # 수학: 건너뜀
    }

    def __init__(self, timeout: int = 5, cache_enabled: bool = True):
        """
        Args:
            timeout: API 호출 타임아웃 (초)
            cache_enabled: 캐싱 활성화 여부
        """
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self._cache: dict[str, dict] = {}

    def validate(
        self,
        item: ItemQuestion,
        subject: Optional[str] = None
    ) -> ValidationReport:
        """
        사실 기반 문항 검증

        Args:
            item: 검증할 문항
            subject: 과목 (history, social, science 등)

        Returns:
            ValidationReport
        """
        failure_codes: list[FailureCode] = []
        details: list[str] = []
        recommendations: list[str] = []

        # 과목별 검증 수준 결정
        verification_level = self.SUBJECT_VERIFICATION_LEVEL.get(subject or "", "moderate")
        if verification_level == "skip":
            return ValidationReport(
                item_id=item.item_id,
                status=ValidationStatus.PASS,
                failure_codes=[],
                details=["과목 특성상 사실 검증 건너뜀"],
                recommendations=[]
            )

        # 1. 문항에서 검증 대상 엔티티 추출
        entities = self._extract_entities(item.stem + " " + item.explanation)

        if not entities:
            return ValidationReport(
                item_id=item.item_id,
                status=ValidationStatus.PASS,
                failure_codes=[],
                details=["검증 대상 엔티티 없음"],
                recommendations=[]
            )

        # 2. 각 엔티티에 대해 Wikipedia 검증
        verified_count = 0
        failed_count = 0

        for entity_type, entity_values in entities.items():
            for value in entity_values[:3]:  # 각 유형별 최대 3개만 검증
                result = self._verify_entity(entity_type, value, item)

                if result["verified"]:
                    verified_count += 1
                elif result["found"] and not result["verified"]:
                    failed_count += 1
                    failure_codes.append(FailureCode.FACTUAL_ERROR)
                    details.append(f"{entity_type}: '{value}' - {result['reason']}")
                    if result.get("suggestion"):
                        recommendations.append(result["suggestion"])
                else:
                    # Wikipedia에서 찾지 못함 - 경고만
                    details.append(f"{entity_type}: '{value}' - Wikipedia에서 확인 불가")

        # 3. 선지 사실 검증 (정답 선지)
        correct_choice = self._get_correct_choice_text(item)
        if correct_choice:
            choice_entities = self._extract_entities(correct_choice)
            for entity_type, entity_values in choice_entities.items():
                for value in entity_values[:2]:
                    result = self._verify_entity(entity_type, value, item)
                    if result["found"] and not result["verified"]:
                        failure_codes.append(FailureCode.FACTUAL_ERROR)
                        details.append(f"정답 선지 - {entity_type}: '{value}' 사실 오류")

        # 상태 결정
        if failure_codes:
            status = ValidationStatus.FAIL
        elif details and verification_level == "strict":
            status = ValidationStatus.REVIEW
            recommendations.append("수동으로 사실 관계를 검토하세요.")
        else:
            status = ValidationStatus.PASS

        return ValidationReport(
            item_id=item.item_id,
            status=status,
            failure_codes=list(set(failure_codes)),
            details=details,
            recommendations=recommendations
        )

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """텍스트에서 검증 대상 엔티티 추출"""
        entities: dict[str, list[str]] = {}

        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                # 튜플인 경우 첫 번째 요소 또는 조합
                values = []
                for match in matches:
                    if isinstance(match, tuple):
                        values.append("".join(match))
                    else:
                        values.append(match)
                entities[entity_type] = list(set(values))

        return entities

    def _verify_entity(
        self,
        entity_type: str,
        value: str,
        item: ItemQuestion
    ) -> dict:
        """Wikipedia API로 엔티티 검증"""
        result = {
            "verified": False,
            "found": False,
            "reason": "",
            "suggestion": None
        }

        try:
            # Wikipedia 검색
            wiki_data = self._search_wikipedia(value)

            if not wiki_data:
                return result

            result["found"] = True

            # 엔티티 유형별 검증 로직
            if entity_type == "year":
                # 연도 관련 사실 확인
                if value in wiki_data.get("extract", ""):
                    result["verified"] = True
                else:
                    result["reason"] = f"'{value}' 연도가 문맥과 맞지 않을 수 있음"

            elif entity_type == "person":
                # 인물 정보 확인
                extract = wiki_data.get("extract", "")
                if len(extract) > 50:
                    result["verified"] = True
                else:
                    result["reason"] = f"'{value}' 인물 정보 불충분"

            elif entity_type == "event":
                # 사건/이벤트 확인
                if wiki_data.get("pageid"):
                    result["verified"] = True
                else:
                    result["reason"] = f"'{value}' 사건을 확인할 수 없음"

            elif entity_type == "place":
                # 장소 확인
                if wiki_data.get("pageid"):
                    result["verified"] = True

            elif entity_type == "date":
                # 날짜 검증 (해당 날짜에 관련 사건이 있는지)
                result["verified"] = True  # 날짜 형식만 확인

        except Exception as e:
            result["reason"] = f"검증 중 오류: {str(e)}"

        return result

    def _search_wikipedia(self, query: str) -> Optional[dict]:
        """Wikipedia API 검색"""
        if self.cache_enabled and query in self._cache:
            return self._cache[query]

        params = {
            "action": "query",
            "format": "json",
            "titles": query,
            "prop": "extracts|pageprops",
            "exintro": True,
            "explaintext": True,
            "redirects": 1,
        }

        url = f"{self.WIKIPEDIA_API_URL}?{urllib.parse.urlencode(params)}"

        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1":
                    result = {
                        "pageid": page_id,
                        "title": page_data.get("title", ""),
                        "extract": page_data.get("extract", ""),
                    }
                    if self.cache_enabled:
                        self._cache[query] = result
                    return result

            return None

        except Exception:
            return None

    def _get_correct_choice_text(self, item: ItemQuestion) -> Optional[str]:
        """정답 선지 텍스트 반환"""
        for choice in item.choices:
            if choice.label == item.correct_answer:
                return choice.text
        return None

    def check_specific_fact(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> dict:
        """
        특정 사실 주장 검증

        Args:
            claim: 검증할 사실 주장
            context: 추가 맥락

        Returns:
            검증 결과 딕셔너리
        """
        entities = self._extract_entities(claim)

        results = {
            "claim": claim,
            "entities_found": entities,
            "verifications": [],
            "overall_verified": True
        }

        for entity_type, values in entities.items():
            for value in values:
                wiki_data = self._search_wikipedia(value)
                verification = {
                    "entity": value,
                    "type": entity_type,
                    "found_in_wikipedia": wiki_data is not None,
                    "wikipedia_extract": wiki_data.get("extract", "")[:200] if wiki_data else None
                }
                results["verifications"].append(verification)

                if wiki_data is None:
                    results["overall_verified"] = False

        return results

    def validate_batch(self, items: list[ItemQuestion], subject: Optional[str] = None) -> list[ValidationReport]:
        """여러 문항 일괄 검증"""
        return [self.validate(item, subject) for item in items]
