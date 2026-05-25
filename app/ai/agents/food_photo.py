"""FoodPhotoAnalyzerAgent — Vision-based food detection from photos.

Uses OpenRouter vision models (gpt-4o-mini) to detect foods in images
and estimate nutritional content from visual analysis.
"""

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.ai.base import BaseAgent

logger = logging.getLogger(__name__)


class FoodPhotoAnalysis(BaseModel):
    """Structured analysis result from a food photo."""

    detected_foods: list[str] = Field(
        ..., description="Names of detected foods in the image"
    )
    estimated_carbs_g: float = Field(
        ..., ge=0, description="Total estimated carbohydrate content in grams"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the analysis"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Preparation, portion, or serving suggestions",
    )
    disclaimer: str = Field(
        default="This is an AI estimate based on visual analysis. "
        "Actual nutritional values may vary.",
        description="Safety disclaimer",
    )


class FoodPhotoAnalyzerAgent(BaseAgent):
    """Agent that analyzes food photos and estimates nutritional content.

    Uses OpenRouter vision models to detect foods, estimate portion sizes,
    and return structured nutritional analysis.
    """

    SYSTEM_PROMPT = """You are a food analysis AI. Given a photo of a meal or food item:
1. Identify all visible foods/drinks
2. Estimate the total carbohydrate content in grams based on visual portion size
3. Rate your confidence (0.0-1.0) based on how clearly the food is visible
4. Suggest serving or preparation notes (e.g., "appears to be grilled", "large portion")

Rules:
- Be honest about uncertainty — low confidence is better than guessing
- Consider common portion sizes when estimating carbs
- Note if the image quality is poor or the food is partially obscured
- Return the analysis as a valid JSON object matching this schema:
  {
    "detected_foods": ["food1", "food2"],
    "estimated_carbs_g": 45.0,
    "confidence": 0.85,
    "suggestions": ["Suggestion 1", "Suggestion 2"]
  }

Always include the disclaimer field: "This is an AI estimate based on visual analysis. Actual nutritional values may vary." """

    VISION_MODEL = "openai/gpt-4o-mini"
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, name: str = "food_photo_analyzer") -> None:
        """Initialize the food photo analyzer agent.

        Args:
            api_key: OpenRouter API key (or any OpenAI-compatible key).
            name: Agent name for logging.
        """
        super().__init__(name)
        self.api_key = api_key

    async def analyze(self, base64_image: str) -> FoodPhotoAnalysis:
        """Analyze a food photo from a base64-encoded image.

        Args:
            base64_image: Base64-encoded JPEG/PNG image data (without data: URI prefix).

        Returns:
            FoodPhotoAnalysis with detected foods and nutritional estimates.
        """
        # Ensure image has the data URI prefix if not already present
        image_data = base64_image
        if not base64_image.startswith("data:"):
            image_data = f"data:image/jpeg;base64,{base64_image}"

        messages = [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this food photo and estimate the nutritional content."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            },
        ]

        payload = {
            "model": self.VISION_MODEL,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ruskibeats/t1d",
        }

        last_error: Exception | None = None
        for attempt in range(2):  # max 1 retry
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.OPENROUTER_URL,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "{}")
                )

                # Parse JSON from the response
                parsed = json.loads(content)

                # Ensure disclaimer is present
                if "disclaimer" not in parsed:
                    parsed["disclaimer"] = (
                        "This is an AI estimate based on visual analysis. "
                        "Actual nutritional values may vary."
                    )

                return FoodPhotoAnalysis(**parsed)

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning("OpenRouter vision request failed (attempt %d): %s", attempt + 1, e)
                last_error = e
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning("Failed to parse vision response (attempt %d): %s", attempt + 1, e)
                last_error = e

        # Return a safe fallback on failure
        logger.error("Food photo analysis failed after retries: %s", last_error)
        return FoodPhotoAnalysis(
            detected_foods=[],
            estimated_carbs_g=0.0,
            confidence=0.0,
            suggestions=["Unable to analyze the image. Please try again with a clearer photo."],
        )

    async def handle(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle an agent task to analyze a food photo.

        Expected data keys:
            - image: str (base64 encoded image)
            - api_key: str (optional, overrides instance key)

        Returns:
            Dict with 'analysis' key containing FoodPhotoAnalysis dict.
        """
        base64_image = data.get("image", "")
        if not base64_image:
            return {"error": "No image provided", "analysis": None}

        if "api_key" in data:
            self.api_key = data["api_key"]

        analysis = await self.analyze(base64_image)
        return {"analysis": analysis.model_dump()}
