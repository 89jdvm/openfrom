from tools.common import clean_summary, short_summary


def test_heading_words_are_removed():
    assert clean_summary("Key Responsibilities In-depth secondary research on markets and competitors").startswith("In-depth")
    assert clean_summary("Job description: The Centre of Excellence works with county governments on water").startswith("The Centre")


def test_title_case_heading_run_is_dropped():
    s = clean_summary("ESG Advisory & Technical Leadership Provide expert guidance on ESG standards for clients")
    assert s.startswith("Provide expert guidance")


def test_fragment_start_skips_to_next_sentence_or_drops():
    s = clean_summary("and the types of tasks involved. Decision-oriented analysis that lets funders make better calls")
    assert s.startswith("Decision-oriented")
    assert clean_summary("and then nothing clean follows here at all") == ""


def test_short_summary_strips_contacts_and_caps_length():
    at = "@"
    s = short_summary("Write to jobs" + at + "example.org or see https://example.org/apply. " + "Lead research on markets. " * 20)
    assert at not in s and "http" not in s and len(s) <= 200
