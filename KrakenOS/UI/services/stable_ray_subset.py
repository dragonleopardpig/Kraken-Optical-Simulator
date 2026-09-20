"""bugs/0824: choose which rays to draw by the ray's OWN identity, not its position.

`source_illumination_rays_overlay._subsample` picks with
``rng.choice(len(polylines), cap, replace=False)``. Its comment calls that
"deterministic (seeded)", and it is -- for one fixed list. It is not stable across
runs: the draw is over LIST POSITIONS, so anything that changes the population
re-rolls every ray on screen. Raise the ray budget, change a role tag, let one more
ray clip, and the overlay you are comparing against is gone.

That matters on exactly the path a user reaches for when they need to know where
stray light came from, which is the same observation optiland's NSQ path recorder
makes: its ``record_paths`` contract selects a subset by a PCG32 hash of ``ray_id``
so membership is "independent of batch_size ... and stable for a given seed
regardless of how many rays end up actually being born".

Here that means: a ray's membership is a pure function of (its identity, the seed),
compared against a threshold. Two policies, because they trade different things:

* ``select_smallest_k`` -- exactly ``cap`` items, the ``cap`` lowest hashes. At a
  fixed population it is perfectly reproducible; when the population grows the
  threshold tightens, so the set changes only by competition between fixed hashes,
  never by a re-roll.
* ``select_by_probability`` -- a FIXED threshold, so membership is fully
  population-independent: a ray is in or out no matter what else was traced. The
  count then varies around ``p * n``. This is the one to use when two runs at
  different ray budgets must be compared ray-for-ray.

Neither reads a global RNG, so nothing upstream can perturb the selection by
consuming random numbers first -- another way the old code could shift silently.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

_MASK64 = (1 << 64) - 1
_U32 = (1 << 32) - 1

#: splitmix64 constants -- a well-mixed 64-bit finalizer. The point is avalanche
#: (one bit of identity flips half the output bits), so adjacent ray indices do not
#: land adjacent in hash space and a subset is spatially unbiased.
_GOLDEN = 0x9E3779B97F4A7C15
_MIX_A = 0xBF58476D1CE4E5B9
_MIX_B = 0x94D049BB133111EB


def _splitmix64(value: int) -> int:
    z = (value + _GOLDEN) & _MASK64
    z = ((z ^ (z >> 30)) * _MIX_A) & _MASK64
    z = ((z ^ (z >> 27)) * _MIX_B) & _MASK64
    return (z ^ (z >> 31)) & _MASK64


def hash_identity(identity: Any, seed: int = 0) -> int:
    """Uniform 32-bit hash of an arbitrary hashable identity.

    Folds each element of a tuple identity in turn, so ``(source, index)`` mixes
    both parts rather than letting a shared source collapse the space.
    """
    acc = _splitmix64(int(seed) & _MASK64)
    parts = identity if isinstance(identity, tuple) else (identity,)
    for part in parts:
        if isinstance(part, bool):
            item = 1 if part else 0
        elif isinstance(part, int):
            item = part & _MASK64
        elif isinstance(part, float):
            item = int.from_bytes(repr(part).encode(), "little", signed=False) & _MASK64
        else:
            item = int.from_bytes(str(part).encode(), "little", signed=False) & _MASK64
        acc = _splitmix64((acc ^ item) & _MASK64)
    return acc & _U32


def ray_identity(record: Any) -> tuple:
    """A stable identity for one traced ray record.

    Prefers the engine's own ray index, which survives reordering and re-tracing.
    Falls back to the launch point, which is stable for a seeded source sampler.
    Never falls back to list position -- that is the bug this module exists for.
    """
    get = record.get if hasattr(record, "get") else (lambda k, d=None: getattr(record, k, d))
    source = str(get("source_id", "") or get("source_name", "") or "")
    for key in ("source_ray_index", "ray_index"):
        value = get(key, None)
        if value is not None:
            return (source, int(value))
    launch = tuple(
        round(float(get(axis, 0.0) or 0.0), 9)
        for axis in ("source_x", "source_y", "source_z")
    )
    return (source, launch)


def select_smallest_k(
    items: Sequence[Any],
    cap: int | None,
    *,
    key: Callable[[Any], Any],
    seed: int = 0,
) -> list:
    """The ``cap`` items with the lowest identity hash, in their original order.

    Returns every item when ``cap`` is None or not binding. Order is preserved so
    the caller's downstream merge stays deterministic too.
    """
    items = list(items)
    if cap is None or len(items) <= int(cap):
        return items
    scored = sorted(range(len(items)), key=lambda i: (hash_identity(key(items[i]), seed), i))
    keep = set(scored[: int(cap)])
    return [item for i, item in enumerate(items) if i in keep]


def select_by_probability(
    items: Iterable[Any],
    probability: float,
    *,
    key: Callable[[Any], Any],
    seed: int = 0,
) -> list:
    """Every item whose identity hash falls under a FIXED threshold.

    Membership does not depend on the population at all, so two traces at different
    ray budgets agree on every ray they share.
    """
    p = min(max(float(probability), 0.0), 1.0)
    threshold = int(p * (_U32 + 1))
    return [item for item in items if hash_identity(key(item), seed) < threshold]


def subset_report(total: int, drawn: int, cap: int | None) -> str:
    """One line saying what the viewer is actually looking at."""
    if cap is None or total <= (cap or 0):
        return f"drawing all {total} rays"
    return (
        f"drawing {drawn} of {total} rays (identity-stable subset, seed-pinned): "
        f"the same rays appear across runs, and raising the budget does not reshuffle them"
    )
