"""Pydantic schemas for IML data models."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field


class IMLItem(BaseModel):
    """Parsed IML item data model."""

    # Core identifiers
    id: str = Field(description="Item ID (from 문항 id attribute)")
    raw_path: Path = Field(description="Original IML file path")

    # Classification
    subject: str = Field(default="", description="Subject name (e.g., '수학')")
    subject_code: str = Field(default="", description="Subject code (cls4)")
    grade: str = Field(default="", description="Grade (e.g., '중2')")
    grade_code: str = Field(default="", description="Grade code (cls3)")
    school_level: str = Field(default="", description="School level (e.g., '중학교')")
    school_level_code: str = Field(default="", description="School level code (cls2)")

    # Question metadata
    question_type: str = Field(default="", description="Question type (e.g., '선택형')")
    question_type_code: str = Field(default="", description="Question type code (qt)")
    difficulty: str = Field(default="", description="Difficulty (e.g., '중')")
    difficulty_code: str = Field(default="", description="Difficulty code (df)")

    # Content
    stem: str = Field(default="", description="Question stem text (물음)")
    choices: list[str] = Field(default_factory=list, description="Answer choices (답항)")
    answer: str = Field(default="", description="Correct answer (정답)")
    explanation: str = Field(default="", description="Explanation (해설)")

    # Additional content
    hint: str = Field(default="", description="Hint (힌트)")
    direction: str = Field(default="", description="Direction (지시)")

    # Images and media
    images: list[str] = Field(
        default_factory=list, description="Image paths (DrawObjPic)"
    )
    has_images: bool = Field(default=False, description="Whether item has images")

    # Math expressions
    math_expressions: list[str] = Field(
        default_factory=list, description="Math expressions (수식)"
    )
    has_math: bool = Field(default=False, description="Whether item has math")

    # Keywords and metadata
    keywords: list[str] = Field(default_factory=list, description="Keywords (kw)")

    # Additional classification
    cls1: str = Field(default="", description="Classification 1 (교육과정)")
    cls5: str = Field(default="", description="Classification 5")
    cls6: str = Field(default="", description="Classification 6 (학기)")
    cls7: str = Field(default="", description="Classification 7 (단원)")
    cls8: str = Field(default="", description="Classification 8 (세부단원)")

    # Raw XML attributes for reference
    raw_attributes: dict[str, str] = Field(
        default_factory=dict, description="All raw XML attributes"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {Path: str}


class GroupSamplingResult(BaseModel):
    """Result of sampling for a single subject/grade group."""

    subject: str
    grade: str
    target_count: int
    actual_count: int
    items: list[IMLItem]


class SamplingReport(BaseModel):
    """Report of the entire sampling process."""

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    raw_data_dir: str
    output_dir: str
    samples_per_group: int
    require_images: bool

    # Statistics
    total_items_scanned: int = 0
    total_items_with_images: int = 0
    total_items_sampled: int = 0

    # Results by group
    groups: list[GroupSamplingResult] = Field(default_factory=list)

    # Summary by subject
    by_subject: dict[str, int] = Field(default_factory=dict)

    # Summary by grade
    by_grade: dict[str, int] = Field(default_factory=dict)

    # Items that couldn't be parsed
    parse_errors: list[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), Path: str}
