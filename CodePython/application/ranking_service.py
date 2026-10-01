"""Stable descending score ordering, optionally limited to the best matches."""

import math
from numbers import Real


class RankingService:
    def rank(self, candidates, top_k=None):
        if top_k is not None and (
            not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0
        ):
            raise ValueError("top_k must be a nonnegative integer or None.")
        try:
            entries = list(candidates)
        except TypeError as exc:
            raise ValueError("Candidates must be an iterable of (product, score) pairs.") from exc
        for candidate in entries:
            if not isinstance(candidate, (tuple, list)) or len(candidate) != 2:
                raise ValueError("Every candidate must be a (product, score) pair.")
            score = candidate[1]
            try:
                valid_score = (
                    isinstance(score, Real) and not isinstance(score, bool)
                    and math.isfinite(score)
                )
            except OverflowError:
                valid_score = False
            if not valid_score:
                raise ValueError("Candidate scores must be finite numbers.")
        ranked = sorted(entries, key=lambda candidate: candidate[1], reverse=True)
        return ranked if top_k is None else ranked[:top_k]
