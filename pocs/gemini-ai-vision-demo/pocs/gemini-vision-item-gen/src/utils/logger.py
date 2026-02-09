"""감사 로깅 모듈"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..core.config import settings
from ..core.schemas import GenerationLog, ValidationReport, ItemQuestion


class AuditLogger:
    """감사 및 추적 로깅 시스템"""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or settings.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Python 로거 설정
        self.logger = logging.getLogger("agentic_vision")
        self.logger.setLevel(getattr(logging, settings.log_level.upper()))

        # 파일 핸들러
        log_file = self.log_dir / f"audit-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        self.logger.addHandler(file_handler)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s: %(message)s")
        )
        self.logger.addHandler(console_handler)

    def log_generation_start(self, session_id: str, image_path: str, item_type: str):
        """문항 생성 시작 로깅"""
        self.logger.info(
            f"[GEN_START] session={session_id}, image={image_path}, type={item_type}"
        )

    def log_generation_complete(self, log: GenerationLog):
        """문항 생성 완료 로깅"""
        status = "SUCCESS" if log.success else "FAILED"
        self.logger.info(
            f"[GEN_{status}] session={log.session_id}, "
            f"item_id={log.final_item_id or 'N/A'}, "
            f"duration={log.total_duration_ms}ms, "
            f"phases={len(log.phases)}"
        )

        # 상세 로그 파일 저장
        self._save_json_log(f"gen-{log.session_id}", log.model_dump(mode="json"))

    def log_validation(self, report: ValidationReport):
        """검수 결과 로깅"""
        self.logger.info(
            f"[VALIDATE] item={report.item_id}, "
            f"status={report.status.value}, "
            f"failures={[f.value for f in report.failure_codes]}"
        )

        # 상세 로그 파일 저장
        self._save_json_log(f"val-{report.item_id}", report.model_dump(mode="json"))

    def log_item_saved(self, item: ItemQuestion, filepath: Path):
        """문항 저장 로깅"""
        self.logger.info(
            f"[ITEM_SAVED] item={item.item_id}, "
            f"type={item.item_type.value}, "
            f"path={filepath}"
        )

    def log_error(self, context: str, error: Exception):
        """오류 로깅"""
        self.logger.error(f"[ERROR] {context}: {str(error)}")

    def log_info(self, message: str):
        """정보 로깅"""
        self.logger.info(message)

    def log_phase(self, session_id: str, phase: str, duration_ms: int, details: dict):
        """단계별 상세 로깅"""
        self.logger.debug(
            f"[PHASE] session={session_id}, phase={phase}, "
            f"duration={duration_ms}ms, details={json.dumps(details, ensure_ascii=False)[:200]}"
        )

    def _save_json_log(self, name: str, data: Any):
        """JSON 로그 파일 저장"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filepath = self.log_dir / f"{name}-{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def get_session_logs(self, session_id: str) -> list[Path]:
        """특정 세션의 모든 로그 파일 조회"""
        return list(self.log_dir.glob(f"*-{session_id}-*.json"))

    def get_daily_summary(self, date: Optional[str] = None) -> dict:
        """일별 요약 통계"""
        date = date or datetime.now().strftime("%Y%m%d")
        gen_logs = list(self.log_dir.glob(f"gen-*-{date}*.json"))
        val_logs = list(self.log_dir.glob(f"val-*-{date}*.json"))

        success_count = 0
        fail_count = 0
        total_duration = 0

        for log_path in gen_logs:
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                total_duration += data.get("total_duration_ms", 0)

        return {
            "date": date,
            "total_generations": len(gen_logs),
            "success_count": success_count,
            "fail_count": fail_count,
            "validation_count": len(val_logs),
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration // len(gen_logs) if gen_logs else 0
        }
