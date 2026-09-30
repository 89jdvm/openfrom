from tools.seed_from_pocket import ALLOWED, project


def _posting():
    return {
        "uid": "lever:acme:1", "source": "lever", "title": "Programme Officer", "company": "Acme",
        "location": "Remote", "countries": [], "remote": True, "remote_scope": "worldwide",
        "posted": "2026-09-01", "deadline": None, "url": "https://example.org/1",
        "salary_min": 1, "salary_max": 2, "salary_currency": "USD", "salary_period": "year",
        "description": "synthetic text", "tags": ["x"], "extra": {"a": 1},
        "pay_2k": True, "floor": None, "ecuador_open": True, "reasoning": "x",
    }


def _labels():
    return {"labels": {"role_family": "X1", "industry": "I13", "seniority": "MID",
                       "engagement": "PERM", "employer_type": "COMPANY", "how": "vote",
                       "named_problem": "secret", "must_haves": ["a"], "open_to_ecuador": "YES"},
            "facts": {"where_text": "secret", "signals": ["s"]}}


def test_output_keys_equal_allow_list():
    row = project(_posting(), _labels())
    assert list(row) == ALLOWED


def test_out_codes_renamed_and_private_fields_dropped():
    row = project(_posting(), _labels())
    assert row["role_family"] == "R26"
    for k in ("description", "extra", "pay_2k", "floor", "ecuador_open", "reasoning",
              "named_problem", "must_haves", "where_text", "signals"):
        assert k not in row


def test_unlabelled_posting_has_null_labels():
    row = project(_posting(), None)
    assert list(row) == ALLOWED and row["role_family"] is None
