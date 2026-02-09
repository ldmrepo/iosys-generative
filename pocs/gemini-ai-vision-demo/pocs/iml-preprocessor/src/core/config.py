"""Configuration settings for IML Preprocessor."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Directories
    raw_data_dir: Path = Field(
        default=Path("../../../../data/raw"),
        description="Raw IML data directory",
    )
    sample_output_dir: Path = Field(
        default=Path("../../../../data/sample"),
        description="Sample output directory",
    )

    # Sampling settings
    samples_per_group: int = Field(
        default=30,
        description="Number of samples per subject/grade group",
    )
    require_images: bool = Field(
        default=True,
        description="Only sample items with images",
    )

    # Subject code mappings (cls4 attribute)
    SUBJECT_CODES: ClassVar[dict[str, str]] = {
        "01": "국어",
        "02": "영어",
        "03": "수학",
        "04": "사회",
        "05": "과학",
        "06": "역사",
    }

    # Reverse mapping for lookup
    SUBJECT_NAMES: ClassVar[dict[str, str]] = {v: k for k, v in SUBJECT_CODES.items()}

    # School level codes (cls2 attribute)
    SCHOOL_LEVEL_CODES: ClassVar[dict[str, str]] = {
        "01": "초등학교",
        "02": "중학교",
        "03": "고등학교",
    }

    # Grade codes (cls3 attribute) - format varies by school level
    # For elementary: "01 1학년" to "06 6학년"
    # For middle school: "07 1학년" to "09 3학년" OR "01 1학년" to "03 3학년"
    GRADE_CODES_ELEMENTARY: ClassVar[dict[str, str]] = {
        "01": "초1",
        "02": "초2",
        "03": "초3",
        "04": "초4",
        "05": "초5",
        "06": "초6",
    }

    GRADE_CODES_MIDDLE: ClassVar[dict[str, str]] = {
        "07": "중1",
        "08": "중2",
        "09": "중3",
        # Alternative coding
        "01": "중1",
        "02": "중2",
        "03": "중3",
    }

    GRADE_CODES_HIGH: ClassVar[dict[str, str]] = {
        "10": "고1",
        "11": "고2",
        "12": "고3",
        # Alternative coding
        "01": "고1",
        "02": "고2",
        "03": "고3",
    }

    # Question type codes (qt attribute)
    QUESTION_TYPE_CODES: ClassVar[dict[str, str]] = {
        "11": "선택형",
        "21": "진위형",
        "31": "단답형",
        "34": "완성형",
        "37": "배합형",
        "41": "서술형",
        "51": "논술형",
    }

    # Difficulty codes (df attribute)
    DIFFICULTY_CODES: ClassVar[dict[str, str]] = {
        "01": "상",
        "02": "중상",
        "03": "중",
        "04": "중하",
        "05": "하",
    }

    # Target subjects and grades for sampling
    TARGET_SUBJECTS: ClassVar[list[str]] = ["수학", "과학", "국어", "영어", "사회", "역사"]
    TARGET_GRADES: ClassVar[list[str]] = [
        "초1",
        "초2",
        "초3",
        "초4",
        "초5",
        "초6",
        "중1",
        "중2",
        "중3",
    ]


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
