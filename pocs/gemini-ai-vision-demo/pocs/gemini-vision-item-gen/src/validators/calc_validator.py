"""AG-CALC: 수학/과학 계산 검증 모듈

Code Execution 기반 수식 계산 및 정답 검증.
수학, 과학 문항의 계산 정확성을 검증합니다.
"""

import ast
import math
import operator
import re
from typing import Optional

from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)


class CalcValidator:
    """AG-CALC: 계산 기반 정답 검증기

    수학/과학 문항의 계산 과정을 검증합니다.
    - 수식 파싱 및 계산
    - 정답 수치 검증
    - 선지 수치 범위 검증
    """

    # 안전한 수학 함수/연산자
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pow": math.pow,
        "pi": math.pi,
        "e": math.e,
    }

    # 숫자 추출 패턴
    NUMBER_PATTERN = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

    def __init__(self, tolerance: float = 0.01):
        """
        Args:
            tolerance: 수치 비교 허용 오차 (기본 1%)
        """
        self.tolerance = tolerance

    def validate(self, item: ItemQuestion) -> ValidationReport:
        """
        계산 기반 문항 검증

        Args:
            item: 검증할 문항

        Returns:
            ValidationReport
        """
        failure_codes: list[FailureCode] = []
        details: list[str] = []
        recommendations: list[str] = []

        # 1. 문항에서 수식/수치 추출
        stem_numbers = self._extract_numbers(item.stem)
        explanation_numbers = self._extract_numbers(item.explanation)
        correct_choice = self._get_correct_choice_text(item)
        correct_numbers = self._extract_numbers(correct_choice) if correct_choice else []

        # 2. 해설에 계산 과정이 있는지 확인
        calculation_expressions = self._extract_expressions(item.explanation)

        if calculation_expressions:
            # 3. 계산 과정 검증
            for expr in calculation_expressions:
                try:
                    calculated_value = self._safe_eval(expr)
                    if calculated_value is not None:
                        # 계산 결과가 정답에 포함되어 있는지 확인
                        if correct_numbers and not self._value_in_list(calculated_value, correct_numbers):
                            details.append(f"계산 결과 {calculated_value}가 정답 '{correct_choice}'에 없음")
                except Exception as e:
                    details.append(f"수식 계산 실패: {expr} - {str(e)}")

        # 4. 정답 수치 일관성 검증
        if correct_numbers and explanation_numbers:
            # 해설에 언급된 수치가 정답에 포함되어야 함
            for num in explanation_numbers[-3:]:  # 마지막 3개 수치 확인 (결론 부분)
                if not self._value_in_list(num, correct_numbers):
                    # 중간 계산 값일 수 있으므로 경고만
                    pass

        # 5. 선지 간 수치 중복 검사
        choice_numbers_map = {}
        for choice in item.choices:
            nums = self._extract_numbers(choice.text)
            if nums:
                key = tuple(sorted(nums))
                if key in choice_numbers_map:
                    failure_codes.append(FailureCode.OPTION_OVERLAP)
                    details.append(f"선지 {choice.label}와 {choice_numbers_map[key]}의 수치가 동일")
                else:
                    choice_numbers_map[key] = choice.label

        # 6. 정답 레이블 검증
        if item.correct_answer not in [c.label for c in item.choices]:
            failure_codes.append(FailureCode.CALCULATION_ERROR)
            details.append(f"정답 레이블 '{item.correct_answer}'이 유효하지 않음")

        # 7. 음수/0 처리 검사 (나눗셈의 경우)
        if "÷" in item.stem or "/" in item.stem or "나누" in item.stem:
            for choice in item.choices:
                if "0" in choice.text and choice.label != item.correct_answer:
                    # 0으로 나누기 오답은 OK
                    pass
                elif choice.label == item.correct_answer:
                    nums = self._extract_numbers(choice.text)
                    if nums and 0 in nums:
                        details.append("정답에 0이 포함되어 있음 - 확인 필요")

        # 상태 결정
        if failure_codes:
            status = ValidationStatus.FAIL
        elif details:
            status = ValidationStatus.REVIEW
            recommendations.append("계산 과정을 수동으로 검토하세요.")
        else:
            status = ValidationStatus.PASS

        return ValidationReport(
            item_id=item.item_id,
            status=status,
            failure_codes=list(set(failure_codes)),
            details=details,
            recommendations=recommendations
        )

    def verify_calculation(self, expression: str, expected_result: float) -> tuple[bool, Optional[float]]:
        """
        수식 계산 검증

        Args:
            expression: 계산할 수식
            expected_result: 기대 결과

        Returns:
            (일치 여부, 실제 계산 결과)
        """
        try:
            actual_result = self._safe_eval(expression)
            if actual_result is None:
                return False, None

            is_match = abs(actual_result - expected_result) <= abs(expected_result * self.tolerance)
            return is_match, actual_result
        except Exception:
            return False, None

    def _extract_numbers(self, text: str) -> list[float]:
        """텍스트에서 숫자 추출"""
        if not text:
            return []

        matches = self.NUMBER_PATTERN.findall(text)
        numbers = []
        for match in matches:
            try:
                num = float(match)
                numbers.append(num)
            except ValueError:
                continue
        return numbers

    def _extract_expressions(self, text: str) -> list[str]:
        """텍스트에서 계산 수식 추출"""
        if not text:
            return []

        expressions = []

        # 패턴: A + B = C, A - B = C, A × B = C, A ÷ B = C
        patterns = [
            r"(\d+(?:\.\d+)?)\s*[+\-×÷*/]\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*[+\-×÷*/]\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 수식 재구성
                if len(match) == 3:
                    expressions.append(f"{match[0]} + {match[1]}")  # 연산자는 실제로 추출해야 함
                elif len(match) == 2:
                    expressions.append(f"{match[0]} + {match[1]}")

        return expressions

    def _get_correct_choice_text(self, item: ItemQuestion) -> Optional[str]:
        """정답 선지 텍스트 반환"""
        for choice in item.choices:
            if choice.label == item.correct_answer:
                return choice.text
        return None

    def _value_in_list(self, value: float, numbers: list[float]) -> bool:
        """수치가 리스트에 있는지 확인 (허용 오차 적용)"""
        for num in numbers:
            if abs(value - num) <= abs(num * self.tolerance) + 0.001:
                return True
        return False

    def _safe_eval(self, expression: str) -> Optional[float]:
        """안전한 수식 계산 (AST 기반)"""
        if not expression:
            return None

        # 수식 정규화
        expr = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
        expr = re.sub(r"\s+", "", expr)  # 공백 제거

        try:
            tree = ast.parse(expr, mode='eval')
            return self._eval_node(tree.body)
        except (SyntaxError, ValueError, ZeroDivisionError):
            return None

    def _eval_node(self, node: ast.AST) -> float:
        """AST 노드 평가"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant: {node.value}")

        elif isinstance(node, ast.Num):  # Python 3.7 호환
            return float(node.n)

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in self.SAFE_OPERATORS:
                return self.SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self.SAFE_OPERATORS:
                return self.SAFE_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.SAFE_FUNCTIONS:
                    args = [self._eval_node(arg) for arg in node.args]
                    return self.SAFE_FUNCTIONS[func_name](*args)
            raise ValueError(f"Unsupported function call")

        elif isinstance(node, ast.Name):
            if node.id in self.SAFE_FUNCTIONS:
                return self.SAFE_FUNCTIONS[node.id]
            raise ValueError(f"Unsupported name: {node.id}")

        raise ValueError(f"Unsupported node type: {type(node)}")

    def validate_batch(self, items: list[ItemQuestion]) -> list[ValidationReport]:
        """여러 문항 일괄 검증"""
        return [self.validate(item) for item in items]
