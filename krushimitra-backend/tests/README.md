# Vision pipeline tests

Verifies that `/vision/diagnose` is honest: advice follows the **detected disease** (not the
crop), low confidence **abstains** with no treatment and no severity, sample data is **badged**,
and every photo is **captured** with the farmer's correction.

The stub stands in for the self-hosted model, so this runs with no GPU and no API key.

```bash
# terminal 1 — fake vision model
.venv/bin/python -m uvicorn tests.stub_vlm:app --port 8077 --log-level error

# terminal 2 — the 24 checks
PYTHONPATH=. .venv/bin/python tests/test_vision_pipeline.py /tmp/krushi-test
```

Exits non-zero if any check fails. Run it after changing `labels.py`, `knowledge.py`,
`selfhosted.py` or the abstain gate in `api/vision.py`.
