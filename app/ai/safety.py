"""AI safety and guardrail module for T1D Companion.

Provides condition-specific safety guardrails, emergency keyword detection,
and content validation for all AI-generated responses.
"""

import logging
import re
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SafetyScaffold:
    """Safety guardrail builder and content validator.

    Encapsulates all safety logic previously inline in LLMService,
    including emergency keyword detection and condition-specific
    guardrail generation.
    """

    # ------------------------------------------------------------------
    # Keyword dictionaries per condition
    # ------------------------------------------------------------------

    _DIABETES_EMERGENCY_KEYWORDS: List[str] = [
        # Severe hypoglycemia
        "severe low",
        "can't wake",
        "unconscious",
        "seizure",
        "convulsion",
        "glucagon",
        "passed out",
        "blackout",
        "diabetic shock",
        "insulin shock",
        # DKA / hyperglycemia
        "dk symptoms",
        "diabetic ketoacidosis",
        "ketones",
        "large ketones",
        "moderate ketones",
        "vomiting blood sugar",
        "fruity breath",
        "can't breathe blood sugar",
        "chest pain diabetes",
        "extremely high",
        "over 600",
        "blood sugar 600",
        "bg 600",
    ]

    _MENTAL_HEALTH_CRISIS_KEYWORDS: List[str] = [
        "kill myself",
        "suicide",
        "end it",
        "give up",
        "want to die",
        "no reason to live",
        "hurt myself",
        "self harm",
        "self-harm",
        "cutting myself",
        "overdose on purpose",
    ]

    _GENERAL_MEDICAL_KEYWORDS: List[str] = [
        "emergency",
        "urgent",
        "help",
        "911",
        "emergency room",
        "er now",
        "hospital now",
        "can't breathe",
        "chest pain",
        "confused",
        "stroke",
        "heart attack",
        "allergic reaction",
        "anaphylaxis",
        "bleeding out",
        "unresponsive",
    ]

    # Unified list for backward-compatible simple checks
    _ALL_EMERGENCY_KEYWORDS: List[str] = (
        _DIABETES_EMERGENCY_KEYWORDS
        + _MENTAL_HEALTH_CRISIS_KEYWORDS
        + _GENERAL_MEDICAL_KEYWORDS
    )

    # ------------------------------------------------------------------
    # Guardrail templates per condition
    # ------------------------------------------------------------------

    _GUARDRAILS: Dict[str, List[str]] = {
        "diabetes_emergency": [
            "NEVER provide insulin dosing recommendations during emergencies.",
            "NEVER tell users to change their treatment plan.",
            "ALWAYS recommend seeking immediate medical attention or calling emergency services.",
            "Emphasize that severe hypoglycemia or DKA symptoms require urgent professional care.",
            "Mention glucagon only as something to discuss with a care team, not as instruction.",
        ],
        "mental_health_crisis": [
            "ALWAYS provide crisis hotline information (e.g., 988 Suicide & Crisis Lifeline in the US).",
            "NEVER minimize or dismiss the user's feelings.",
            "Encourage contacting a mental health professional or trusted person immediately.",
            "Avoid clinical diagnosis; focus on compassionate listening and resource provision.",
        ],
        "general_medical": [
            "NEVER provide specific medical treatment instructions.",
            "ALWAYS recommend consulting a healthcare provider or calling emergency services.",
            "Acknowledge uncertainty and individual variability in health conditions.",
            "Do not attempt to triage or diagnose based on limited information.",
        ],
    }

    # ------------------------------------------------------------------
    # Severity levels
    # ------------------------------------------------------------------

    _SEVERITY_ORDER: List[str] = ["info", "warning", "critical"]

    def __init__(self) -> None:
        """Initialize SafetyScaffold with compiled keyword regexes."""
        self._compiled_keywords: Dict[str, re.Pattern] = {}
        for condition, keywords in self._keyword_map().items():
            # Compile as word-boundary regex for more robust matching
            pattern = r"(?:" + "|".join(re.escape(kw) for kw in keywords) + r")"
            self._compiled_keywords[condition] = re.compile(pattern, re.IGNORECASE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_guardrails(self, condition: str, severity: str = "warning") -> List[str]:
        """Build a list of guardrail strings for a given condition.

        Args:
            condition: One of "diabetes_emergency", "mental_health_crisis",
                       "general_medical".
            severity: "info", "warning", or "critical". Higher severity
                      adds stricter guardrails.

        Returns:
            List of guardrail strings.
        """
        guardrails = list(self._GUARDRAILS.get(condition, []))

        if severity == "critical":
            guardrails.insert(
                0,
                "CRITICAL: This response must begin with an urgent recommendation "
                "to seek immediate professional help or call emergency services.",
            )
        elif severity == "warning":
            guardrails.insert(
                0,
                "WARNING: Emphasize the importance of consulting a healthcare "
                "provider promptly for any concerning symptoms.",
            )
        else:
            guardrails.insert(
                0,
                "INFO: Provide educational context only; remind the user that "
                "this is not medical advice.",
            )

        return guardrails

    def validate(
        self,
        content: str,
        context: Optional[Dict] = None,
    ) -> Dict:
        """Validate content against safety guardrails and keyword lists.

        Args:
            content: The text to validate (user message or AI response).
            context: Optional dict with keys like:
                - "condition": known condition hint
                - "severity": known severity hint
                - "source": "user" | "assistant" (defaults to "user")

        Returns:
            Dict with keys:
                - is_safe (bool): False if emergency keywords detected
                - safety_level (str): "safe", "warning", or "critical"
                - reasons (List[str]): Human-readable reasons for the assessment
                - requires_escalation (bool): True if professional help needed
                - matched_conditions (List[str]): Which condition keywords matched
        """
        context = context or {}
        source = context.get("source", "user")
        reasons: List[str] = []
        matched_conditions: List[str] = []

        # Keyword scan
        text_lower = content.lower()
        for condition, pattern in self._compiled_keywords.items():
            if pattern.search(text_lower):
                matched_conditions.append(condition)

        # Determine severity and escalation
        requires_escalation = bool(matched_conditions)

        if "diabetes_emergency" in matched_conditions or "mental_health_crisis" in matched_conditions:
            safety_level = "critical"
            reasons.append(
                "Detected language consistent with an acute medical or mental health emergency."
            )
        elif "general_medical" in matched_conditions:
            safety_level = "warning"
            reasons.append(
                "Detected language that may indicate an urgent medical situation."
            )
        else:
            safety_level = "safe"
            reasons.append("No emergency or safety keywords detected.")

        # If content is from the AI assistant, also check for policy violations
        if source == "assistant":
            policy_violations = self._check_policy_violations(content)
            if policy_violations:
                safety_level = max(
                    [safety_level] + [v["level"] for v in policy_violations],
                    key=lambda x: self._SEVERITY_ORDER.index(x) if x in self._SEVERITY_ORDER else 0,
                )
                reasons.extend(v["reason"] for v in policy_violations)
                requires_escalation = requires_escalation or any(
                    v["level"] == "critical" for v in policy_violations
                )

        return {
            "is_safe": safety_level == "safe",
            "safety_level": safety_level,
            "reasons": reasons,
            "requires_escalation": requires_escalation,
            "matched_conditions": matched_conditions,
        }

    def contains_emergency_keywords(self, text: str) -> bool:
        """Backward-compatible keyword check (replaces _contains_emergency_keywords).

        Args:
            text: Text to check.

        Returns:
            True if any emergency keyword is found.
        """
        return bool(self._compiled_keywords["all"].search(text.lower()))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _keyword_map(self) -> Dict[str, List[str]]:
        """Return mapping of condition name to keyword list."""
        return {
            "diabetes_emergency": self._DIABETES_EMERGENCY_KEYWORDS,
            "mental_health_crisis": self._MENTAL_HEALTH_CRISIS_KEYWORDS,
            "general_medical": self._GENERAL_MEDICAL_KEYWORDS,
            "all": self._ALL_EMERGENCY_KEYWORDS,
        }

    def _check_policy_violations(self, text: str) -> List[Dict[str, str]]:
        """Check AI-generated text for policy violations.

        Returns list of violation dicts with keys 'reason' and 'level'.
        """
        violations: List[Dict[str, str]] = []
        text_lower = text.lower()

        # Dosing advice detection
        dosing_patterns = [
            r"\btake\b\s+\d+\s*(?:units?|u)\b",
            r"\bgive\b\s+\d+\s*(?:units?|u)\b",
            r"\binject\b\s+\d+\s*(?:units?|u)\b",
            r"\bdose\b\s+\d+\s*(?:units?|u)\b",
            r"\b\d+\s*(?:units?|u)\s+of\s+insulin\b",
            r"\b(?:take|give|inject)\b\s+(?:a\s+)?\d+\s*(?:unit|u)\b",
        ]
        for pattern in dosing_patterns:
            if re.search(pattern, text_lower):
                violations.append({
                    "reason": "Detected potential insulin dosing instruction in AI response.",
                    "level": "critical",
                })
                break  # One dosing violation is enough

        # Treatment plan change
        treatment_patterns = [
            r"\bchange\b.*\btreatment\b",
            r"\bstop\b.*\binsulin\b",
            r"\bdiscontinue\b.*\bmedication\b",
        ]
        for pattern in treatment_patterns:
            if re.search(pattern, text_lower):
                violations.append({
                    "reason": "Detected potential treatment plan modification advice.",
                    "level": "critical",
                })
                break

        # Missing disclaimer check (warning only)
        if "educational" not in text_lower and "not medical advice" not in text_lower and len(text) > 200:
            violations.append({
                "reason": "Long response may be missing educational disclaimer.",
                "level": "warning",
            })

        return violations
