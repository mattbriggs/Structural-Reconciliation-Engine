"""Node matcher: builds a :class:`MatchGraph` from evidence (REQ-037-051).

Strategy, in deterministic order (REQ-048):

1. **Authoritative identifiers.** A persistent id that is unique and
   non-duplicated in *both* trees, on type-compatible nodes, yields a
   confirmed match independent of lexical similarity (REQ-034, AC-008,
   AC-024). Duplicated ids are never treated as authoritative (AC-010).
2. **Similarity.** Remaining nodes are scored pairwise; hard constraints
   disqualify candidates (REQ-042, AC-011). Ambiguity within the configured
   margin is preserved rather than resolved by position (REQ-044, AC-009).
   Below-threshold pairs are left unmatched (REQ-043, AC-005).

All ordering is derived from sorted node references and profile tie-break
keys, never from map iteration order (REQ-045, REQ-203).
"""

from __future__ import annotations

from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.matches import (
    ConstraintViolation,
    MatchCandidate,
    MatchGraph,
    MatchState,
)
from reconciliation.core.contracts.profiles import EvidenceType, MatchingProfile
from reconciliation.core.contracts.tree import NodeRef
from reconciliation.core.evidence.extractor import EvidenceIndex, NodeEvidence
from reconciliation.core.matching.confidence import derive_confidence
from reconciliation.core.matching.constraints import evaluate_constraints
from reconciliation.core.matching.scorer import score_pair


def _match_id(source_ref: NodeRef, target_ref: NodeRef) -> str:
    return f"m:{source_ref}->{target_ref}"


class NodeMatcherService:
    """Default :class:`NodeMatcher` implementation."""

    def match(self, evidence: EvidenceIndex, profile: MatchingProfile) -> MatchGraph:
        """Produce a deterministic match graph.

        :param evidence: Per-node evidence for both trees.
        :param profile: Active matching profile.
        :returns: A :class:`MatchGraph` with confirmed, ambiguous, and
            candidate correspondences.
        """
        candidates: list[MatchCandidate] = []
        matched_sources: set[NodeRef] = set()
        matched_targets: set[NodeRef] = set()

        # Phase 1: authoritative persistent-id matching.
        if EvidenceType.PERSISTENT_ID in profile.authoritative_id_features:
            for cand in self._authoritative_matches(evidence, profile):
                candidates.append(cand)
                if cand.state is MatchState.CONFIRMED:
                    matched_sources.add(cand.source_node_ref)
                    matched_targets.add(cand.target_node_ref)

        # Phase 2: similarity matching over remaining nodes.
        candidates.extend(
            self._similarity_matches(evidence, profile, matched_sources, matched_targets)
        )

        candidates.sort(key=lambda c: (c.source_node_ref, c.target_node_ref, c.state.value))
        return MatchGraph(candidates=tuple(candidates))

    # -- Phase 1 -----------------------------------------------------------

    def _authoritative_matches(
        self, evidence: EvidenceIndex, profile: MatchingProfile
    ) -> list[MatchCandidate]:
        source_by_id = self._unique_id_index(evidence.source, evidence.duplicate_source_ids)
        target_by_id = self._unique_id_index(evidence.target, evidence.duplicate_target_ids)

        results: list[MatchCandidate] = []
        for persistent_id in sorted(source_by_id.keys() & target_by_id.keys()):
            source = source_by_id[persistent_id]
            target = target_by_id[persistent_id]
            hard, soft = evaluate_constraints(source, target, profile)
            score = score_pair(source, target, profile)
            if hard:
                # Contradictory id + type: reject rather than confirm (AC-011).
                results.append(
                    self._candidate(
                        source, target, MatchState.REJECTED, score,
                        derive_confidence(score, profile.calibration),
                        profile, hard=hard, soft=soft,
                    )
                )
                continue
            # An authoritative identifier establishes identity with maximal
            # confidence; this is deliberately distinct from the (diluted)
            # feature *score* so that a content/structure change on an
            # authoritatively-identified node does not weaken the match
            # (REQ-034, REQ-046, AC-008, AC-024).
            confidence = Confidence(
                value=1.0,
                calibrated=profile.calibration.calibrated,
                model=profile.calibration.model,
            )
            results.append(
                self._candidate(
                    source, target, MatchState.CONFIRMED, score, confidence,
                    profile, soft=soft,
                )
            )
        return results

    @staticmethod
    def _unique_id_index(
        evidence: dict[NodeRef, NodeEvidence], duplicates: frozenset[str]
    ) -> dict[str, NodeEvidence]:
        index: dict[str, NodeEvidence] = {}
        for node_ref in sorted(evidence):
            ev = evidence[node_ref]
            if ev.persistent_id is None or ev.persistent_id in duplicates:
                continue
            index[ev.persistent_id] = ev
        return index

    # -- Phase 2 -----------------------------------------------------------

    def _similarity_matches(
        self,
        evidence: EvidenceIndex,
        profile: MatchingProfile,
        matched_sources: set[NodeRef],
        matched_targets: set[NodeRef],
    ) -> list[MatchCandidate]:
        free_sources = sorted(s for s in evidence.source if s not in matched_sources)
        free_targets = sorted(t for t in evidence.target if t not in matched_targets)

        # Precompute admissible scored pairs (no hard-constraint violations).
        scored: dict[NodeRef, list[tuple[float, NodeRef]]] = {}
        for s in free_sources:
            src_ev = evidence.source[s]
            row: list[tuple[float, NodeRef]] = []
            for t in free_targets:
                tgt_ev = evidence.target[t]
                hard, _ = evaluate_constraints(src_ev, tgt_ev, profile)
                if hard:
                    continue
                value = score_pair(src_ev, tgt_ev, profile).value
                if value >= profile.probable_threshold:
                    row.append((value, t))
            row.sort(key=lambda pair: (-pair[0], pair[1]))
            scored[s] = row

        edges = self._ambiguous_edges(scored, profile)
        ambiguous_sources = {s for s, _t in edges}
        ambiguous_targets = {t for _s, t in edges}

        results: list[MatchCandidate] = []
        taken_targets: set[NodeRef] = set()

        # Emit ambiguous candidates (they do not consume targets). Alternatives
        # are the competing edges that share either endpoint (REQ-044, REQ-256).
        sorted_edges = sorted(edges)
        for s, t in sorted_edges:
            alternatives = tuple(
                _match_id(s2, t2)
                for s2, t2 in sorted_edges
                if (s2, t2) != (s, t) and (s2 == s or t2 == t)
            )
            score = score_pair(evidence.source[s], evidence.target[t], profile)
            results.append(
                self._candidate(
                    evidence.source[s], evidence.target[t], MatchState.AMBIGUOUS,
                    score, derive_confidence(score, profile.calibration),
                    profile, alternatives=alternatives,
                )
            )

        # Greedy confirmation of unambiguous mutual bests, in deterministic order.
        confirmable: list[tuple[float, NodeRef, NodeRef]] = []
        for s in free_sources:
            if s in ambiguous_sources or not scored[s]:
                continue
            best_value, best_target = scored[s][0]
            if best_value >= profile.match_threshold and best_target not in ambiguous_targets:
                confirmable.append((best_value, s, best_target))
        confirmable.sort(key=lambda triple: (-triple[0], triple[1], triple[2]))

        for _value, s, t in confirmable:
            if s in matched_sources or t in taken_targets or t in matched_targets:
                continue
            score = score_pair(evidence.source[s], evidence.target[t], profile)
            results.append(
                self._candidate(
                    evidence.source[s], evidence.target[t], MatchState.CONFIRMED,
                    score, derive_confidence(score, profile.calibration), profile,
                )
            )
            matched_sources.add(s)
            taken_targets.add(t)

        return results

    @staticmethod
    def _ambiguous_edges(
        scored: dict[NodeRef, list[tuple[float, NodeRef]]], profile: MatchingProfile
    ) -> set[tuple[NodeRef, NodeRef]]:
        """Return candidate (source, target) edges that are mutually ambiguous.

        Covers both source-side ambiguity (one source, several near-tied
        targets) and target-side ambiguity (several sources contend for one
        target) so that no ambiguity is silently resolved by position (AC-009).
        """
        margin = profile.ambiguity_margin
        threshold = profile.match_threshold
        edges: set[tuple[NodeRef, NodeRef]] = set()

        # Source-side: a source with >= 2 near-tied plausible targets.
        for s, row in scored.items():
            if len(row) >= 2 and row[0][0] >= threshold and row[0][0] - row[1][0] <= margin:
                top = row[0][0]
                edges.update((s, t) for v, t in row if top - v <= margin)

        # Target-side: a target that is the top pick of >= 2 near-tied sources.
        best_by_target: dict[NodeRef, list[tuple[float, NodeRef]]] = {}
        for s, row in scored.items():
            if row and row[0][0] >= threshold:
                best_by_target.setdefault(row[0][1], []).append((row[0][0], s))
        for t, contenders in best_by_target.items():
            if len(contenders) < 2:
                continue
            contenders.sort(key=lambda pair: (-pair[0], pair[1]))
            top = contenders[0][0]
            close = [(v, s) for v, s in contenders if top - v <= margin]
            if len(close) >= 2:
                edges.update((s, t) for _v, s in close)
        return edges

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _candidate(
        source: NodeEvidence,
        target: NodeEvidence,
        state: MatchState,
        score: object,
        confidence: Confidence,
        profile: MatchingProfile,
        *,
        hard: tuple[ConstraintViolation, ...] = (),
        soft: tuple[ConstraintViolation, ...] = (),
        alternatives: tuple[str, ...] = (),
    ) -> MatchCandidate:
        from reconciliation.core.contracts.evidence import FeatureScore

        assert isinstance(score, FeatureScore)
        return MatchCandidate(
            match_id=_match_id(source.node_ref, target.node_ref),
            source_node_ref=source.node_ref,
            target_node_ref=target.node_ref,
            state=state,
            score=score,
            confidence=confidence,
            evidence=score.contributions,
            hard_constraints=hard,
            violated_soft_constraints=soft,
            alternative_match_ids=alternatives,
            profile_version=profile.version,
        )
