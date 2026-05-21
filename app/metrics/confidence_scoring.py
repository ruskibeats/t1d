"""Confidence scoring utilities for graph detectors."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ConfidenceComponents:
    """Decomposed confidence components for graph edge scoring."""
    pattern_strength: float  # How strong is the pattern match (0-1)
    temporal_alignment: float  # Time window match quality (0-1)
    effect_magnitude: float  # Size of the effect (0-1)
    data_quality: float  # Completeness of data (0-1)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_strength": self.pattern_strength,
            "temporal_alignment": self.temporal_alignment,
            "effect_magnitude": self.effect_magnitude,
            "data_quality": self.data_quality,
        }
    
    def combined_score(self) -> float:
        """Calculate combined confidence score."""
        return (
            self.pattern_strength * 0.4 +
            self.temporal_alignment * 0.3 +
            self.effect_magnitude * 0.2 +
            self.data_quality * 0.1
        )


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for UI/RAG wording."""
    LOW: float = 0.3
    MEDIUM: float = 0.6
    HIGH: float = 0.8


def categorize_confidence(confidence: float) -> str:
    """Return 'low', 'medium', or 'high' for a confidence score."""
    if confidence < ConfidenceThresholds.MEDIUM:
        return "low"
    elif confidence < ConfidenceThresholds.HIGH:
        return "medium"
    return "high"


def build_provenance(
    detector_name: str,
    detector_version: str,
    components: ConfidenceComponents,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build provenance payload for graph edge."""
    provenance = {
        "detector": detector_name,
        "detector_version": detector_version,
        "scoring": {
            "method": "weighted_sum",
            "components": components.to_dict(),
        },
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    if extras:
        provenance.update(extras)
    return provenance