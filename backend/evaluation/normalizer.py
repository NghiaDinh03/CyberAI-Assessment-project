"""Verdict normalization for Evaluation and Golden Case feedback.

Ensures strict separation between canonical evaluation verdicts and legacy labels.
In particular:
- 'compliant' maps to 'satisfied'
- 'partial' maps to 'partial'
- 'non_compliant' is NEVER mapped automatically to 'missing' or 'not_evidenced';
  instead, it is flagged as 'needs_label_review' and excluded from automated evaluation.
"""

from typing import Optional, Tuple
from .schemas import CANONICAL_VERDICTS


def normalize_expert_verdict(raw_verdict: Optional[str]) -> Tuple[Optional[str], str]:
    """Normalize a raw or legacy verdict string into a canonical assessment verdict.

    Returns:
        (canonical_verdict, status_code)
        
        status_code may be:
        - 'approved': Verdict is canonical ('satisfied', 'partial', 'not_evidenced',
                      'missing', 'needs_expert_review') or safely mapped ('compliant' -> 'satisfied').
        - 'needs_label_review': Legacy ambiguous label (e.g. 'non_compliant') that requires
                                auditor/expert re-classification.
        - 'missing_label': Input was empty or None.
        - 'unknown_label': Input was not recognized.
    """
    if raw_verdict is None:
        return (None, "missing_label")

    clean = str(raw_verdict).strip().lower()
    if not clean:
        return (None, "missing_label")

    # Already canonical
    if clean in CANONICAL_VERDICTS:
        return (clean, "approved")

    # Legacy safe mapping
    if clean == "compliant":
        return ("satisfied", "approved")

    # Legacy ambiguous mapping - MUST NOT MAP TO MISSING OR NOT_EVIDENCED
    if clean == "non_compliant":
        return (None, "needs_label_review")

    # Additional standard legacy aliases
    if clean in ("not_compliant", "noncompliant"):
        return (None, "needs_label_review")

    return (None, "unknown_label")


def is_valid_canonical_verdict(verdict: Optional[str]) -> bool:
    """Return True if verdict is strictly one of the 5 canonical verdicts."""
    if not verdict:
        return False
    return str(verdict).strip().lower() in CANONICAL_VERDICTS
