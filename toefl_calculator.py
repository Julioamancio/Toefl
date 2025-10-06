"""Utility functions for TOEFL Junior calculations used during import preview.
Provides CEFR mapping for Listening, school label resolution from `turma_meta`,
and CSA grade calculation for Listening.
"""
from typing import Optional


def cefr_listening(score: Optional[int]) -> Optional[str]:
    """
    Map a Listening score (200-300) to a CEFR level.
    Uses the central calculation from models to keep consistency across the app.
    """
    if score is None:
        return None
    try:
        from models import calculate_level_by_score
        return calculate_level_by_score(score, 'listening')
    except Exception:
        # Fallback to listening_csa thresholds if models is unavailable
        try:
            from listening_csa import get_listening_cefr
            return get_listening_cefr(score)
        except Exception:
            return None


def school_label(turma_meta: Optional[str]) -> Optional[str]:
    """
    Resolve the expected CEFR level associated with a school label (`turma_meta`),
    e.g. '6.1', '6.2', '9.2', etc.
    """
    if turma_meta in (None, ""):
        return None
    try:
        from models import SCHOOL_LEVEL_MAP
        # Normalize like '6,1' or '6.1' to float
        value = float(str(turma_meta).strip().replace(",", "."))
        return SCHOOL_LEVEL_MAP.get(value)
    except Exception:
        return None


def grade_listening(listening_score: Optional[int], turma_meta: Optional[str], turma_name: Optional[str] = None) -> Optional[float]:
    """
    Calcula CSA Listening (0–5) baseado em listening score (200–300) e turma/nivel.
    """
    if listening_score is None:
        return None
    try:
        from listening_csa import compute_listening_csa
        rotulo = None
        if turma_meta not in (None, ""):
            rotulo = str(turma_meta).strip().replace(",", ".")
        result = compute_listening_csa(rotulo, listening_score, turma_name=turma_name)
        return result.get("points")
    except Exception:
        return None