"""Auth + Digital Crop Twin, end to end.

The flow a real farmer walks: log in with a phone, add a plot, start a crop cycle, record what
happened to it, and get back a health score that explains itself. Ownership isolation is tested
explicitly because this is the first feature where one farmer's data could leak into another's.
"""
from datetime import date, timedelta


from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import create_all  # noqa: E402
from app.main import app  # noqa: E402

create_all()
client = TestClient(app)

DEV_OTP = "123456"


def login(phone: str = "9890011223") -> dict:
    client.post("/auth/otp/request", json={"phone": phone})
    r = client.post("/auth/otp/verify", json={"phone": phone, "otp": DEV_OTP})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- auth ---------------------------------------------------------------------------------

def test_otp_request_never_pretends_an_sms_was_sent():
    """No provider is wired, so claiming 'check your SMS' would be a lie the farmer acts on."""
    r = client.post("/auth/otp/request", json={"phone": "9890011223"})
    assert r.status_code == 200
    body = r.json()
    assert body["sent"] is False
    assert body["otp_is_real"] is False
    assert body["dev_otp"] == DEV_OTP


def test_phone_numbers_normalise_to_one_account():
    """+91 / 0 / spaces must not create three accounts for one farmer."""
    ids = set()
    for raw in ("9876543210", "+919876543210", "09876543210", "98765 43210"):
        r = client.post("/auth/otp/verify", json={"phone": raw, "otp": DEV_OTP})
        assert r.status_code == 200, raw
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        ids.add(client.get("/auth/me", headers=h).json()["id"])
    assert len(ids) == 1, f"one farmer should have one account, got {ids}"


def test_bad_phone_and_bad_otp_are_rejected():
    assert client.post("/auth/otp/verify", json={"phone": "12345", "otp": DEV_OTP}).status_code == 422
    assert client.post("/auth/otp/verify", json={"phone": "9890011223", "otp": "000000"}).status_code == 401


def test_protected_routes_need_a_token():
    assert client.get("/farms").status_code in (401, 403)
    assert client.get("/crop-cycles").status_code in (401, 403)


def test_profile_update_and_device_linking():
    h = login("9811111111")
    r = client.patch("/auth/me", headers=h, json={
        "name": "रोहित", "village": "निफाड", "district": "Nashik", "device_id": "install-aaa",
    })
    assert r.status_code == 200
    assert r.json()["name"] == "रोहित"

    # A second farmer must not be able to steal the first one's captures by claiming the id.
    h2 = login("9822222222")
    client.patch("/auth/me", headers=h2, json={"device_id": "install-aaa"})
    me2 = client.get("/auth/me", headers=h2).json()
    assert me2["id"] != client.get("/auth/me", headers=h).json()["id"]


# --- plots ---------------------------------------------------------------------------------

def test_plot_stores_the_facts_every_screen_used_to_re_ask():
    h = login("9833333333")
    r = client.post("/farms", headers=h, json={
        "name": "मळा १", "district": "Nashik", "area_acres": 2.5,
        "soil": "medium", "irrigation_method": "drip",
        "row_spacing_m": 0.15, "plant_spacing_m": 0.10,
    })
    assert r.status_code == 201, r.text
    farm = r.json()
    assert farm["soil"] == "medium" and farm["irrigation_method"] == "drip"
    assert any(p["id"] == farm["id"] for p in client.get("/farms", headers=h).json())


def test_one_farmer_cannot_see_or_touch_another_farmers_plot():
    a = login("9844444444")
    b = login("9855555555")
    farm = client.post("/farms", headers=a, json={"name": "A's plot"}).json()
    assert client.get(f"/farms/{farm['id']}", headers=b).status_code == 404
    assert client.patch(f"/farms/{farm['id']}", headers=b, json={"name": "hijacked"}).status_code == 404
    assert client.delete(f"/farms/{farm['id']}", headers=b).status_code == 404


def test_invalid_soil_or_method_is_rejected():
    h = login("9866666666")
    assert client.post("/farms", headers=h, json={"soil": "chocolate"}).status_code == 422
    assert client.post("/farms", headers=h, json={"irrigation_method": "hose"}).status_code == 422


# --- the twin ------------------------------------------------------------------------------

def _farm_and_cycle(h, days_ago=60, crop="onion"):
    farm = client.post("/farms", headers=h, json={
        "name": "plot", "district": "Nashik", "soil": "medium", "irrigation_method": "drip",
    }).json()
    r = client.post("/crop-cycles", headers=h, json={
        "farm_id": farm["id"], "crop": crop,
        "sowing_date": (date.today() - timedelta(days=days_ago)).isoformat(),
    })
    assert r.status_code == 201, r.text
    return farm, r.json()


def test_cycle_knows_its_stage_without_being_told():
    """The whole point: the AI stops asking what it already knows."""
    h = login("9877777777")
    _, cycle = _farm_and_cycle(h, days_ago=60)
    assert cycle["stage"]["days_after_sowing"] == 60
    assert cycle["stage"]["stage"] == "mid"
    assert cycle["stage"]["progress_pct"] == 50
    assert cycle["stage"]["stage_mr"]


def test_a_new_cycle_starts_at_full_health_but_says_why():
    h = login("9888888888")
    _, cycle = _farm_and_cycle(h)
    assert cycle["health"]["score"] == 100
    assert cycle["health"]["items"] == []
    # "nothing recorded" must not be presented as "healthy"
    assert "निरोगी आहे असा नाही" in cycle["health"]["note"]


def test_sowing_appears_on_the_timeline_immediately():
    h = login("9899999999")
    _, cycle = _farm_and_cycle(h)
    events = client.get(f"/crop-cycles/{cycle['id']}/timeline", headers=h).json()
    assert [e["type"] for e in events] == ["sowing"]
    assert events[0]["day_index"] == 0


def test_a_diagnosis_lowers_health_and_the_score_itemises_why():
    h = login("9700000001")
    _, cycle = _farm_and_cycle(h)
    client.post(f"/crop-cycles/{cycle['id']}/events", headers=h, json={
        "type": "diagnosis", "title": "करपा",
        "data": {"severity_level": "severe", "disease_slug": "onion_purple_blotch"},
    })
    health = client.get(f"/crop-cycles/{cycle['id']}/health-score", headers=h).json()
    assert health["score"] < 100
    assert health["items"], "a score with no breakdown is a number nobody can check"
    assert health["items"][0]["reason"] == "onion_purple_blotch"
    assert health["band"] in ("good", "fair", "poor", "critical")


def test_an_abstained_diagnosis_does_not_punish_the_farmer():
    """Our uncertainty is not their crop's problem."""
    h = login("9700000002")
    _, cycle = _farm_and_cycle(h)
    client.post(f"/crop-cycles/{cycle['id']}/events", headers=h, json={
        "type": "diagnosis", "data": {"severity_level": None, "disease_slug": "unknown"},
    })
    assert client.get(f"/crop-cycles/{cycle['id']}/health-score", headers=h).json()["score"] == 100


def test_old_problems_fade_but_incurable_ones_linger():
    h = login("9700000003")
    _, a = _farm_and_cycle(h)
    _, b = _farm_and_cycle(h)
    old = (date.today() - timedelta(days=25)).isoformat()
    client.post(f"/crop-cycles/{a['id']}/events", headers=h, json={
        "type": "diagnosis", "on": old,
        "data": {"on": old, "severity_level": "severe", "disease_slug": "onion_purple_blotch"},
    })
    client.post(f"/crop-cycles/{b['id']}/events", headers=h, json={
        "type": "diagnosis", "on": old,
        "data": {"on": old, "severity_level": "severe", "disease_slug": "onion_iris_yellow_spot_virus"},
    })
    curable = client.get(f"/crop-cycles/{a['id']}/health-score", headers=h).json()["score"]
    incurable = client.get(f"/crop-cycles/{b['id']}/health-score", headers=h).json()["score"]
    assert curable > incurable, "a virus does not heal because a month passed"


def test_logging_irrigation_updates_the_cycle_so_it_is_not_asked_twice():
    h = login("9700000004")
    _, cycle = _farm_and_cycle(h)
    today = date.today().isoformat()
    client.post(f"/crop-cycles/{cycle['id']}/events", headers=h, json={
        "type": "irrigation", "on": today, "data": {"mm": 12},
    })
    assert client.get(f"/crop-cycles/{cycle['id']}", headers=h).json()["last_watered_date"] == today


def test_harvest_closes_the_season_and_lands_on_the_timeline():
    h = login("9700000005")
    _, cycle = _farm_and_cycle(h)
    r = client.patch(f"/crop-cycles/{cycle['id']}", headers=h, json={
        "status": "harvested", "yield_quintal": 180,
    })
    assert r.status_code == 200
    assert r.json()["status"] == "harvested" and r.json()["harvest_date"]
    types = [e["type"] for e in client.get(f"/crop-cycles/{cycle['id']}/timeline", headers=h).json()]
    assert "harvest" in types


def test_future_dates_are_refused():
    h = login("9700000006")
    farm = client.post("/farms", headers=h, json={"name": "p"}).json()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = client.post("/crop-cycles", headers=h, json={
        "farm_id": farm["id"], "crop": "onion", "sowing_date": tomorrow,
    })
    assert r.status_code == 400


def test_unsupported_crop_is_refused():
    h = login("9700000007")
    farm = client.post("/farms", headers=h, json={"name": "p"}).json()
    r = client.post("/crop-cycles", headers=h, json={"farm_id": farm["id"], "crop": "wheat"})
    assert r.status_code == 400


def test_one_farmer_cannot_read_anothers_cycle():
    a = login("9700000008")
    b = login("9700000009")
    _, cycle = _farm_and_cycle(a)
    assert client.get(f"/crop-cycles/{cycle['id']}", headers=b).status_code == 404
    assert client.get(f"/crop-cycles/{cycle['id']}/timeline", headers=b).status_code == 404
    assert client.post(f"/crop-cycles/{cycle['id']}/events", headers=b,
                       json={"type": "note", "body": "x"}).status_code == 404
    assert client.get("/crop-cycles", headers=b).json() == []


def test_a_plot_with_history_is_not_silently_destroyed():
    h = login("9700000010")
    farm, _ = _farm_and_cycle(h)
    assert client.delete(f"/farms/{farm['id']}", headers=h).status_code == 409
