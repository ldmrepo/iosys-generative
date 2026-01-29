"""
LLM-based Similar Question Generator with Vision Support
"""

import base64
import json
import uuid
import time
import logging
import os
from pathlib import Path
from typing import Optional, List

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ...core.config import get_settings
from .prompts import PromptBuilder, GenerationRequest

logger = logging.getLogger(__name__)


# Pydantic models for structured outputs
class GeneratedItem(BaseModel):
    """Single generated item structure"""
    question: str = Field(description="Question text with LaTeX math in $...$ format")
    choices: List[str] = Field(description="5 choices for multiple choice, empty for short answer")
    correct_choice: int = Field(description="Correct answer index 1-5 for MC, 0 for short answer")
    explanation: str = Field(description="Explanation with LaTeX math in $...$ format")
    variation_note: str = Field(description="Summary of changes from original")

    class Config:
        extra = "forbid"  # This adds additionalProperties: false


class GenerationResponse(BaseModel):
    """Response structure for generation"""
    items: List[GeneratedItem] = Field(description="List of generated items")

    class Config:
        extra = "forbid"  # This adds additionalProperties: false


class GenerationService:
    """Service for generating similar questions using LLM with Vision support"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.prompt_builder = PromptBuilder()
        self._settings = get_settings()
        self.model = self._settings.openai_model or "gpt-4o"
        self.model_text_only = self._settings.openai_model_text_only or "gpt-4o-mini"

    def _ensure_client(self):
        """Ensure OpenAI client is initialized"""
        if self.client is None:
            if not self._settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.client = AsyncOpenAI(api_key=self._settings.openai_api_key)

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string"""
        try:
            # Handle relative paths
            if not os.path.isabs(image_path):
                image_path = os.path.join(self._settings.iml_data_path, image_path)

            if not os.path.exists(image_path):
                logger.warning(f"Image not found: {image_path}")
                return None

            with open(image_path, "rb") as image_file:
                return base64.standard_b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None

    def _extract_json(self, content: str) -> dict:
        """Extract and parse JSON from LLM response with fallback handling"""
        import re

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find JSON object pattern
        json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Last resort: try to fix common issues
        cleaned = content.strip()
        # Remove leading/trailing non-JSON text
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        if start_idx != -1 and end_idx != -1:
            cleaned = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                logger.error(f"JSON extraction failed. Content preview: {cleaned[:500]}...")
                raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        raise ValueError("No valid JSON found in LLM response")

    def _get_image_media_type(self, image_path: str) -> str:
        """Get media type from image file extension"""
        ext = Path(image_path).suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return media_types.get(ext, "image/jpeg")

    def _resolve_image_paths(self, source_item: dict) -> List[str]:
        """Resolve image paths from source item"""
        image_paths = []
        base_dir = Path(self._settings.iml_data_path)

        # Helper to resolve relative paths
        def resolve_path(img_path: str) -> str:
            if os.path.isabs(img_path):
                return img_path
            # Try multiple base directories
            candidates = [
                base_dir / img_path,
                base_dir / "data" / "raw" / img_path,
            ]
            # Also try using source_file's directory as base
            source_file = source_item.get("source_file", "")
            if source_file:
                source_dir = Path(source_file).parent
                candidates.append(base_dir / source_dir / img_path)

            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
            # Return with base_dir as fallback
            return str(base_dir / img_path)

        # Check question_images field
        question_images = source_item.get("question_images")
        if question_images:
            if isinstance(question_images, str):
                # Could be JSON string or single path
                try:
                    images = json.loads(question_images)
                    if isinstance(images, list):
                        image_paths.extend([resolve_path(img) for img in images])
                    else:
                        image_paths.append(resolve_path(str(images)))
                except json.JSONDecodeError:
                    image_paths.append(resolve_path(question_images))
            elif isinstance(question_images, list):
                image_paths.extend([resolve_path(img) for img in question_images])

        # Check metadata for additional images
        metadata = source_item.get("metadata", {})
        if isinstance(metadata, dict):
            meta_images = metadata.get("images", [])
            if isinstance(meta_images, list):
                image_paths.extend([resolve_path(img) for img in meta_images])

        # If no images found from question_images, scan source_file directory
        if not image_paths:
            source_file = source_item.get("source_file", "")
            if source_file:
                # Look for DrawObjPic folder (common IML structure)
                draw_obj_pic_dir = base_dir / source_file.replace(".iml", "") / "DrawObjPic"
                if draw_obj_pic_dir.exists():
                    for img in os.listdir(draw_obj_pic_dir):
                        if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            image_paths.append(str(draw_obj_pic_dir / img))

        # Remove duplicates and filter to only existing files
        unique_paths = []
        seen = set()
        for p in image_paths:
            normalized = os.path.normpath(p)
            if normalized not in seen and os.path.exists(normalized):
                seen.add(normalized)
                unique_paths.append(normalized)

        return unique_paths

    def _build_vision_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str]
    ) -> List[dict]:
        """Build messages array with images for Vision API"""
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Build user content with text and images
        user_content = []

        # Add text first
        user_content.append({
            "type": "text",
            "text": user_prompt
        })

        # Add images
        for image_path in image_paths:
            base64_image = self._encode_image_to_base64(image_path)
            if base64_image:
                media_type = self._get_image_media_type(image_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_image}",
                        "detail": "high"  # Use high detail for math/diagrams
                    }
                })
                logger.info(f"Added image to Vision request: {image_path}")

        messages.append({"role": "user", "content": user_content})

        return messages

    async def generate(
        self,
        source_item: dict,
        count: int = 3,
        variation_type: str = "mixed",
        additional_prompt: str = "",
        image_paths: Optional[List[str]] = None
    ) -> dict:
        """
        Generate similar questions based on source item

        Args:
            source_item: Source item dictionary with question details
            count: Number of questions to generate (1-6)
            variation_type: Type of variation (numeric/context/structure/mixed/auto)
            additional_prompt: Additional instructions for generation
            image_paths: Optional list of image paths to include

        Returns:
            dict with generated_items list and metadata
        """
        self._ensure_client()

        start_time = time.time()

        # Resolve image paths if not provided
        if image_paths is None and source_item.get("has_image"):
            image_paths = self._resolve_image_paths(source_item)

        has_images = bool(image_paths)

        # Build request
        request = GenerationRequest(
            source_item=source_item,
            count=min(max(count, 1), 6),  # Clamp to 1-6
            variation_type=variation_type,
            additional_prompt=additional_prompt,
            has_images=has_images
        )

        # Build prompts
        system_prompt = self.prompt_builder.get_system_prompt(has_images=has_images)
        user_prompt = self.prompt_builder.build_user_prompt(request)

        # Select model based on whether images are present
        model = self.model if has_images else self.model_text_only

        # Call LLM
        try:
            if has_images and image_paths:
                # Use Vision API with images
                messages = self._build_vision_messages(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    image_paths=image_paths
                )
                logger.info(f"Calling Vision API with {len(image_paths)} images")
            else:
                # Text-only request
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                logger.info("Calling API without images (text-only)")

            # Use structured outputs with inline JSON schema (OpenAI doesn't support $ref)
            json_schema = {
                "name": "generation_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "choices": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "correct_choice": {"type": "integer"},
                                    "explanation": {"type": "string"},
                                    "variation_note": {"type": "string"}
                                },
                                "required": ["question", "choices", "correct_choice", "explanation", "variation_note"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["items"],
                    "additionalProperties": False
                }
            }
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": json_schema},
                temperature=0.7,
                max_tokens=4000
            )

            # Parse response - should always be valid JSON with strict mode
            content = response.choices[0].message.content
            result = json.loads(content)

            # Process generated items
            generated_items = []
            for idx, item in enumerate(result.get("items", [])):
                generated_item = self._process_generated_item(
                    item=item,
                    index=idx,
                    source_item_id=source_item.get("id") or source_item.get("item_id"),
                    variation_type=variation_type,
                    has_images=has_images
                )
                generated_items.append(generated_item)

            generation_time_ms = (time.time() - start_time) * 1000

            return {
                "generated_items": generated_items,
                "generation_time_ms": round(generation_time_ms, 2),
                "model": model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "images_used": len(image_paths) if image_paths else 0
            }

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Generation failed: {e}")

    def _process_generated_item(
        self,
        item: dict,
        index: int,
        source_item_id: str,
        variation_type: str,
        has_images: bool = False
    ) -> dict:
        """Process and enrich a single generated item, converting to QTI format"""
        from datetime import datetime

        # Generate temp ID
        temp_id = f"gen_{int(time.time())}_{index}_{uuid.uuid4().hex[:8]}"

        # Extract from simplified format (question, choices, correct_choice, explanation)
        question_text = item.get("question", "")
        choices = item.get("choices", [])
        correct_choice = item.get("correct_choice", 0)  # 1-based index
        explanation = item.get("explanation", "")

        # Convert $...$ math to HTML with data-latex for rendering
        def convert_math_to_html(text: str) -> str:
            """Convert $...$ LaTeX to <span class='math' data-latex='...'>"""
            import re
            # Match $...$ but not $$...$$
            pattern = r'\$([^$]+)\$'
            def replacer(match):
                latex = match.group(1)
                return f'<span class="math" data-latex="{latex}"></span>'
            return re.sub(pattern, replacer, text)

        # Build choice interactions for QTI
        choice_interactions = []
        correct_response_value = None

        if choices:
            simple_choices = []
            for i, choice in enumerate(choices):
                choice_id = f"choice_{i + 1}"
                choice_html = convert_math_to_html(str(choice))
                simple_choices.append({
                    "identifier": choice_id,
                    "content": choice_html
                })
                # correct_choice is 1-based
                if i + 1 == correct_choice:
                    correct_response_value = choice_id

            choice_interactions.append({
                "type": "choiceInteraction",
                "responseIdentifier": "RESPONSE",
                "shuffle": False,
                "maxChoices": 1,
                "simpleChoices": simple_choices
            })

        # Build QTI AssessmentItem
        assessment_item = {
            "identifier": temp_id,
            "title": "",
            "responseDeclarations": [
                {
                    "identifier": "RESPONSE",
                    "cardinality": "single",
                    "baseType": "identifier",
                    "correctResponse": {
                        "values": [correct_response_value] if correct_response_value else []
                    }
                }
            ],
            "outcomeDeclarations": [
                {
                    "identifier": "SCORE",
                    "cardinality": "single",
                    "baseType": "float",
                    "defaultValue": 0
                }
            ],
            "itemBody": {
                "content": convert_math_to_html(question_text),
                "interactions": choice_interactions,
                "feedbackBlocks": [
                    {
                        "outcomeIdentifier": "SCORE",
                        "identifier": "explanation",
                        "showHide": "show",
                        "content": convert_math_to_html(explanation)
                    }
                ] if explanation else None
            }
        }

        return {
            "temp_id": temp_id,
            "assessment_item": assessment_item,
            "variation_note": item.get("variation_note", ""),
            "metadata": {
                "source_item_id": source_item_id,
                "variation_type": variation_type,
                "is_ai_generated": True,
                "generation_model": self.model if has_images else self.model_text_only,
                "generation_timestamp": datetime.utcnow().isoformat() + "Z",
                "confidence_score": 0.85,
                "used_vision_api": has_images
            }
        }

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self._settings.openai_api_key)


# Singleton instance
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """Get or create generation service singleton"""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
