# KrakenOS Sphinx documentation

The Sphinx source lives in `docs/source`.

Build locally:

```bash
python -m pip install -r docs/requirements.txt
make -C docs html
```

The converted provisional manual starts at `docs/source/manual/index.rst`.
The source PDF is retained at `KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf`.
