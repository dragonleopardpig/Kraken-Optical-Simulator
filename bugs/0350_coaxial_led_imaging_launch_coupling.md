# 0350 — Coaxial LED bounds the Object-plane imaging launch

Status: implemented and guarded.

## Problem

An enabled physical scene source historically drove the primary preview trace.
That is useful for source-to-detector and stray-light layouts, but it meant a
coaxial LED could replace the Object-driven imaging rays instead of illuminating
them. The existing effective-area heatmap correctly showed the folded footprint,
yet the imaging launch itself did not use that footprint.

## Opt-in contract

A live physical scene source may set `couple_to_imaging_launch: true` together
with a valid coaxial descriptor:

- `coaxial_illuminator: true`
- `coaxial_aperture_fold_mm`
- `coaxial_aperture_perp_mm`
- `coaxial_fold_angle_deg`
- `coaxial_fold_axis`

For a finite-object Open 3D editor preview, the source remains additive. When
its physical rays are needed, they are traced in an isolated illumination
keeper, while the primary imaging rays continue to originate at the Object
plane. Their X/Y field origins are bounded by the folded LED rectangle,
intersected with the configured finite field and the registered camera's
object-space FOV when available. The Object row's round display diameter is not
used as the rectangular FOV.

Removing the flag or setting it to false restores the existing uncoupled source
and field-launch behavior. A disabled/non-physical source, an invalid descriptor,
or an infinity object does not activate coupling.

`angular_weight: Cosine-weighted` with `cone_deg: 90.0` is the full
forward-hemisphere Lambertian emitter law. The angular distribution affects the
isolated physical LED trace; the descriptor supplies the imaging-launch
rectangle.

## MV-150 result

For the 55 × 74 mm side LED and a 45° fold,

```text
folded LED       = (55*cos(45°)) × 74
                 = 38.8909 × 74 mm
camera FOV       = 39 × 39 mm
launch rectangle = 38.8909 × 39 mm
```

The fold axis is therefore slightly under-filled while the perpendicular axis
remains camera-FOV limited, which is the expected two-edge relative-illumination
case.

## Verification

Run the focused coupling guard and the existing effective-area guard:

```bash
python -m KrakenOS.UI.validate_open3d_coaxial_imaging_launch
python -m KrakenOS.UI.validate_open3d_effective_illumination_area
```

The focused guard checks opt-in/opt-out recognition, the 55 × 74 mm at 45°
intersection, Object-plane launch origins, the rectangular field grid,
physical-source isolation, legacy restoration, and the 90° cosine-weighted
Lambertian sampler. When the MV-150 attachment is present it also traces a
reduced physical LED sample through the Uncoated cube entry face and requires
reflected branches to reach or cross the Object plane. The effective-area guard
independently checks the folded footprint and two-dark-edge detector overlay.
