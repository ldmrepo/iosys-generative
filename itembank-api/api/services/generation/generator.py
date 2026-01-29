"""
LLM-based Similar Question Generator
"""

import json
import uuid
import time
from typing import Optional
from datetime import datetime

from openai import AsyncOpenAI

from ...core.config import get_settings
from .prompts import PromptBuilder, GenerationRequest


class GenerationService:
    """Service for generating similar questions using LLM"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.prompt_builder = PromptBuilder()
        self._settings = get_settings()
        self.model = self._settings.openai_model or "gpt-4o"

    def _ensure_client(self):
        """Ensure OpenAI client is initialized"""
        if self.client is None:
            if not self._settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.client = AsyncOpenAI(api_key=self._settings.openai_api_key)

    async def generate(
        self,
        source_item: dict,
        count: int = 3,
        variation_type: str = "mixed",
        additional_prompt: str = ""
    ) -> dict:
        """
        Generate similar questions based on source item

        Args:
            source_item: Source item dictionary with question details
            count: Number of questions to generate (1-6)
            variation_type: Type of variation (numeric/context/structure/mixed/auto)
            additional_prompt: Additional instructions for generation

        Returns:
            dict with generated_items list and metadata
        """
        self._ensure_client()

        start_time = time.time()

        # Build request
        request = GenerationRequest(
            source_item=source_item,
            count=min(max(count, 1), 6),  # Clamp to 1-6
            variation_type=variation_type,
            additional_prompt=additional_prompt
        )

        # Build prompts
        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(request)

        # Call LLM
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4000
            )

            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Process generated items
            generated_items = []
            for idx, item in enumerate(result.get("items", [])):
                generated_item = self._process_generated_item(
                    item=item,
                    index=idx,
                    source_item_id=source_item.get("id") or source_item.get("item_id"),
                    variation_type=variation_type
                )
                generated_items.append(generated_item)

            generation_time_ms = (time.time() - start_time) * 1000

            return {
                "generated_items": generated_items,
                "generation_time_ms": round(generation_time_ms, 2),
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else None
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
        variation_type: str
    ) -> dict:
        """Process and enrich a single generated item"""

        # Generate temp ID
        temp_id = f"gen_{int(time.time())}_{index}_{uuid.uuid4().hex[:8]}"

        # Normalize choices
        choices = item.get("choices", [])
        if isinstance(choices, str):
            choices = [choices] if choices else []

        return {
            "temp_id": temp_id,
            "question_text": item.get("question", ""),
            "choices": choices,
            "answer_text": item.get("answer", ""),
            "explanation_text": item.get("explanation", ""),
            "variation_note": item.get("variation_note", ""),
            "uses_original_image": item.get("uses_original_image", False),
            "metadata": {
                "source_item_id": source_item_id,
                "variation_type": variation_type,
                "is_ai_generated": True,
                "generation_model": self.model,
                "generation_timestamp": datetime.utcnow().isoformat() + "Z",
                "confidence_score": 0.85  # Placeholder, can be improved
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
