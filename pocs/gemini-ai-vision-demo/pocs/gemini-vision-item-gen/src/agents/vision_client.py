"""Gemini Vision API 클라이언트 - Agentic Vision 지원

v3.0.0: 자연어 기반 이미지 분석
- 구조화된 정보 추출 대신 자연어 설명 출력
- 이미지 내용 유형 및 시각 요소 식별
"""

import json
import time
from pathlib import Path
from typing import Optional
from PIL import Image
import io

from google import genai
from google.genai import types

from ..core.config import settings
from ..core.schemas import PhaseLog, PhaseType, EvidencePack
from ..utils.json_utils import extract_json_from_text


class GeminiVisionClient:
    """Gemini API 클라이언트 with Agentic Vision 지원

    v3.0.0: 자연어 기반 이미지 분석
    - describe_image(): 이미지를 자연어로 상세 설명
    - extract_evidence(): 자연어 설명에서 EvidencePack 생성
    """

    # v3.0.0: 자연어 이미지 설명 프롬프트
    DESCRIBE_IMAGE_PROMPT = """이 이미지를 자세히 설명해주세요.

1. **이미지에 무엇이 보이나요?**
   - 주요 객체, 기호, 텍스트, 그래프, 도형 등을 구체적으로 나열하세요.

2. **각 요소의 의미는 무엇인가요?**
   - 색상, 위치, 크기, 관계 등을 설명하세요.
   - 텍스트가 있다면 정확히 읽어주세요.
   - 숫자나 수치가 있다면 정확히 기록하세요.

3. **교육 문항에서 이 이미지가 어떤 역할을 할 수 있나요?**
   - 이 이미지로 어떤 질문을 만들 수 있을지 생각해보세요.

구체적이고 상세하게 설명해주세요. 추측은 피하고 이미지에서 직접 확인 가능한 내용만 기술하세요.

마지막에 다음 JSON 형식으로 요약을 추가해주세요:
```json
{
    "content_type": "이미지 유형 (표지판, 그래프, 지도, 도형, 실험 장치, 사진, 그림 등)",
    "visual_elements": ["시각 요소1", "시각 요소2", "시각 요소3"]
}
```"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = settings.gemini_model
        self.phase_logs: list[PhaseLog] = []

    def _load_image(self, image_path: str | Path) -> tuple[bytes, str]:
        """이미지 로드 및 바이트 변환"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {path}")

        with Image.open(path) as img:
            # 이미지 포맷 확인
            img_format = img.format or "PNG"
            mime_type = f"image/{img_format.lower()}"

            # 바이트로 변환
            buffer = io.BytesIO()
            img.save(buffer, format=img_format)
            image_bytes = buffer.getvalue()

        return image_bytes, mime_type

    def _log_phase(
        self,
        phase: PhaseType,
        input_data: dict,
        output_data: dict,
        code_executed: Optional[str] = None,
        duration_ms: int = 0
    ) -> PhaseLog:
        """단계별 로그 기록"""
        log = PhaseLog(
            phase=phase,
            input_data=input_data,
            output_data=output_data,
            code_executed=code_executed,
            duration_ms=duration_ms
        )
        self.phase_logs.append(log)
        return log

    def analyze_image_with_agentic_vision(
        self,
        image_path: str | Path,
        prompt: str,
        enable_code_execution: bool = True
    ) -> dict:
        """
        Agentic Vision을 사용한 이미지 분석

        Args:
            image_path: 분석할 이미지 경로
            prompt: 분석 프롬프트
            enable_code_execution: 코드 실행 활성화 (Agentic Vision)

        Returns:
            분석 결과 딕셔너리
        """
        self.phase_logs = []  # 로그 초기화

        # 이미지 로드
        image_bytes, mime_type = self._load_image(image_path)

        # Think 단계 로깅
        start_time = time.time()
        self._log_phase(
            phase=PhaseType.THINK,
            input_data={"image_path": str(image_path), "prompt": prompt[:100]},
            output_data={"status": "planning"}
        )

        # API 호출 설정
        tools = []
        if enable_code_execution:
            tools.append(types.Tool(code_execution=types.ToolCodeExecution()))

        config = types.GenerateContentConfig(
            tools=tools if tools else None,
            temperature=0.7,
        )

        # 컨텐츠 구성
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=prompt)
                ]
            )
        ]

        # Act 단계 - API 호출
        act_start = time.time()
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            act_duration = int((time.time() - act_start) * 1000)

            # 응답 파싱
            result = self._parse_response(response)

            # Act 단계 로깅
            self._log_phase(
                phase=PhaseType.ACT,
                input_data={"model": self.model_name, "code_execution": enable_code_execution},
                output_data={"response_length": len(result.get("text", ""))},
                code_executed=result.get("code_executed"),
                duration_ms=act_duration
            )

            # Observe 단계 로깅
            total_duration = int((time.time() - start_time) * 1000)
            self._log_phase(
                phase=PhaseType.OBSERVE,
                input_data={"raw_response": result.get("text", "")[:200]},
                output_data={"parsed": True, "total_duration_ms": total_duration},
                duration_ms=total_duration - act_duration
            )

            result["phase_logs"] = self.phase_logs
            result["total_duration_ms"] = total_duration

            return result

        except Exception as e:
            self._log_phase(
                phase=PhaseType.ACT,
                input_data={"error": True},
                output_data={"error_message": str(e)}
            )
            raise

    def _parse_response(self, response) -> dict:
        """API 응답 파싱"""
        result = {
            "text": "",
            "code_executed": None,
            "code_output": None,
            "raw_parts": []
        }

        if not response.candidates:
            return result

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return result

        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                result["text"] += part.text
                result["raw_parts"].append({"type": "text", "content": part.text})
            elif hasattr(part, 'executable_code') and part.executable_code:
                code = part.executable_code.code
                result["code_executed"] = code
                result["raw_parts"].append({"type": "code", "content": code})
            elif hasattr(part, 'code_execution_result') and part.code_execution_result:
                output = part.code_execution_result.output
                result["code_output"] = output
                result["raw_parts"].append({"type": "code_output", "content": output})

        return result

    def describe_image(self, image_path: str | Path) -> dict:
        """v3.0.0: 이미지를 자연어로 상세 설명

        Args:
            image_path: 분석할 이미지 경로

        Returns:
            {
                "image_description": "자연어 이미지 설명",
                "content_type": "이미지 유형",
                "visual_elements": ["요소1", "요소2", ...]
            }
        """
        result = self.analyze_image_with_agentic_vision(
            image_path=image_path,
            prompt=self.DESCRIBE_IMAGE_PROMPT,
            enable_code_execution=False  # 자연어 설명에는 코드 실행 불필요
        )

        text = result.get("text", "")

        # JSON 요약 추출
        content_type = ""
        visual_elements = []

        json_str = extract_json_from_text(text)
        if json_str:
            try:
                summary = json.loads(json_str)
                content_type = summary.get("content_type", "")
                visual_elements = summary.get("visual_elements", [])
            except json.JSONDecodeError:
                pass

        # JSON 부분을 제외한 설명 텍스트
        if "```json" in text:
            image_description = text.split("```json")[0].strip()
        else:
            image_description = text

        return {
            "image_description": image_description,
            "content_type": content_type,
            "visual_elements": visual_elements,
            "raw_response": text,
            "phase_logs": result.get("phase_logs", []),
            "total_duration_ms": result.get("total_duration_ms", 0),
        }

    def extract_evidence(self, analysis_result: dict) -> EvidencePack:
        """분석 결과에서 Evidence Pack 추출

        v3.0.0: 자연어 설명 기반 EvidencePack 생성
        """
        text = analysis_result.get("text", "")

        evidence = EvidencePack(
            analysis_summary=text[:500]
        )

        # v3.0.0: 자연어 이미지 설명 추가
        if "image_description" in analysis_result:
            evidence.image_description = analysis_result["image_description"]
            evidence.content_type = analysis_result.get("content_type", "")
            evidence.visual_elements = analysis_result.get("visual_elements", [])
        else:
            # 레거시: JSON 요약 추출
            json_str = extract_json_from_text(text)
            if json_str:
                try:
                    summary = json.loads(json_str)
                    evidence.content_type = summary.get("content_type", "")
                    evidence.visual_elements = summary.get("visual_elements", [])
                except json.JSONDecodeError:
                    pass

            # JSON 제외한 설명
            if "```json" in text:
                evidence.image_description = text.split("```json")[0].strip()
            else:
                evidence.image_description = text

        # 텍스트에서 사실 추출 (간단한 파싱)
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("*") or line.startswith("•")):
                fact = line.lstrip("-*• ").strip()
                if fact:
                    evidence.extracted_facts.append(fact)

        # 코드 실행 결과가 있으면 추가
        if analysis_result.get("code_output"):
            evidence.extracted_facts.append(f"[코드 실행 결과] {analysis_result['code_output'][:200]}")

        return evidence

    def get_phase_logs(self) -> list[PhaseLog]:
        """현재 세션의 단계별 로그 반환"""
        return self.phase_logs.copy()

    def generate_text_only(self, prompt: str) -> dict:
        """텍스트 전용 생성 (이미지 없이)

        Args:
            prompt: 생성 프롬프트

        Returns:
            생성 결과 딕셔너리
        """
        self.phase_logs = []

        start_time = time.time()
        self._log_phase(
            phase=PhaseType.THINK,
            input_data={"prompt": prompt[:100]},
            output_data={"status": "planning"}
        )

        config = types.GenerateContentConfig(
            temperature=0.7,
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]

        act_start = time.time()
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            act_duration = int((time.time() - act_start) * 1000)

            result = self._parse_response(response)

            self._log_phase(
                phase=PhaseType.ACT,
                input_data={"model": self.model_name},
                output_data={"response_length": len(result.get("text", ""))},
                duration_ms=act_duration
            )

            total_duration = int((time.time() - start_time) * 1000)
            self._log_phase(
                phase=PhaseType.OBSERVE,
                input_data={"raw_response": result.get("text", "")[:200]},
                output_data={"parsed": True, "total_duration_ms": total_duration},
                duration_ms=total_duration - act_duration
            )

            result["phase_logs"] = self.phase_logs
            result["total_duration_ms"] = total_duration

            return result

        except Exception as e:
            self._log_phase(
                phase=PhaseType.ACT,
                input_data={"error": True},
                output_data={"error_message": str(e)}
            )
            raise
