# 0679 — VTK XML errors at app launch: the mesh-cache reader raced its writer

User launch log: `vtkXMLPolyDataReader` "no element found" on
`cad_cache/prism_assembly_chunk_armA_*.analytic.v2.vtp` -- with the failing BYTE
INDEX GROWING between retries (67093 -> 85326 -> 126826): the reader was parsing
the .vtp WHILE it was being written. First-launch cache build on a fresh key (the
0677 wire step re-extracted the chunk STEP every run, bumping the mtime that keys
the cache). Self-healing (the reader unlinks and rebuilds), but noisy and racy.

Fixes:
1. `mesh.save` for the analytic display cache now writes to a temp file and
   `os.replace`s it -- atomic like the neighbouring pickle cache already was.
2. `extract_chunk_armA` reuses the existing STEP instead of re-extracting
   (stable mtime -> stable cache key -> no per-run rebuild).

The cache file on disk is complete; a relaunch loads clean.
