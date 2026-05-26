"""Declarative pipeline stage graph.

Stages declare their dependencies (needs_llm, needs_interactive).
PipelineRunner executes them in order, injecting dependencies and
handling the clarification loop as a first-class stage wrapper.

Usage:
    runner = PipelineRunner(llm=llm, interactive=True)
    state = await runner.run("jacket potato with beans")
    print(state.response)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from sim_user_insights.scripts.companion_pipeline_v2 import (
    CompanionState,
    stage_select_profile,
    stage_parse_foods,
    stage_db_lookup,
    stage_decide_clarification,
    stage_apply_clarification,
    stage_forecast,
    stage_historical_context,
    stage_companion_advice,
)

logger = logging.getLogger(__name__)

StageFunc = Callable[..., Any]  # sync or async stage function


@dataclass
class Stage:
    """A pipeline stage declaration.

    Attributes:
        name: Human-readable stage name for logging/debugging
        func: The stage function (sync or async)
        needs_llm: If True, receives the LLMCapture as second arg
        needs_interactive: If True, receives interactive bool as kwarg
    """
    name: str
    func: StageFunc
    needs_llm: bool = False
    needs_interactive: bool = False


@dataclass
class PipelineResult:
    """Result of running the pipeline, including any clarification request."""
    state: CompanionState
    clarification_needed: bool = False
    clarification_prompt: str | None = None
    completed: bool = True  # False if stopped for clarification


class PipelineRunner:
    """Executes a declarative stage graph with dependency injection.

    Stages are defined as data, not hardcoded call sequences.
    The clarification loop is handled by a stage wrapper, not inline if/else.
    """

    def __init__(
        self,
        llm: Any = None,
        interactive: bool = False,
        verbose: bool = False,
        stages: list[Stage] | None = None,
    ):
        self._llm = llm
        self._interactive = interactive
        self._verbose = verbose
        self._stages = stages or self._default_stages()

    @staticmethod
    def _default_stages() -> list[Stage]:
        """The standard companion pipeline stage graph."""
        return [
            Stage("select_profile", stage_select_profile),
            Stage("parse_foods", stage_parse_foods, needs_llm=True),
            Stage("db_lookup", stage_db_lookup),
            Stage("decide_clarification", stage_decide_clarification),
            Stage("forecast", stage_forecast),
            Stage("historical_context", stage_historical_context),
            Stage("companion_advice", stage_companion_advice, needs_llm=True),
        ]

    async def run(
        self,
        scenario: str,
        anchor_type: str | None = None,
        question_mode: str = "forecast",
        clarification_answer: str | None = None,
    ) -> PipelineResult:
        """Run the pipeline for a scenario.

        Handles the clarification loop: if a stage signals that clarification
        is needed and we're in interactive mode, returns early with the prompt.
        Otherwise continues through all stages.

        Args:
            scenario: Natural language meal description
            anchor_type: Optional anchor profile override
            question_mode: "forecast", "action", or "compare"
            clarification_answer: Pre-supplied answer (for resumed runs)

        Returns:
            PipelineResult with final state and clarification info
        """
        state = CompanionState(
            scenario=scenario,
            anchor_type=anchor_type,
            question_mode=question_mode,
            clarification_answer=clarification_answer,
        )

        # Pre-supplied clarification answer: apply before running
        if clarification_answer:
            state = stage_apply_clarification(state)

        for stage in self._stages:
            logger.debug(f"Running stage: {stage.name}")

            # Build kwargs based on declared dependencies
            kwargs: dict[str, Any] = {}
            if stage.needs_llm and self._llm:
                kwargs["llm_call"] = self._llm
            if stage.needs_interactive:
                kwargs["interactive"] = self._interactive

            # Execute stage (sync or async)
            result = stage.func(state, **kwargs)
            if hasattr(result, "__await__"):
                result = await result
            state = result

            # Verbose output
            if self._verbose:
                self._print_verbose(stage.name, state)

            # Check if clarification was requested by decide_clarification
            if (
                stage.name == "decide_clarification"
                and state.clarification_needed
                and state.clarification_prompt
            ):
                if self._interactive:
                    # Return early — caller will ask user and resume
                    return PipelineResult(
                        state=state,
                        clarification_needed=True,
                        clarification_prompt=state.clarification_prompt,
                        completed=False,
                    )
                # Non-interactive: log and continue
                logger.info(
                    f"Clarification needed but not in interactive mode: "
                    f"{state.clarification_prompt}"
                )

        return PipelineResult(state=state, completed=True)

    def _print_verbose(self, stage_name: str, state: CompanionState) -> None:
        """Print verbose stage output (matches old pipeline format)."""
        if stage_name == "select_profile":
            print(f"\n[STAGE 1] Profile Selection")
            print("-" * 50)
            print(f"  Output: anchor_type={state.anchor_type}")
            if state.profile_json:
                print(f"  Profile label: {state.profile_json.get('anchor_label')}")
            if state.sim_reading:
                print(f"  CGM: {state.sim_reading.get('cgm_displayed_mg_dl')} mg/dL")
                print(f"  Trend: {state.sim_reading.get('trend')}")
                print(f"  IOB: {state.sim_reading.get('insulin_on_board_units')}u")
        elif stage_name == "parse_foods":
            print(f"\n[STAGE 2] Food Parsing")
            print("-" * 50)
            print(f"  Foods parsed: {len(state.foods)}")
            for i, f in enumerate(state.foods):
                d = f if isinstance(f, dict) else {"item": f.item, "quantity": f.quantity, "unit": f.unit}
                print(f"  Food [{i}]: {d}")
        elif stage_name == "db_lookup":
            print(f"\n[STAGE 3] Database Lookup")
            print("-" * 50)
            print(f"  Totals: {state.totals}")
            print(f"  Carb range: {state.total_carbs_g_range}")
            print(f"  Confidence: {state.confidence_overall}")
            print(f"  Evidence items: {len(state.evidence_items)}")
            for i, e in enumerate(state.evidence_items[:3]):
                m = e.get("selected_match", {}) or {}
                c = e.get("computed", {}) or {}
                print(f"  Evidence [{i}]: {m.get('name','?')} | carbs: {c.get('carbs_g','?')}g | conf: {e.get('confidence','?')}")
        elif stage_name == "decide_clarification":
            if state.clarification_needed:
                print(f"\n[CLARIFICATION] {state.clarification_prompt}")
        elif stage_name == "forecast":
            if state.forecast:
                print(f"\n[STAGE 4] Forecast")
                print("-" * 50)
                fc = state.forecast
                print(f"  Baseline: {fc.baseline_mg_dl} mg/dL")
                print(f"  Peak: {fc.peak_mg_dl} mg/dL at {fc.peak_time_minutes} min")
                if fc.forecast_points:
                    print(f"  Forecast points: {len(fc.forecast_points)} timepoints")
        elif stage_name == "historical_context":
            if state.historical_timeline:
                print(f"\n[STAGE 5] Historical Context")
                print("-" * 50)
                print(f"  Similar meals found: {len(state.similar_meals)}")
                if state.historical_summary:
                    hs = state.historical_summary
                    print(f"  Avg peak delta: {hs.get('avg_peak_delta_mgdl')} mg/dL")
                    print(f"  Avg peak time: {hs.get('avg_peak_time_minutes')} min")
        elif stage_name == "companion_advice":
            print(f"\n[STAGE 6] Companion Advice")
            print("-" * 50)
            print(f"  Response length: {len(state.response)} chars")

    async def resume_after_clarification(
        self,
        state: CompanionState,
        answer: str,
    ) -> PipelineResult:
        """Resume the pipeline after receiving a clarification answer.

        Re-runs db_lookup with the updated quantity, then continues
        through forecast and companion_advice.
        """
        state.clarification_answer = answer
        state = stage_apply_clarification(state)

        # Re-run db_lookup with updated quantity
        state = await stage_db_lookup(state)

        # Continue with remaining stages
        remaining = [
            s for s in self._stages
            if s.name in ("forecast", "historical_context", "companion_advice")
        ]
        for stage in remaining:
            kwargs: dict[str, Any] = {}
            if stage.needs_llm and self._llm:
                kwargs["llm_call"] = self._llm
            result = stage.func(state, **kwargs)
            if hasattr(result, "__await__"):
                result = await result
            state = result

        return PipelineResult(state=state, completed=True)
