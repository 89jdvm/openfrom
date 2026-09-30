import codecs
import json

from tools.check_public_safe import check_blob, PUBLIC_EMAIL


def r(s):
    return codecs.decode(s, "rot13")


def test_clean_code_passes():
    assert check_blob("a.py", b"print('hello')\n", []) == []


def test_public_email_allowed():
    assert check_blob("README.md", f"mail {PUBLIC_EMAIL}".encode(), []) == []


def test_other_email_fails():
    assert check_blob("README.md", ("x " + "someone" + "@" + "example.org").encode(), [])


def test_private_word_in_code_fails():
    assert check_blob("a.ts", r("fbzr qernz wbo").encode(), [])


def test_private_word_in_data_allowed():
    row = {"title": r("Lbhe qernz WQ ebyr")}
    assert check_blob("jobs.json", json.dumps(row).encode(), []) == []


def test_standalone_initials_in_code_fail_but_not_inside_words():
    assert check_blob("a.md", r("nfx WQ").encode(), [])
    assert check_blob("a.md", r("WQE nppbhag").encode(), []) == []


def test_long_string_in_json_fails():
    assert check_blob("jobs.json", json.dumps({"summary": "x" * 401}).encode(), [])
    assert check_blob("jobs.json", json.dumps({"summary": "x" * 400}).encode(), []) == []


def test_long_string_in_jsonl_fails():
    assert check_blob("s.jsonl", (json.dumps({"a": "y" * 500}) + "\n").encode(), [])


def test_private_key_in_data_fails():
    assert check_blob("x.json", json.dumps({r("sybbe"): 1}).encode(), [])


def test_env_and_size():
    assert check_blob(".env", b"A=1", [])
    assert check_blob("big.bin", b"0" * (5 * 1024 * 1024 + 1), [])


def test_phone_pattern():
    import re
    pat = re.compile(r"[\s().-]?".join("123456789"))
    assert check_blob("a.md", b"call 123 456 789", [pat])
