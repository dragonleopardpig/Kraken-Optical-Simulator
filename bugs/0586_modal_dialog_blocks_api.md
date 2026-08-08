# 0586 — a modal dialog on a programmatic path (and the true story of 0579)

Found while resuming the camera half of the bugs/0579 sweep, which had never executed.

## What it is

Both vendor-folder importers ended their failure branch with a modal dialog:

```python
except Exception as exc:
    messagebox.showerror("Swap Imaging Lens", f"...{folder}\n\n{exc}", parent=parent)
    return None
```

Right for a user who picked a folder from the menu. Fatal for anyone calling the API with an
explicit folder: a modal with nobody to dismiss it waits **forever**. The camera path had a
second one, `_prompt_camera_flange_distance` (bugs/0309), which prompts when the datasheet lacks
the flange-to-sensor distance.

## It rewrites bugs/0579

bugs/0579 recorded four lens folders as "HANG the swap (900 s timeout each)" and reasoned toward
a slow datasheet-PDF parse, on the strength of a shared signature (no `.zmx`, no prescription
dump → the PDF route). **That was wrong.** Called directly, without a GUI, every one of them
*fails in 0.1–0.3 seconds*:

```
DCX                            0.3s  ValueError: surrogate needs a positive, finite effective focal length
DCV50mm                        0.1s  ValueError: ...
Aspherized_Achromatic_Lenses   0.2s  ValueError: ...
aspherized-achromatic-lenses   0.2s  ValueError: ...
ball_lens                      0.1s  ValueError: ...
cylinder_lens_rectangle        0.1s  ValueError: ...
15056                          0.8s  OK  Machine Vision 15056 1x
```

The 900 seconds were the dialog, not the parse. The diagnosis had been made from a timeout
without ever obtaining a stack — see the method note below.

## The camera half, unblocked

The same defect is why the sweep's six camera rows never ran. Direct import:

```
BC-GM25M12X1   no scrapeable SENSOR SIZE   -> declines
BC-GM25M12X4   no scrapeable SENSOR SIZE   -> declines
BC-GM65M12X4 / BC-OM25M / hr25MCX / shr661MCX12  -> import fine
```

Declining is defensible: an EFL or a sensor size cannot be invented. Hanging is not.

## Fix

`_report_folder_import_failure(title, message, parent, *, interactive)` — always records to the
debug log and the status bar; shows the modal **only when interactive**. `interactive` is decided
by the caller from whether *it* opened the folder dialog, and the discriminator is exact by
construction: every GUI entry point calls these with **no** `folder` and lets `askdirectory`
supply one, so an explicitly-passed folder is a programmatic call. The flange prompt is skipped
the same way, leaving the record exactly as a user pressing Cancel would.

## Measured after

```
probe: RETURNED None
probe: status 'Import Vendor Camera: Could not extract a sensor size from this folder...'
probe: camera body bounds [144.788, 214.788, -35.0, 35.0, -65.499, 8.131]   (unchanged)
```

A declined swap now returns promptly, says why, and leaves the scene untouched. The six camera
rows then ran for the first time (lens PYRITE 45-85, solve 23×23):

| camera | lens swap | attach (solve) | rays b/s/a | sensorZ |
|---|---|---|---|---|
| BC-GM25M12X1 | ok | 0.0000 | 170/170/40 | −40.38 |
| BC-GM25M12X4 | ok | 0.0000 | 170/170/40 | −40.38 |
| BC-GM65M12X4 | ok | 0.0000 | 170/80/58 | +36.92 |
| BC-OM25M | ok | 0.0000 | 170/114/36 | −58.12 |
| hr25MCX | ok | 0.0000 | 170/85/32 | −87.03 |
| shr661MCX12 | ok | 0.0000 | 170/47/17 | +3.42 |

bugs/0574's body carry holds across every camera change, no runaway, every solve applies. The
two `170/170` rows are the declines — the camera never changed — which the harness now records
explicitly (`camera_swap: declined`) rather than reporting as a swap that happened.

## Method note, worth more than the fix

The hang was diagnosed twice from a timeout and twice wrongly. What worked:
`faulthandler.dump_traceback_later(deadline, exit=True)` inside the probe, so the process dumps
its **own** stack and dies — no signalling. Two attempts to `kill -USR1` the child hit the wrong
PID, because `xvfb-run`'s process tree puts a wrapper between `pgrep` and the interpreter, and one
of those attempts used a `pkill -f "Xvfb :"` broad enough to have killed an unrelated 2.5 h
marathon's display. **Never diagnose a hang without a stack, and let the process dump its own.**

## Open

- The two sensor-size-less cameras and six EFL-less lens folders decline correctly but silently
  from the user's point of view (status bar only). A prompt like the flange one — "enter the
  sensor size / EFL" — would turn six declines into six usable folders. Feature, not defect.
- Ray counts fall after the solve on every camera (170 → 17…58). Same pattern the lens sweep
  found; decide it by termination reason (`aperture_stop_vignette` = honest vignetting vs
  `no_next_intersection` = geometry missing the sensor), not by the count.
