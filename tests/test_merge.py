from datetime import date

from tools.merge import dedupe, key


def row(uid, source, org="Planet Labs", title="Solutions Architect", also=None, posted="2026-09-20"):
    return {"uid": uid, "source": source, "organization": org, "title": title, "url": "https://example.org/" + uid,
            "posted": posted, "deadline": None, "first_seen": posted, "also": also,
            "w": {"scope": "worldwide", "countries": [], "regions": [], "utc": None}}


def test_same_job_on_two_boards_is_one_row():
    assert key(row("a", "pcdn", org="Planet")) == key(row("b", "greenhouse"))


def test_employer_board_wins_and_state_rows_with_null_also_work():
    old = row("old:1", "himalayas", also=None)          # as restored from the state
    new = row("gh:1", "greenhouse")
    out = dedupe([old, new], {"old:1"}, date(2026, 9, 30))
    assert len(out) == 1 and out[0]["source"] == "greenhouse" and out[0]["also"] == ["himalayas"]


def test_old_jobs_drop_out_after_60_days():
    out = dedupe([row("x", "himalayas", posted="2026-07-01")], set(), date(2026, 9, 30))
    assert out == []
