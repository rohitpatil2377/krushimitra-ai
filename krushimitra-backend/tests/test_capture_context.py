"""The field context is what makes a saved photo a training example.

These tests guard the one part of the pipeline that cannot be repaired in hindsight: a photo
stored without a split group can never be held out honestly, so any accuracy measured on it is
measuring the model against plants it has already seen.
"""
import base64
from datetime import date


import json  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.capture import COORD_DP, normalize_context, stats  # noqa: E402

client = TestClient(app)


# --- normalize_context --------------------------------------------------------------------

def test_no_context_is_not_splittable():
    out = normalize_context(None)
    assert out["context"] == {}
    assert out["split_group"] is None
    assert out["split_group_source"] is None


def test_plot_beats_farmer_as_split_group():
    """Two plots of one farmer are different fields; one plot over weeks is the same plant."""
    out = normalize_context({"farmer_id": "f1", "plot_id": "p1"})
    assert out["split_group"] == "plot:p1"
    assert out["split_group_source"] == "plot"


def test_farmer_is_the_fallback_group():
    out = normalize_context({"farmer_id": "f1"})
    assert out["split_group"] == "farmer:f1"
    assert out["split_group_source"] == "farmer"


def test_days_after_sowing_is_derived():
    out = normalize_context(
        {"sowing_date": "2026-09-01"}, captured_on=date(2026, 11, 13)
    )
    assert out["context"]["days_after_sowing"] == 73
    assert out["context"]["sowing_date"] == "2026-09-01"


def test_future_sowing_date_drops_the_derived_age():
    """A wrong phone clock must not become a negative crop stage in the training data."""
    out = normalize_context(
        {"sowing_date": "2027-01-01"}, captured_on=date(2026, 11, 13)
    )
    assert "days_after_sowing" not in out["context"]
    assert out["context"]["sowing_date"] == "2027-01-01"  # kept, so it can be audited


def test_unparseable_sowing_date_does_not_crash():
    out = normalize_context({"sowing_date": "last diwali"})
    assert "sowing_date" not in out["context"]
    assert "days_after_sowing" not in out["context"]


def test_coordinates_are_rounded_for_privacy():
    """Precision we never store cannot later leak. ~100 m locates a village, not a house."""
    out = normalize_context({"lat": 19.9974533, "lon": 73.7898009})
    assert out["context"]["lat"] == round(19.9974533, COORD_DP)
    assert out["context"]["lon"] == round(73.7898009, COORD_DP)
    assert len(str(out["context"]["lat"]).split(".")[1]) <= COORD_DP


def test_blank_strings_are_dropped_not_stored():
    out = normalize_context({"district": "   ", "taluka": "Niphad", "farmer_id": ""})
    assert "district" not in out["context"]
    assert out["context"]["taluka"] == "Niphad"
    assert out["split_group"] is None


# --- end to end ---------------------------------------------------------------------------

def _diagnose(tmp_path, context):
    payload = {"image_base64": base64.b64encode(b"fake-bytes").decode(), "crop": "onion"}
    if context is not None:
        payload["context"] = context
    r = client.post("/vision/diagnose", json=payload)
    assert r.status_code == 200
    return r.json()


def test_context_reaches_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "capture_dir", str(tmp_path))
    body = _diagnose(tmp_path, {
        "farmer_id": "install-abc",
        "plot_id": "plot-1",
        "district": "Nashik",
        "sowing_date": "2026-09-01",
        "device_model": "Redmi 9A",
        "app_version": "0.2.0",
    })
    assert body["diagnosis_id"]

    records = [p for p in tmp_path.rglob("*.json") if not p.name.endswith(".feedback.json")]
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["split_group"] == "plot:plot-1"
    assert record["context"]["district"] == "Nashik"
    assert record["context"]["device_model"] == "Redmi 9A"
    assert record["context"]["days_after_sowing"] >= 0
    # The diagnosis itself is unchanged by the context.
    assert record["predicted_slug"]


def test_older_app_build_still_works(tmp_path, monkeypatch):
    """No context field at all: the farmer still gets a diagnosis, the dataset is just poorer."""
    monkeypatch.setattr(settings, "capture_dir", str(tmp_path))
    body = _diagnose(tmp_path, None)
    assert body["diagnosis_id"]
    records = [p for p in tmp_path.rglob("*.json") if not p.name.endswith(".feedback.json")]
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["split_group"] is None


def test_stats_counts_what_is_trainable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "capture_dir", str(tmp_path))
    _diagnose(tmp_path, {"plot_id": "p1", "farmer_id": "f1"})
    _diagnose(tmp_path, {"plot_id": "p1", "farmer_id": "f1"})   # same plant, same group
    _diagnose(tmp_path, {"plot_id": "p2", "farmer_id": "f1"})
    _diagnose(tmp_path, None)                                    # the one that cannot be split

    s = stats()
    assert s["captured"] == 4
    assert s["splittable"] == 3
    assert s["not_splittable"] == 1
    assert s["distinct_plots"] == 2
    assert s["distinct_farmers"] == 1
