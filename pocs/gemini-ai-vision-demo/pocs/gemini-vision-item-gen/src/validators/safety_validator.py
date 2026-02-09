"""AG-SAFE: 안전 및 편향 검사 모듈

문항의 편향성, 부적절한 내용, 안전 위반 여부를 검사합니다.
"""

import re
from typing import Optional

from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)


class SafetyValidator:
    """AG-SAFE: 안전 및 편향 검증기

    교육 문항의 안전성과 공정성을 검증합니다.
    - 성별/인종/종교/지역 편향
    - 부적절한 표현
    - 민감한 주제
    - 연령 부적합 내용
    """

    # 편향 키워드 패턴
    BIAS_PATTERNS = {
        "gender": {
            "keywords": [
                r"여자(?:는|가|들은)\s*(?:수학|과학|운동)을?\s*못",
                r"남자(?:는|가|들은)\s*(?:가사|요리|육아)를?\s*못",
                r"(?:남자|여자)(?:다운|답게)",
                r"(?:남자|여자)\s*(?:일|직업)",
            ],
            "level": "high",
            "message": "성별 고정관념 표현 발견",
        },
        "region": {
            "keywords": [
                r"(?:경상|전라|충청|강원|제주)\s*(?:사람|도민)(?:은|들은)\s*(?:무식|게으르|거칠)",
                r"(?:서울|지방)\s*사람(?:은|들은)",
            ],
            "level": "high",
            "message": "지역 차별 표현 발견",
        },
        "age": {
            "keywords": [
                r"(?:노인|어르신)(?:은|들은)\s*(?:무식|고집|느림)",
                r"(?:젊은|어린)\s*사람(?:은|들은)\s*(?:무모|철없|버릇없)",
                r"꼰대",
                r"틀딱",
            ],
            "level": "medium",
            "message": "연령 차별 표현 발견",
        },
        "disability": {
            "keywords": [
                r"(?:장애인|불구자|병신|벙어리|귀머거리)",
                r"(?:정신|지체)\s*(?:이상|미약|결함)",
            ],
            "level": "high",
            "message": "장애 차별 표현 발견",
        },
        "religion": {
            "keywords": [
                r"(?:기독교|불교|이슬람|천주교|무속)(?:는|이|가)\s*(?:미신|사이비|문제)",
            ],
            "level": "high",
            "message": "종교 차별 표현 발견",
        },
        "nationality": {
            "keywords": [
                r"(?:중국인|일본인|미국인)(?:은|들은)\s*(?:더럽|무식|야만)",
                r"(?:조선족|다문화)\s*(?:문제|범죄)",
            ],
            "level": "high",
            "message": "국적/민족 차별 표현 발견",
        },
    }

    # 부적절한 내용 패턴
    INAPPROPRIATE_PATTERNS = {
        "violence": {
            "keywords": [
                r"(?:살인|폭행|학대|고문|강간)",
                r"(?:잔인하게|피투성이)",
            ],
            "level": "high",
            "message": "폭력적 내용 발견",
        },
        "profanity": {
            "keywords": [
                r"(?:씨발|좆|병신|지랄|개새끼|년|놈)",
                r"(?:ㅅㅂ|ㅈㄹ|ㅂㅅ)",
            ],
            "level": "high",
            "message": "비속어 발견",
        },
        "sexual": {
            "keywords": [
                r"(?:성관계|섹스|음란|야동)",
                r"(?:가슴|엉덩이|성기)",
            ],
            "level": "high",
            "message": "성적 내용 발견",
        },
        "gambling": {
            "keywords": [
                r"(?:도박|카지노|베팅|슬롯머신)",
            ],
            "level": "medium",
            "message": "도박 관련 내용 발견",
        },
        "drugs": {
            "keywords": [
                r"(?:마약|대마초|필로폰|코카인|헤로인)",
                r"(?:흡입|투약).*(?:쾌감|기분)",
            ],
            "level": "high",
            "message": "약물 관련 부적절한 내용 발견",
        },
    }

    # 민감한 주제 패턴
    SENSITIVE_PATTERNS = {
        "political": {
            "keywords": [
                r"(?:보수|진보)(?:는|가)\s*(?:옳|틀|좋|나쁨)",
                r"(?:정당|정치인)\s*(?:비판|비난|공격)",
                r"(?:민주당|국민의힘|더불어민주당)",
            ],
            "level": "medium",
            "message": "정치적 편향 가능성",
        },
        "suicide": {
            "keywords": [
                r"(?:자살|자해|극단적\s*선택)",
                r"(?:삶을\s*끝|죽고\s*싶)",
            ],
            "level": "high",
            "message": "자살/자해 관련 민감한 내용",
        },
        "historical_controversy": {
            "keywords": [
                r"(?:친일|반일|위안부|독도|일본해)",
                r"(?:5\.18|광주|민주화)",
            ],
            "level": "medium",
            "message": "역사적 논쟁 주제 - 주의 필요",
        },
    }

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: 엄격 모드 (medium 레벨도 FAIL 처리)
        """
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self):
        """패턴 컴파일"""
        self._compiled_bias = {}
        for category, config in self.BIAS_PATTERNS.items():
            self._compiled_bias[category] = {
                "patterns": [re.compile(p, re.IGNORECASE) for p in config["keywords"]],
                "level": config["level"],
                "message": config["message"],
            }

        self._compiled_inappropriate = {}
        for category, config in self.INAPPROPRIATE_PATTERNS.items():
            self._compiled_inappropriate[category] = {
                "patterns": [re.compile(p, re.IGNORECASE) for p in config["keywords"]],
                "level": config["level"],
                "message": config["message"],
            }

        self._compiled_sensitive = {}
        for category, config in self.SENSITIVE_PATTERNS.items():
            self._compiled_sensitive[category] = {
                "patterns": [re.compile(p, re.IGNORECASE) for p in config["keywords"]],
                "level": config["level"],
                "message": config["message"],
            }

    def validate(self, item: ItemQuestion) -> ValidationReport:
        """
        안전 및 편향 검사

        Args:
            item: 검사할 문항

        Returns:
            ValidationReport
        """
        failure_codes: list[FailureCode] = []
        details: list[str] = []
        recommendations: list[str] = []

        # 전체 텍스트 추출
        full_text = self._extract_full_text(item)

        # 1. 편향 검사
        bias_results = self._check_patterns(full_text, self._compiled_bias)
        for result in bias_results:
            if result["level"] == "high":
                failure_codes.append(FailureCode.BIAS_DETECTED)
                details.append(f"[편향] {result['message']}: '{result['matched']}'")
                recommendations.append(f"{result['category']} 관련 표현을 중립적으로 수정하세요.")
            elif result["level"] == "medium" and self.strict_mode:
                failure_codes.append(FailureCode.BIAS_DETECTED)
                details.append(f"[편향 경고] {result['message']}: '{result['matched']}'")

        # 2. 부적절한 내용 검사
        inappropriate_results = self._check_patterns(full_text, self._compiled_inappropriate)
        for result in inappropriate_results:
            failure_codes.append(FailureCode.SAFETY_VIOLATION)
            details.append(f"[부적절] {result['message']}: '{result['matched']}'")
            recommendations.append(f"교육 문항에 부적절한 {result['category']} 내용을 제거하세요.")

        # 3. 민감한 주제 검사
        sensitive_results = self._check_patterns(full_text, self._compiled_sensitive)
        for result in sensitive_results:
            if result["level"] == "high":
                failure_codes.append(FailureCode.SAFETY_VIOLATION)
                details.append(f"[민감] {result['message']}: '{result['matched']}'")
            else:
                details.append(f"[주의] {result['message']}: '{result['matched']}'")
                recommendations.append(f"'{result['category']}' 주제 다룸 시 중립성 유지하세요.")

        # 4. 선지 균형 검사 (성별/인물 분포)
        balance_check = self._check_choice_balance(item)
        if not balance_check["balanced"]:
            details.append(f"[균형] {balance_check['message']}")
            recommendations.append("선지에 다양한 성별/배경의 인물을 포함하세요.")

        # 상태 결정
        if failure_codes:
            status = ValidationStatus.FAIL
        elif details:
            status = ValidationStatus.REVIEW
        else:
            status = ValidationStatus.PASS

        return ValidationReport(
            item_id=item.item_id,
            status=status,
            failure_codes=list(set(failure_codes)),
            details=details,
            recommendations=recommendations
        )

    def _extract_full_text(self, item: ItemQuestion) -> str:
        """문항 전체 텍스트 추출"""
        texts = [item.stem, item.explanation]
        for choice in item.choices:
            texts.append(choice.text)
        return " ".join(texts)

    def _check_patterns(
        self,
        text: str,
        compiled_patterns: dict
    ) -> list[dict]:
        """패턴 매칭 검사"""
        results = []

        for category, config in compiled_patterns.items():
            for pattern in config["patterns"]:
                match = pattern.search(text)
                if match:
                    results.append({
                        "category": category,
                        "level": config["level"],
                        "message": config["message"],
                        "matched": match.group()[:50],  # 매칭된 텍스트 (최대 50자)
                    })
                    break  # 카테고리당 하나만 보고

        return results

    def _check_choice_balance(self, item: ItemQuestion) -> dict:
        """선지 내 인물 균형 검사"""
        male_patterns = re.compile(r"(?:철수|영수|민수|준호|지훈|남자|아버지|형|오빠|삼촌|할아버지)")
        female_patterns = re.compile(r"(?:영희|수지|민희|지현|여자|어머니|언니|누나|이모|할머니)")

        male_count = 0
        female_count = 0

        for choice in item.choices:
            if male_patterns.search(choice.text):
                male_count += 1
            if female_patterns.search(choice.text):
                female_count += 1

        # 3개 이상 선지에 인물이 있고, 한쪽 성별만 있으면 불균형
        total = male_count + female_count
        if total >= 3 and (male_count == 0 or female_count == 0):
            return {
                "balanced": False,
                "message": f"선지 인물 성별 불균형 (남:{male_count}, 여:{female_count})"
            }

        return {"balanced": True, "message": ""}

    def quick_check(self, text: str) -> dict:
        """
        빠른 안전 검사 (단일 텍스트)

        Args:
            text: 검사할 텍스트

        Returns:
            검사 결과 딕셔너리
        """
        issues = []

        # 편향 체크
        for result in self._check_patterns(text, self._compiled_bias):
            issues.append({"type": "bias", **result})

        # 부적절 체크
        for result in self._check_patterns(text, self._compiled_inappropriate):
            issues.append({"type": "inappropriate", **result})

        # 민감 체크
        for result in self._check_patterns(text, self._compiled_sensitive):
            issues.append({"type": "sensitive", **result})

        return {
            "text": text[:100],
            "is_safe": len(issues) == 0,
            "issues": issues
        }

    def validate_batch(self, items: list[ItemQuestion]) -> list[ValidationReport]:
        """여러 문항 일괄 검증"""
        return [self.validate(item) for item in items]
