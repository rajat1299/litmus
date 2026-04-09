from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from litmus.compatibility import compatibility_report_from_result
from litmus.confidence import calculate_confidence_score
from litmus.config import DecisionPolicy, coerce_decision_policy
from litmus.properties.runner import PropertyCheckStatus
from litmus.replay.differential import ReplayClassification


class RiskLevel(str, Enum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"


class PolicyCheckStatusValue(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class MergeRecommendation(str, Enum):
    ALLOW = "allow"
    REVIEW_REQUIRED = "review_required"
    BLOCK = "block"


class VerificationDecision(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    NEEDS_DEEPER_VERIFICATION = "needs_deeper_verification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(slots=True)
class UnsupportedGap:
    boundary: str
    detail: str
    status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "boundary": self.boundary,
            "detail": self.detail,
            "status": self.status,
        }


@dataclass(slots=True)
class EvidenceSummary:
    confidence_score: float
    total_signals: int
    replay_signals: int
    property_signals: int
    detected_boundary_count: int
    unsupported_gap_count: int
    pending_review_count: int
    replay_counts: dict[str, int]
    property_counts: dict[str, int]
    invariant_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "confidence_score": self.confidence_score,
            "total_signals": self.total_signals,
            "replay_signals": self.replay_signals,
            "property_signals": self.property_signals,
            "detected_boundary_count": self.detected_boundary_count,
            "unsupported_gap_count": self.unsupported_gap_count,
            "pending_review_count": self.pending_review_count,
            "replay_counts": dict(self.replay_counts),
            "property_counts": dict(self.property_counts),
            "invariant_counts": dict(self.invariant_counts),
        }


@dataclass(slots=True)
class RiskAssessment:
    level: RiskLevel
    risk_classes: list[str]
    detected_boundaries: list[str]
    unsupported_gaps: list[UnsupportedGap] = field(default_factory=list)
    evidence_expectations: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level.value,
            "risk_classes": list(self.risk_classes),
            "detected_boundaries": list(self.detected_boundaries),
            "unsupported_gaps": [gap.to_dict() for gap in self.unsupported_gaps],
            "evidence_expectations": list(self.evidence_expectations),
            "reasons": list(self.reasons),
        }


@dataclass(slots=True)
class PolicyCheck:
    name: str
    status: PolicyCheckStatusValue
    detail: str
    blocking: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "blocking": self.blocking,
        }


@dataclass(slots=True)
class PolicyEvaluation:
    policy_name: str
    merge_recommendation: MergeRecommendation
    checks: list[PolicyCheck] = field(default_factory=list)

    @property
    def failing_checks(self) -> list[str]:
        return [check.name for check in self.checks if check.status is PolicyCheckStatusValue.FAILED]

    @property
    def warning_checks(self) -> list[str]:
        return [check.name for check in self.checks if check.status is PolicyCheckStatusValue.WARNING]

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_name": self.policy_name,
            "merge_recommendation": self.merge_recommendation.value,
            "checks": [check.to_dict() for check in self.checks],
            "failing_checks": self.failing_checks,
            "warning_checks": self.warning_checks,
        }


@dataclass(slots=True)
class VerificationVerdict:
    decision: VerificationDecision
    summary: str
    reasons: list[str]
    confidence_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "confidence_score": self.confidence_score,
        }


@dataclass(slots=True)
class VerificationDecisionBundle:
    evidence: EvidenceSummary
    risk: RiskAssessment
    policy: PolicyEvaluation
    verdict: VerificationVerdict

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence": self.evidence.to_dict(),
            "risk_assessment": self.risk.to_dict(),
            "policy_evaluation": self.policy.to_dict(),
            "verification_verdict": self.verdict.to_dict(),
        }


def evaluate_verification_result(result) -> VerificationDecisionBundle:
    decision_policy = coerce_decision_policy(
        getattr(result, "decision_policy", DecisionPolicy.ALPHA_LOCAL_V1)
    )
    compatibility = compatibility_report_from_result(result)
    replay_counts = Counter(replay.classification.value for replay in result.replay_results)
    scored_property_results = [
        property_result
        for property_result in result.property_results
        if property_result.status is not PropertyCheckStatus.SKIPPED
    ]
    property_counts = Counter(property_result.status.value for property_result in result.property_results)
    confirmed_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "confirmed")
    suggested_invariants = sum(1 for invariant in result.invariants if invariant.status.value == "suggested")
    pending_review_count = sum(1 for invariant in result.invariants if invariant.is_pending_suggestion())

    unsupported_gaps: list[UnsupportedGap] = []
    detected_boundaries: list[str] = []
    for boundary, snapshot in compatibility.boundaries.items():
        if snapshot.detected:
            detected_boundaries.append(boundary)
        if not snapshot.unsupported:
            continue
        details = snapshot.unsupported_details or ["Unsupported coverage detected."]
        for detail in details:
            unsupported_gaps.append(
                UnsupportedGap(
                    boundary=boundary,
                    detail=detail,
                    status=snapshot.status,
                )
            )

    confidence_score = calculate_confidence_score(result.replay_results, result.property_results)
    evidence = EvidenceSummary(
        confidence_score=confidence_score,
        total_signals=len(result.replay_results) + len(scored_property_results),
        replay_signals=len(result.replay_results),
        property_signals=len(scored_property_results),
        detected_boundary_count=len(detected_boundaries),
        unsupported_gap_count=len(unsupported_gaps),
        pending_review_count=pending_review_count,
        replay_counts={
            ReplayClassification.UNCHANGED.value: replay_counts[ReplayClassification.UNCHANGED.value],
            ReplayClassification.BREAKING_CHANGE.value: replay_counts[ReplayClassification.BREAKING_CHANGE.value],
            ReplayClassification.BENIGN_CHANGE.value: replay_counts[ReplayClassification.BENIGN_CHANGE.value],
            ReplayClassification.IMPROVEMENT.value: replay_counts[ReplayClassification.IMPROVEMENT.value],
        },
        property_counts={
            PropertyCheckStatus.PASSED.value: property_counts[PropertyCheckStatus.PASSED.value],
            PropertyCheckStatus.FAILED.value: property_counts[PropertyCheckStatus.FAILED.value],
            PropertyCheckStatus.SKIPPED.value: property_counts[PropertyCheckStatus.SKIPPED.value],
        },
        invariant_counts={
            "total": len(result.invariants),
            "confirmed": confirmed_invariants,
            "suggested": suggested_invariants,
        },
    )

    risk_classes = _risk_classes_for_result(
        invariants=result.invariants,
        property_results=result.property_results,
        scenarios=result.scenarios,
        route_count=len(result.routes),
        detected_boundaries=detected_boundaries,
    )
    evidence_expectations = _evidence_expectations_for_result(
        scenarios=result.scenarios,
        scored_property_results=scored_property_results,
        detected_boundaries=detected_boundaries,
        pending_review_count=pending_review_count,
    )
    risk_reasons = _risk_reasons(
        detected_boundaries=detected_boundaries,
        unsupported_gaps=unsupported_gaps,
        pending_review_count=pending_review_count,
        route_count=len(result.routes),
    )
    risk = RiskAssessment(
        level=_risk_level_for_result(
            replay_counts=replay_counts,
            property_counts=property_counts,
            unsupported_gaps=unsupported_gaps,
            route_count=len(result.routes),
            pending_review_count=pending_review_count,
            total_signals=evidence.total_signals,
            detected_boundaries=detected_boundaries,
        ),
        risk_classes=risk_classes,
        detected_boundaries=detected_boundaries,
        unsupported_gaps=unsupported_gaps,
        evidence_expectations=evidence_expectations,
        reasons=risk_reasons,
    )

    has_blocking_regressions = (
        replay_counts[ReplayClassification.BREAKING_CHANGE.value] > 0
        or property_counts[PropertyCheckStatus.FAILED.value] > 0
    )
    checks = [
        PolicyCheck(
            name="blocking_regressions",
            status=(
                PolicyCheckStatusValue.FAILED
                if has_blocking_regressions
                else PolicyCheckStatusValue.PASSED
            ),
            detail=(
                "Breaking replay or failed property check detected."
                if has_blocking_regressions
                else "No breaking replay or failed property checks detected."
            ),
            blocking=_is_blocking_check("blocking_regressions", decision_policy),
        ),
        PolicyCheck(
            name="sufficient_evidence",
            status=(
                PolicyCheckStatusValue.FAILED
                if evidence.total_signals == 0
                else PolicyCheckStatusValue.PASSED
            ),
            detail=(
                "No replay or property signals were recorded for this run."
                if evidence.total_signals == 0
                else "At least one replay or property signal was recorded."
            ),
            blocking=_is_blocking_check("sufficient_evidence", decision_policy),
        ),
        PolicyCheck(
            name="supported_boundary_coverage",
            status=(
                PolicyCheckStatusValue.FAILED
                if unsupported_gaps
                else PolicyCheckStatusValue.PASSED
            ),
            detail=(
                "Unsupported boundary coverage was detected in the exercised path."
                if unsupported_gaps
                else "No unsupported boundary coverage was detected in the exercised path."
            ),
            blocking=_is_blocking_check("supported_boundary_coverage", decision_policy),
        ),
        PolicyCheck(
            name="suggested_invariant_review",
            status=(
                PolicyCheckStatusValue.WARNING
                if pending_review_count > 0
                else PolicyCheckStatusValue.PASSED
            ),
            detail=(
                f"{pending_review_count} suggested invariants still need review."
                if pending_review_count > 0
                else "No pending suggested invariants need review."
            ),
            blocking=_is_blocking_check("suggested_invariant_review", decision_policy),
        ),
    ]

    decision = _decision_from_checks(checks)
    merge_recommendation = _merge_recommendation_from_checks(checks)
    policy = PolicyEvaluation(
        policy_name=decision_policy.value,
        merge_recommendation=merge_recommendation,
        checks=checks,
    )
    verdict = VerificationVerdict(
        decision=decision,
        summary=_summary_for_decision(decision),
        reasons=_verdict_reasons(checks=checks, unsupported_gaps=unsupported_gaps),
        confidence_score=confidence_score,
    )
    return VerificationDecisionBundle(
        evidence=evidence,
        risk=risk,
        policy=policy,
        verdict=verdict,
    )


def _risk_classes_for_result(
    *,
    invariants,
    property_results,
    scenarios,
    route_count: int,
    detected_boundaries: list[str],
) -> list[str]:
    risk_classes: list[str] = []
    if route_count > 0 or scenarios or detected_boundaries:
        risk_classes.append("reliability")
    if invariants or property_results:
        risk_classes.append("correctness")
    if any(boundary in {"http", "redis"} for boundary in detected_boundaries):
        risk_classes.append("external_dependency")
    if any(boundary in {"sqlalchemy", "redis"} for boundary in detected_boundaries):
        risk_classes.append("data_integrity")
    return risk_classes


def _evidence_expectations_for_result(
    *,
    scenarios,
    scored_property_results,
    detected_boundaries: list[str],
    pending_review_count: int,
) -> list[str]:
    expectations: list[str] = []
    if scenarios:
        expectations.append("deterministic_replay")
    if scored_property_results:
        expectations.append("property_checks")
    if detected_boundaries:
        expectations.append("supported_boundary_coverage")
    if pending_review_count > 0:
        expectations.append("reviewed_suggested_invariants")
    return expectations


def _risk_reasons(
    *,
    detected_boundaries: list[str],
    unsupported_gaps: list[UnsupportedGap],
    pending_review_count: int,
    route_count: int,
) -> list[str]:
    reasons: list[str] = []
    if route_count > 0:
        reasons.append(f"{route_count} route(s) are in the current verification scope.")
    if detected_boundaries:
        reasons.append(
            "Detected boundary coverage on " + ", ".join(detected_boundaries) + "."
        )
    if unsupported_gaps:
        reasons.append(
            "Unsupported coverage remains on "
            + ", ".join(sorted({gap.boundary for gap in unsupported_gaps}))
            + "."
        )
    if pending_review_count > 0:
        reasons.append(f"{pending_review_count} suggested invariants still need review.")
    return reasons


def _risk_level_for_result(
    *,
    replay_counts: Counter,
    property_counts: Counter,
    unsupported_gaps: list[UnsupportedGap],
    route_count: int,
    pending_review_count: int,
    total_signals: int,
    detected_boundaries: list[str],
) -> RiskLevel:
    if (
        replay_counts[ReplayClassification.BREAKING_CHANGE.value] > 0
        or property_counts[PropertyCheckStatus.FAILED.value] > 0
        or unsupported_gaps
        or any(boundary in {"sqlalchemy", "redis"} for boundary in detected_boundaries)
    ):
        return RiskLevel.HIGH
    if (
        route_count > 0
        or pending_review_count > 0
        or total_signals > 0
        or detected_boundaries
    ):
        return RiskLevel.ELEVATED
    return RiskLevel.LOW


def _decision_from_checks(
    checks: list[PolicyCheck],
) -> VerificationDecision:
    status_by_name = {check.name: check.status for check in checks}
    if status_by_name["blocking_regressions"] is PolicyCheckStatusValue.FAILED:
        return VerificationDecision.UNSAFE
    if status_by_name["sufficient_evidence"] is PolicyCheckStatusValue.FAILED:
        return VerificationDecision.INSUFFICIENT_EVIDENCE
    if status_by_name["supported_boundary_coverage"] is PolicyCheckStatusValue.FAILED:
        return VerificationDecision.NEEDS_DEEPER_VERIFICATION
    return VerificationDecision.SAFE


def _merge_recommendation_from_checks(checks: list[PolicyCheck]) -> MergeRecommendation:
    failed_checks = [check for check in checks if check.status is PolicyCheckStatusValue.FAILED]
    if any(check.blocking for check in failed_checks):
        return MergeRecommendation.BLOCK
    if failed_checks:
        return MergeRecommendation.REVIEW_REQUIRED
    return MergeRecommendation.ALLOW


def _is_blocking_check(check_name: str, policy_name: DecisionPolicy) -> bool:
    return check_name in _blocking_checks_for_policy(policy_name)


def _blocking_checks_for_policy(policy_name: DecisionPolicy) -> frozenset[str]:
    if policy_name is DecisionPolicy.STRICT_LOCAL_V1:
        return frozenset(
            {
                "blocking_regressions",
                "sufficient_evidence",
                "supported_boundary_coverage",
            }
        )
    return frozenset({"blocking_regressions"})


def _summary_for_decision(decision: VerificationDecision) -> str:
    summaries = {
        VerificationDecision.SAFE: "Verification evidence supports this change for the current grounded surface.",
        VerificationDecision.UNSAFE: "Verification found a blocking regression in the current grounded surface.",
        VerificationDecision.NEEDS_DEEPER_VERIFICATION: (
            "Verification found unsupported coverage gaps, so the grounded surface is not enough to trust this change."
        ),
        VerificationDecision.INSUFFICIENT_EVIDENCE: (
            "Verification did not gather enough grounded evidence to support a decision."
        ),
    }
    return summaries[decision]


def _verdict_reasons(
    *,
    checks: list[PolicyCheck],
    unsupported_gaps: list[UnsupportedGap],
) -> list[str]:
    reasons = [
        check.detail
        for check in checks
        if check.status in {PolicyCheckStatusValue.FAILED, PolicyCheckStatusValue.WARNING}
    ]
    if unsupported_gaps:
        reasons.extend(
            f"{gap.boundary}: {gap.detail}"
            for gap in unsupported_gaps
        )
    return reasons
