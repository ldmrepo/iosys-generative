"""메타데이터 정규화 유틸리티

과목, 학년, 난이도 등의 메타데이터를 정규화하고 검증하는 유틸리티.
"""

from typing import Optional


class MetadataNormalizer:
    """메타데이터 정규화 및 검증

    다양한 형식의 입력 메타데이터를 표준 형식으로 정규화.
    """

    # 과목 코드 매핑
    SUBJECT_CODES = {
        # 코드 -> 과목명
        "01": "국어",
        "02": "영어",
        "03": "수학",
        "04": "사회",
        "05": "과학",
        "06": "역사",
        "07": "도덕",
        "08": "기술가정",
        "09": "정보",
        "10": "음악",
        "11": "미술",
        "12": "체육",
    }

    # 과목명 -> 코드 역매핑
    SUBJECT_NAMES = {v: k for k, v in SUBJECT_CODES.items()}

    # 학교급 코드
    SCHOOL_LEVEL_CODES = {
        "01": "초등학교",
        "02": "중학교",
        "03": "고등학교",
    }

    # 학년 코드 (통합)
    GRADE_CODES = {
        # 초등학교
        "01": "초1", "02": "초2", "03": "초3",
        "04": "초4", "05": "초5", "06": "초6",
        # 중학교
        "07": "중1", "08": "중2", "09": "중3",
        # 고등학교
        "10": "고1", "11": "고2", "12": "고3",
    }

    # 난이도 코드
    DIFFICULTY_CODES = {
        # 코드 -> 표준명
        "01": "easy",
        "02": "medium",
        "03": "hard",
        # 한글 별칭
        "상": "hard",
        "중": "medium",
        "하": "easy",
        # 영문 별칭
        "hard": "hard",
        "medium": "medium",
        "easy": "easy",
        "high": "hard",
        "low": "easy",
    }

    # 채점유형 코드
    QUESTION_TYPE_CODES = {
        "11": "선택형",
        "21": "진위형",
        "31": "단답형",
        "34": "완성형",
        "37": "배합형",
        "41": "서술형",
        "51": "논술형",
    }

    # 기본값
    DEFAULT_SUBJECT = "03"  # 수학
    DEFAULT_DIFFICULTY = "medium"
    DEFAULT_GRADE = ""

    def __init__(self):
        pass

    def normalize(self, metadata: dict) -> dict:
        """메타데이터 정규화 및 기본값 적용

        Args:
            metadata: 원본 메타데이터 딕셔너리

        Returns:
            정규화된 메타데이터
        """
        if metadata is None:
            metadata = {}

        normalized = {}

        # 과목 정규화
        subject = metadata.get("subject", "")
        normalized["subject"] = self.normalize_subject(subject)
        normalized["subject_code"] = self._get_subject_code(normalized["subject"])

        # 학년 정규화
        grade = metadata.get("grade", "")
        normalized["grade"] = self.normalize_grade(grade)
        normalized["grade_code"] = self._get_grade_code(normalized["grade"])

        # 학교급 추론
        normalized["school_level"] = self._infer_school_level(normalized["grade"])
        normalized["school_level_code"] = self._get_school_level_code(
            normalized["school_level"]
        )

        # 난이도 정규화
        difficulty = metadata.get("difficulty", "")
        normalized["difficulty"] = self.normalize_difficulty(difficulty)

        # 채점유형 정규화
        question_type = metadata.get("question_type", "")
        normalized["question_type"] = self.normalize_question_type(question_type)

        # 추가 메타데이터 복사
        for key in ["curriculum_code", "unit", "keywords", "variation_type"]:
            if key in metadata:
                normalized[key] = metadata[key]

        return normalized

    def normalize_subject(self, subject: str) -> str:
        """과목 정규화

        다양한 형식의 과목 입력을 표준 과목명으로 변환.

        Args:
            subject: 과목 (코드, 이름, 또는 조합)

        Returns:
            표준 과목명 (예: "수학")
        """
        if not subject:
            return self.SUBJECT_CODES.get(self.DEFAULT_SUBJECT, "수학")

        subject = str(subject).strip()

        # 코드인 경우
        if subject in self.SUBJECT_CODES:
            return self.SUBJECT_CODES[subject]

        # 이름인 경우
        if subject in self.SUBJECT_NAMES:
            return subject

        # "03 수학" 형식
        parts = subject.split(maxsplit=1)
        if parts:
            code = parts[0]
            if code in self.SUBJECT_CODES:
                return self.SUBJECT_CODES[code]
            # 이름만 있는 경우
            name = parts[-1]
            if name in self.SUBJECT_NAMES:
                return name

        # 부분 매칭 시도
        subject_lower = subject.lower()
        for name in self.SUBJECT_NAMES:
            if name in subject:
                return name

        return self.SUBJECT_CODES.get(self.DEFAULT_SUBJECT, "수학")

    def normalize_grade(self, grade: str) -> str:
        """학년 정규화

        Args:
            grade: 학년 (코드, 이름, 또는 조합)

        Returns:
            표준 학년 (예: "중2")
        """
        if not grade:
            return self.DEFAULT_GRADE

        grade = str(grade).strip()

        # 코드인 경우
        if grade in self.GRADE_CODES:
            return self.GRADE_CODES[grade]

        # 이미 표준 형식인 경우
        if self._is_standard_grade(grade):
            return grade

        # "08 중2" 형식
        parts = grade.split(maxsplit=1)
        if parts:
            code = parts[0]
            if code in self.GRADE_CODES:
                return self.GRADE_CODES[code]

        # 숫자만 있는 경우 (예: "2" -> 학교급 필요)
        if grade.isdigit():
            # 기본적으로 중학교로 가정
            num = int(grade)
            if 1 <= num <= 6:
                return f"초{num}"
            elif 1 <= num <= 3:
                return f"중{num}"

        return self.DEFAULT_GRADE

    def normalize_difficulty(self, difficulty: str) -> str:
        """난이도 정규화

        Args:
            difficulty: 난이도 (코드, 한글, 영문)

        Returns:
            표준 난이도 (easy, medium, hard)
        """
        if not difficulty:
            return self.DEFAULT_DIFFICULTY

        difficulty = str(difficulty).strip().lower()

        # 직접 매핑
        if difficulty in self.DIFFICULTY_CODES:
            return self.DIFFICULTY_CODES[difficulty]

        # "02 중" 형식
        parts = difficulty.split(maxsplit=1)
        if parts:
            code = parts[0]
            if code in self.DIFFICULTY_CODES:
                return self.DIFFICULTY_CODES[code]
            name = parts[-1] if len(parts) > 1 else parts[0]
            if name in self.DIFFICULTY_CODES:
                return self.DIFFICULTY_CODES[name]

        return self.DEFAULT_DIFFICULTY

    def normalize_question_type(self, question_type: str) -> str:
        """채점유형 정규화

        Args:
            question_type: 채점유형 (코드 또는 이름)

        Returns:
            표준 채점유형명
        """
        if not question_type:
            return ""

        question_type = str(question_type).strip()

        # 코드인 경우
        if question_type in self.QUESTION_TYPE_CODES:
            return self.QUESTION_TYPE_CODES[question_type]

        # 이미 이름인 경우
        if question_type in self.QUESTION_TYPE_CODES.values():
            return question_type

        return ""

    def validate_subject(self, subject: str) -> bool:
        """과목 유효성 검증

        Args:
            subject: 과목 (코드 또는 이름)

        Returns:
            유효 여부
        """
        if not subject:
            return False

        subject = str(subject).strip()

        # 코드 또는 이름 확인
        if subject in self.SUBJECT_CODES or subject in self.SUBJECT_NAMES:
            return True

        # "03 수학" 형식
        parts = subject.split(maxsplit=1)
        if parts:
            return parts[0] in self.SUBJECT_CODES or parts[-1] in self.SUBJECT_NAMES

        return False

    def validate_grade(self, grade: str) -> bool:
        """학년 유효성 검증

        Args:
            grade: 학년 (코드 또는 이름)

        Returns:
            유효 여부
        """
        if not grade:
            return True  # 빈 값은 허용 (옵션)

        grade = str(grade).strip()

        # 코드 확인
        if grade in self.GRADE_CODES:
            return True

        # 표준 형식 확인
        if self._is_standard_grade(grade):
            return True

        return False

    def validate_difficulty(self, difficulty: str) -> bool:
        """난이도 유효성 검증

        Args:
            difficulty: 난이도

        Returns:
            유효 여부
        """
        if not difficulty:
            return True  # 빈 값은 허용

        difficulty = str(difficulty).strip().lower()
        return difficulty in self.DIFFICULTY_CODES

    def _get_subject_code(self, subject_name: str) -> str:
        """과목명에서 코드 추출"""
        return self.SUBJECT_NAMES.get(subject_name, "")

    def _get_grade_code(self, grade: str) -> str:
        """학년에서 코드 추출"""
        for code, name in self.GRADE_CODES.items():
            if name == grade:
                return code
        return ""

    def _get_school_level_code(self, school_level: str) -> str:
        """학교급에서 코드 추출"""
        for code, name in self.SCHOOL_LEVEL_CODES.items():
            if name == school_level:
                return code
        return ""

    def _infer_school_level(self, grade: str) -> str:
        """학년에서 학교급 추론"""
        if not grade:
            return ""

        if grade.startswith("초"):
            return "초등학교"
        elif grade.startswith("중"):
            return "중학교"
        elif grade.startswith("고"):
            return "고등학교"

        return ""

    def _is_standard_grade(self, grade: str) -> bool:
        """표준 학년 형식인지 확인 (예: 초1, 중2, 고3)"""
        if len(grade) != 2:
            return False

        prefix = grade[0]
        suffix = grade[1]

        if prefix == "초" and suffix.isdigit() and 1 <= int(suffix) <= 6:
            return True
        if prefix == "중" and suffix.isdigit() and 1 <= int(suffix) <= 3:
            return True
        if prefix == "고" and suffix.isdigit() and 1 <= int(suffix) <= 3:
            return True

        return False
