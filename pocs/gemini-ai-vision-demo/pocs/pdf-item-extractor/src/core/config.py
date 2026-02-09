"""설정 관리"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 키
    google_api_key: str = Field(default="", description="Google API Key")

    # 모델 설정
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini Flash 모델 (Agentic Vision)"
    )

    # PDF 처리 설정
    pdf_dpi: int = Field(default=200, description="PDF 렌더링 DPI")

    # 출력 설정
    output_dir: Path = Field(
        default=Path(__file__).parent.parent.parent / "output",
        description="출력 디렉토리"
    )

    # 프롬프트 설정
    prompts_dir: Path = Field(
        default=Path(__file__).parent.parent.parent / "prompts",
        description="프롬프트 디렉토리"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
