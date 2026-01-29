"""
latex_cleaner.py
LaTeX 수식 정리 유틸리티

IML 원본의 LaTeX는 각 문자가 공백으로 분리되어 있음.
예: '{ 1 2 }' → '12', '{ A B C D }' → 'ABCD'
"""

import re
from typing import List, Tuple


def clean_latex(latex: str) -> str:
    """
    LaTeX 수식 정리

    - 연속 숫자 사이 공백 제거: '1 2 3' → '123'
    - 연속 영문자 사이 공백 제거: 'A B C' → 'ABC'
    - 변수와 숫자 사이 공백 유지: 'x 2' → 'x2' (계수)
    - LaTeX 명령어 보존: '\\overline', '\\cfrac' 등
    - 불필요한 중첩 중괄호 정리
    """
    if not latex:
        return ""

    # 원본 저장
    original = latex

    # Step 1: 바깥쪽 중괄호 제거
    latex = latex.strip()
    if latex.startswith('{') and latex.endswith('}'):
        inner = latex[1:-1].strip()
        # 중괄호 균형 확인
        if inner.count('{') == inner.count('}'):
            latex = inner

    # Step 2: 연속된 공백을 단일 공백으로
    latex = re.sub(r'\s+', ' ', latex)

    # Step 3: 연속 숫자 사이 공백 제거
    # '1 2 3' → '123', '1 0 8' → '108'
    latex = re.sub(r'(\d)\s+(\d)', r'\1\2', latex)
    # 반복 적용 (3자리 이상 숫자)
    while re.search(r'(\d)\s+(\d)', latex):
        latex = re.sub(r'(\d)\s+(\d)', r'\1\2', latex)

    # Step 3.5: 소수점 주변 공백 제거
    # '0 . 5' → '0.5'
    latex = re.sub(r'(\d)\s*\.\s*(\d)', r'\1.\2', latex)

    # Step 4: 연속 영대문자 사이 공백 제거 (변수명, 점 이름)
    # 'A B C D' → 'ABCD'
    latex = re.sub(r'([A-Z])\s+([A-Z])', r'\1\2', latex)
    while re.search(r'([A-Z])\s+([A-Z])', latex):
        latex = re.sub(r'([A-Z])\s+([A-Z])', r'\1\2', latex)

    # Step 5: 연속 영소문자 사이 공백 제거 (단위 등)
    # 'c m' → 'cm'
    latex = re.sub(r'([a-z])\s+([a-z])', r'\1\2', latex)
    while re.search(r'([a-z])\s+([a-z])', latex):
        latex = re.sub(r'([a-z])\s+([a-z])', r'\1\2', latex)

    # Step 6: 숫자와 단위 사이 공백 정리
    # '8 cm' 는 유지하되 '~ c m' → '~cm'
    latex = re.sub(r'~\s*([a-z])', r'~\1', latex)

    # Step 7: 연산자 주변 공백 정리
    # '= 6' → '= 6' (유지), 하지만 '=  6' → '= 6'
    latex = re.sub(r'([=<>+\-])  +', r'\1 ', latex)
    latex = re.sub(r'  +([=<>+\-])', r' \1', latex)

    # Step 8: 중괄호 내부 공백 정리
    # '{ A }' → '{A}'
    latex = re.sub(r'\{\s+', '{', latex)
    latex = re.sub(r'\s+\}', '}', latex)

    # Step 9: LaTeX 명령어 정리
    # '\ overline' → '\overline'
    latex = re.sub(r'\\\s+([a-zA-Z]+)', r'\\\1', latex)

    # Step 9.5: LaTeX 명령어 뒤 중괄호 공백 제거
    # '\overline {' → '\overline{'
    latex = re.sub(r'(\\[a-zA-Z]+)\s+\{', r'\1{', latex)

    # Step 9.6: 중괄호 사이 공백 제거
    # '} {' → '}{'
    latex = re.sub(r'\}\s+\{', '}{', latex)

    # Step 9.6.5: 지수/첨자 연산자 주변 공백 제거
    # '^ {' → '^{', '_ {' → '_{'
    latex = re.sub(r'\^\s*\{', '^{', latex)
    latex = re.sub(r'_\s*\{', '_{', latex)
    latex = re.sub(r'\}\s*\^', '}^', latex)
    latex = re.sub(r'\}\s*_', '}_', latex)

    # Step 9.7: 숫자와 변수 사이 공백 제거 (계수)
    # '2 a' → '2a', '3 x' → '3x'
    latex = re.sub(r'(\d)\s+([a-zA-Z])(?![a-zA-Z])', r'\1\2', latex)

    # Step 9.8: LaTeX 명령어를 기호로 변환
    latex = re.sub(r'\\angle\b', '∠', latex)
    latex = re.sub(r'\\triangle\b', '△', latex)
    latex = re.sub(r'\\therefore\b', '∴', latex)
    latex = re.sub(r'\\because\b', '∵', latex)
    latex = re.sub(r'\\perp\b', '⊥', latex)
    latex = re.sub(r'\\parallel\b', '∥', latex)
    latex = re.sub(r'\\neq\b', '≠', latex)
    latex = re.sub(r'\\leq\b', '≤', latex)
    latex = re.sub(r'\\geq\b', '≥', latex)

    # Step 10: 특수 기호 정리
    # '° ' → '°', '△ ' → '△'
    latex = re.sub(r'(°|△|∠|∴|∵|⊥|∥|≠|≤|≥)\s+', r'\1', latex)
    latex = re.sub(r'\s+(°|△|∠|∴|∵|⊥|∥|≠|≤|≥)', r'\1', latex)

    # Step 11: degree 기호 정리
    # '\degree' 앞 숫자와 붙이기
    latex = re.sub(r'(\d)\s*\\degree', r'\1°', latex)

    # Step 12: 분수 정리
    # '\cfrac { 1 } { 2 }' → '\cfrac{1}{2}'
    latex = re.sub(r'\\cfrac\s*\{', r'\\cfrac{', latex)
    latex = re.sub(r'\\frac\s*\{', r'\\frac{', latex)

    # Step 13: 괄호 앞뒤 공백 정리
    latex = re.sub(r'\(\s+', '(', latex)
    latex = re.sub(r'\s+\)', ')', latex)

    # Step 14: 쉼표 뒤 공백 정리
    latex = re.sub(r',\s*', ', ', latex)

    # Step 15: 최종 공백 정리
    latex = re.sub(r'\s+', ' ', latex)
    latex = latex.strip()

    return latex


def clean_latex_in_text(text: str) -> str:
    """
    텍스트 내의 $...$ 형식 LaTeX를 정리
    """
    if not text or '$' not in text:
        return text

    def replace_latex(match):
        latex = match.group(1)
        cleaned = clean_latex(latex)
        return f'${cleaned}$'

    # $...$ 패턴 찾아서 정리
    result = re.sub(r'\$([^$]+)\$', replace_latex, text)

    return result


def test_cleaner():
    """테스트"""
    test_cases = [
        ('{  A  B  C  D  }', 'ABCD'),
        ('{  8  ~  c  m  }', '8 ~cm'),
        ('{ { \\overline {  F  C  } } =  6  ~  c  m  }', '{\\overline{FC}} = 6 ~cm'),
        ('{  1 0 8  }', '108'),
        ('{  △  E  F  C  }', '△EFC'),
        ('{ \\cfrac {  1  } {  2  } }', '\\cfrac{1}{2}'),
        ('{  x  +  2  a  >  1  }', 'x + 2a > 1'),
        ('{  \\angle  A  =  1 0 8  \\degree  }', '∠A = 108°'),
    ]

    print("LaTeX Cleaner Test Results:")
    print("=" * 60)

    for original, expected in test_cases:
        result = clean_latex(original)
        status = "✓" if result == expected else "✗"
        print(f"{status} Input:    {original}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()


if __name__ == "__main__":
    test_cleaner()
