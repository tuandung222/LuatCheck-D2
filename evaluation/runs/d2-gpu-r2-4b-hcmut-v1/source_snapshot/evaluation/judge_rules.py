"""The scoring rule that turns one validated judgment into strict success, shared by the analysis and the human-audit scorer.

Pure functions, no imports: the rule is a definition, kept in one place so judge, analysis and human audit cannot drift apart.

Abstention outputs (the task expects a refusal, or the candidate refused / asked a clarifying question)
  A statement that the information is absent from the sources ("Không có thông tin ... trong các văn bản đã tra cứu") is not a
  factual claim; the judge prompt says so and should not list it. Older judgments (before this rule) sometimes list it labelled
  `not_established`, which would make every correct refusal a failure. For abstention outputs the scoring therefore
    * ignores claims labelled `not_established` (they can only be the absence statement or unverifiable filler),
    * still fails on a claim labelled `contradicted` (an assertion that the sources refute),
    * still requires behaviour_appropriate, correctness == 2 and completeness == 2 from the judge.
  Limit of the rule: invented assertions inside a refusal that the judge labelled `not_established` are not penalised by the claim
  check; correctness == 2 is then the only guard. For every other output all claims must be `supported`.
"""
from typing import Any, Dict, List

ABSTENTION_STATUSES = ("refused", "clarified")


def is_abstention(expected_behavior: str, candidate_behavior: str) -> bool:
    return expected_behavior == "refuse" or candidate_behavior in ABSTENTION_STATUSES


def counted_claims(claims: List[Dict[str, Any]], abstention: bool) -> List[Dict[str, Any]]:
    """Claims that count toward faithfulness / strict success (absence statements dropped for abstention outputs)."""
    return [c for c in claims if not (abstention and c["support"] == "not_established")]


def unsupported_claims(claims: List[Dict[str, Any]], abstention: bool) -> List[Dict[str, Any]]:
    return [c for c in counted_claims(claims, abstention) if c["support"] != "supported"]


def judgment_strict_success(judgment: Dict[str, Any], abstention: bool) -> bool:
    """judgment must be judgeable. behaviour_appropriate, correctness 2, completeness 2 and no unsupported counted claim."""
    return bool(judgment["behaviour_appropriate"] and judgment["correctness"] == 2 and judgment["completeness"] == 2
                and not unsupported_claims(judgment["claims"], abstention))
