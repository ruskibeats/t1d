"""AI-driven insights engine for proactive pattern recognition.

This service uses the LLM to analyze glucose data, detect patterns,
and generate human-readable, safety-compliant insights.

The AI reads raw data and generates natural language insights like:
- "I've noticed your glucose tends to spike around 7pm on weekdays"
- "After eating pizza, your glucose typically peaks at 240 mg/dL"
- "Your overnight glucose has been stable for the past week"

All insights include medical disclaimers and never suggest specific
insulin doses.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEvent, GlucoseReading, User
from app.services.llm_service import LLMService


logger = logging.getLogger(__name__)

# Safety system prompt for insight generation
INSIGHT_SYSTEM_PROMPT = """You are a diabetes data analyst helping a person with Type 1 diabetes
understand their glucose patterns. Your role is to:

1. Analyze glucose data and identify meaningful patterns
2. Explain patterns in clear, supportive language
3. Suggest areas to discuss with their healthcare team

CRITICAL SAFETY RULES:
- NEVER suggest specific insulin doses or unit amounts
- NEVER tell the user to change their medication
- ALWAYS recommend discussing patterns with their healthcare team
- Use phrases like "you may want to discuss with your doctor" or
  "your care team might suggest"
- Be supportive and non-judgmental
- Acknowledge that diabetes management is complex and individual

Format your response as JSON with the following structure:
{
  "insights": [
    {
      "type": "time_of_day_spike" | "time_of_day_low" | "meal_spike" | "trend" | "positive",
      "severity": "low" | "moderate" | "high",
      "title": "Short, clear title (max 60 chars)",
      "description": "Human-readable description of the pattern (1-2 sentences)",
      "recommendation": "What to discuss with their care team (1 sentence)",
      "confidence": 0.0-1.0
    }
  ],
  "summary": "A brief 1-2 sentence overall summary of the user's glucose patterns"
}"""

PRE_MEAL_SYSTEM_PROMPT = """You are a diabetes coach helping a person with Type 1 diabetes
prepare for a meal. Based on their historical data for this specific food,
provide a helpful prediction and tips.

CRITICAL SAFETY RULES:
- NEVER suggest specific insulin doses or unit amounts
- NEVER tell the user exactly how much insulin to take
- ALWAYS recommend discussing dosing with their healthcare team
- Focus on patterns and timing, not doses
- Be supportive and practical

Format your response as JSON:
{
  "prediction": "Based on your history with [food], your glucose typically peaks around X mg/dL about Y minutes after eating",
  "tips": ["Tip 1", "Tip 2"],
  "current_context": "Comment on current glucose if provided",
  "disclaimer": "This is not medical advice. Always consult your healthcare provider for dosing decisions."
}"""


class InsightsService:
    """AI-driven insights generation service.

    Uses the LLM to analyze glucose data and generate personalized,
    safety-compliant insights and recommendations.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.InsightsService")
        self.llm = LLMService()

    async def generate_insights(
        self,
        session: AsyncSession,
        user_id: int,
        lookback_days: int = 14,
    ) -> Dict[str, Any]:
        """Generate AI-driven insights from glucose data.

        Fetches recent glucose readings and events, sends them to the
        LLM for analysis, and returns structured insights.

        Args:
            session: Database session
            user_id: User ID
            lookback_days: Days of historical data to analyze

        Returns:
            Dict with insights array and summary
        """
        # Fetch glucose readings
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days)

        glucose_result = await session.execute(
            select(GlucoseReading)
            .where(
                GlucoseReading.user_id == user_id,
                GlucoseReading.timestamp >= start_date,
                GlucoseReading.timestamp <= end_date,
            )
            .order_by(GlucoseReading.timestamp.desc())
            .limit(500)
        )
        readings = glucose_result.scalars().all()

        if not readings:
            return {
                "insights": [],
                "summary": "Not enough glucose data yet. Keep logging to see personalized insights.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Fetch meal events
        events_result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "meal",
                ContextEvent.timestamp >= start_date,
                ContextEvent.timestamp <= end_date,
            )
            .order_by(ContextEvent.timestamp.desc())
            .limit(100)
        )
        meals = events_result.scalars().all()

        # Prepare data for LLM
        glucose_data = []
        for r in readings:
            glucose_data.append({
                "timestamp": r.timestamp.isoformat(),
                "value": r.glucose_value,
                "source": r.source,
                "trend": r.trend,
            })

        meal_data = []
        for m in meals:
            meal_data.append({
                "timestamp": m.timestamp.isoformat(),
                "description": m.description,
                "carbs": m.carbs_grams,
            })

        # Build user prompt
        user_prompt = f"""Analyze the following glucose data and generate insights.

GLUCOSE READINGS (last {lookback_days} days, {len(readings)} readings):
{json.dumps(glucose_data[:100], indent=2)}

MEAL EVENTS ({len(meals)} meals logged):
{json.dumps(meal_data[:30], indent=2)}

STATISTICS:
- Average glucose: {sum(r.glucose_value for r in readings) / len(readings):.0f} mg/dL
- Min: {min(r.glucose_value for r in readings):.0f} mg/dL
- Max: {max(r.glucose_value for r in readings):.0f} mg/dL
- Readings above 180: {sum(1 for r in readings if r.glucose_value > 180)}
- Readings below 70: {sum(1 for r in readings if r.glucose_value < 70)}

Generate insights as JSON."""

        try:
            response = await self.llm.generate_response(
                message=user_prompt,
                system_prompt=INSIGHT_SYSTEM_PROMPT,
                session=session,
                user_id=user_id,
            )

            # Parse JSON from response
            result = json.loads(response)
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            return result

        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse LLM insight response: {response[:200]}")
            return {
                "insights": [],
                "summary": "Unable to generate insights at this time.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Insight generation failed: {e}")
            return {
                "insights": [],
                "summary": "Unable to generate insights at this time.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    async def predict_meal(
        self,
        session: AsyncSession,
        user_id: int,
        food_name: str,
        current_glucose: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate a pre-meal prediction using AI.

        Analyzes historical data for a specific food and generates
        a personalized prediction for the upcoming meal.

        Args:
            session: Database session
            user_id: User ID
            food_name: Name of the food
            current_glucose: Current glucose reading (optional)

        Returns:
            Prediction dict or None if insufficient data
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=60)

        # Find past meals with this food
        meals_result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "meal",
                ContextEvent.timestamp >= start_date,
                ContextEvent.description.ilike(f"%{food_name}%"),
            )
            .order_by(ContextEvent.timestamp.desc())
            .limit(20)
        )
        meals = meals_result.scalars().all()

        if len(meals) < 2:
            return None

        # Get glucose outcomes for each meal
        meal_outcomes = []
        for meal in meals:
            peak_result = await session.execute(
                select(GlucoseReading)
                .where(
                    GlucoseReading.user_id == user_id,
                    GlucoseReading.timestamp >= meal.timestamp,
                    GlucoseReading.timestamp <= meal.timestamp + timedelta(hours=3),
                )
                .order_by(GlucoseReading.glucose_value.desc())
                .limit(1)
            )
            peak = peak_result.scalar_one_or_none()
            if peak:
                time_to_peak = (peak.timestamp - meal.timestamp).total_seconds() / 60
                meal_outcomes.append({
                    "meal_time": meal.timestamp.isoformat(),
                    "description": meal.description,
                    "carbs": meal.carbs_grams,
                    "peak_glucose": peak.glucose_value,
                    "time_to_peak_min": round(time_to_peak, 0),
                })

        if len(meal_outcomes) < 2:
            return None

        # Build prompt
        current_ctx = ""
        if current_glucose:
            current_ctx = f"\nCURRENT GLUCOSE: {current_glucose} mg/dL"

        user_prompt = f"""Predict the glucose outcome for this meal.

FOOD: {food_name}
NUMBER OF PAST MEALS WITH THIS FOOD: {len(meal_outcomes)}
{current_ctx}

HISTORICAL OUTCOMES:
{json.dumps(meal_outcomes, indent=2)}

Provide a prediction as JSON."""

        try:
            response = await self.llm.generate_response(
                message=user_prompt,
                system_prompt=PRE_MEAL_SYSTEM_PROMPT,
                session=session,
                user_id=user_id,
            )

            result = json.loads(response)
            result["food_name"] = food_name
            result["based_on_meals"] = len(meal_outcomes)
            return result

        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Meal prediction failed: {e}")
            return None