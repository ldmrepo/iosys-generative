"""프로세서 모듈

파이프라인 각 단계의 처리 로직을 담당하는 프로세서 모듈.

Processors:
- P1InputProcessor: 입력 처리 (QTI 파싱, 이미지 검증, 메타데이터 정규화)
- P5OutputProcessor: 출력 처리 (이미지 위치 보존, 이미지 생성, QTI/IML 포맷팅)
"""

from .p1_input import P1InputProcessor
from .p5_output import P5OutputProcessor

__all__ = ["P1InputProcessor", "P5OutputProcessor"]
