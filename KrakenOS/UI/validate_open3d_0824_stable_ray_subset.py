"""Guard for bugs/0824 -- which rays get drawn depends on the ray, not on its position.

`source_illumination_rays_overlay._subsample` picked with
``rng.choice(len(polylines), cap, replace=False)``, over LIST POSITIONS. Its comment
called that "deterministic (seeded)", and for one fixed list it is. Across runs it is
not: anything that changes the list -- a different ray budget, a role tag that now
matches, one more ray clipping short, or merely a different order out of the splitter
-- re-rolls every ray on screen. That is the one code path a user reaches for when
they need to know where stray light came from, and two runs of it could not be
compared.

Selection is now a pure function of (ray identity, seed). What that does and does not
buy is worth stating exactly, because overclaiming here would be its own bug:

  * ORDER-independent -- shuffle the input, get the same set. This is the real fix.
  * Free of upstream RNG coupling -- nothing that draws random numbers first can
    shift the overlay.
  * Reproducible at a fixed population.
  * NOT population-independent, for the smallest-k policy: growing the population
    tightens which hashes win. `select_by_probability` is the policy for comparing
    two runs at different ray budgets, and it IS population-independent.

Checks (display-free, pure):
  A  the hash avalanches and spreads -- adjacent ray indices do not land adjacent;
  B  the same population selects the same set, every time;
  C  ORDER-independence -- a shuffled input gives an identical set (the positional
     draw does not, and the contrast is asserted so the point cannot rot);
  D  no coupling to any upstream RNG;
  E  select_by_probability is fully population-independent, in both directions;
  F  ray_identity prefers the engine index, falls back to the launch point, and
     distinguishes the same index under different sources;
  G  the overlay caps by identity and consults NO random number generator;
  H  degradation: empty input, cap None, cap not binding, output order preserved.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0824_stable_ray_subset
"""

from __future__ import annotations

import random


def _recs(n: int, source: str = "S1", start: int = 0):
    return [{"source_id": source, "ray_index": i} for i in range(start, start + n)]


def _key(record):
    return (record["source_id"], record["ray_index"])


def _idx(selected):
    return [r["ray_index"] for r in selected]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    import numpy as np

    from KrakenOS.UI.services import source_illumination_rays_overlay as sir
    from KrakenOS.UI.services.stable_ray_subset import (
        hash_identity,
        ray_identity,
        select_by_probability,
        select_smallest_k,
        subset_report,
    )

    # ---- A: the hash avalanches -----------------------------------------------------------------
    hashes = [hash_identity(("S1", i), 7) for i in range(4096)]
    ok(len(set(hashes)) == len(hashes), "A1: 4096 adjacent identities hash without collision")
    neighbours = [abs(hashes[i + 1] - hashes[i]) for i in range(len(hashes) - 1)]
    ok(min(neighbours) > 0 and sum(neighbours) / len(neighbours) > 2**29,
       "A2: adjacent indices land far apart -- a subset is not a contiguous block")
    quarters = [0, 0, 0, 0]
    for h in hashes:
        quarters[min(h // (2**30), 3)] += 1
    ok(all(800 < q < 1300 for q in quarters),
       f"A3: the hash spreads roughly uniformly across the range (quarters {quarters})")
    ok(hash_identity(("S1", 5), 7) != hash_identity(("S1", 5), 8),
       "A4: the seed actually moves the hash")

    # ---- B: reproducible at a fixed population --------------------------------------------------
    pop = _recs(1000)
    first = _idx(select_smallest_k(pop, 50, key=_key, seed=7))
    ok(len(first) == 50, f"B1: the cap is exact (got {len(first)})")
    ok(all(_idx(select_smallest_k(pop, 50, key=_key, seed=7)) == first for _ in range(3)),
       "B2: repeated selection over the same population is byte-identical")

    # ---- C: ORDER-independence, and the contrast that motivates it -------------------------------
    shuffled = list(pop)
    random.Random(1234).shuffle(shuffled)
    ok(set(_idx(select_smallest_k(shuffled, 50, key=_key, seed=7))) == set(first),
       "C1: a shuffled input selects the SAME set -- position no longer decides")
    # What the old positional draw does with the same shuffle, asserted so this stays true:
    rng_a = np.random.default_rng(7)
    rng_b = np.random.default_rng(7)
    pos_a = {pop[i]["ray_index"] for i in rng_a.choice(len(pop), 50, replace=False)}
    pos_b = {shuffled[i]["ray_index"] for i in rng_b.choice(len(shuffled), 50, replace=False)}
    ok(pos_a != pos_b,
       "C2: the positional draw it replaced gives a DIFFERENT set on the same shuffle")
    ok(len(pos_a & pos_b) < 10,
       f"C3: and the overlap is near-nothing, not a near-miss (got {len(pos_a & pos_b)}/50)")

    # ---- D: no coupling to an upstream RNG -------------------------------------------------------
    np.random.default_rng(99).random(1000)
    random.random()
    ok(_idx(select_smallest_k(pop, 50, key=_key, seed=7)) == first,
       "D1: consuming other random numbers first cannot shift the selection")

    # ---- E: fixed-threshold selection is population-independent ----------------------------------
    big = select_by_probability(_recs(4000), 0.05, key=_key, seed=7)
    small = select_by_probability(_recs(1000), 0.05, key=_key, seed=7)
    big_set, small_set = set(_idx(big)), set(_idx(small))
    ok(small_set == {i for i in big_set if i < 1000},
       "E1: the smaller population's set is exactly the big one restricted to its range")
    ok(all(i in big_set for i in small_set),
       "E2: no ray flips OUT when the population grows")
    ok(0.03 < len(big) / 4000 < 0.07,
       f"E3: the realised fraction tracks the requested probability (got {len(big)/4000:.3f})")

    # ---- F: ray identity ------------------------------------------------------------------------
    ok(ray_identity({"source_id": "S1", "source_ray_index": 12, "ray_index": 99}) == ("S1", 12),
       "F1: the engine's source_ray_index wins over a bare ray_index")
    ok(ray_identity({"source_id": "S1", "ray_index": 12}) == ("S1", 12),
       "F2: ray_index is used when source_ray_index is absent")
    launch = ray_identity({"source_id": "S1", "source_x": 1.5, "source_y": -2.0, "source_z": 3.0})
    ok(launch == ("S1", (1.5, -2.0, 3.0)),
       f"F3: with no index at all the launch point is the identity (got {launch})")
    ok(ray_identity({"source_id": "A", "ray_index": 1}) != ray_identity({"source_id": "B", "ray_index": 1}),
       "F4: the same index under two sources are different rays")
    ok(hash_identity(("A", 1), 7) != hash_identity(("B", 1), 7),
       "F5: and they hash apart, so one source cannot crowd out the other")

    # ---- G: the overlay is wired to it, and draws no random numbers ------------------------------
    source = __import__("pathlib").Path(sir.__file__).read_text()
    ok("default_rng" not in source and "rng.choice" not in source,
       "G1: the overlay module consults no RNG at all any more")
    ok("stable_ray_subset" in source and "ray_identity" in source,
       "G2: it caps through the identity-stable selector")
    pairs = [({"source_id": "S1", "ray_index": i}, np.zeros((2, 3))) for i in range(500)]
    drawn = sir._subsample(pairs, 40, 7, key=lambda p: ray_identity(p[0]))
    ok(len(drawn) == 40, f"G3: the overlay cap is exact (got {len(drawn)})")
    ok([p[0]["ray_index"] for p in drawn] == sorted(p[0]["ray_index"] for p in drawn),
       "G4: and the drawn set keeps input order, so the merged geometry stays stable")

    # ---- H: degradation --------------------------------------------------------------------------
    ok(select_smallest_k([], 10, key=_key, seed=7) == [], "H1: empty input returns empty")
    ok(len(select_smallest_k(pop, None, key=_key, seed=7)) == 1000,
       "H2: cap None draws everything")
    ok(len(select_smallest_k(pop, 5000, key=_key, seed=7)) == 1000,
       "H3: a cap above the population draws everything, not an error")
    ok(_idx(select_smallest_k(pop, 50, key=_key, seed=7)) == sorted(first),
       "H4: output preserves input order rather than hash order")
    ok("identity-stable" in subset_report(60000, 240, 240) and "all 12 rays" in subset_report(12, 12, 240),
       "H5: the report says what is on screen in both the capped and uncapped cases")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0824 stable-ray-subset validation PASSED")
        return 0
    print("0824 stable-ray-subset validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
