"""Hand-written cases for who_can_apply (40 at M3, more added since). All text is synthetic."""
import pytest

from tools.who_can_apply import open_to, who_can_apply


def job(location="", text="", remote=True, countries=None, scope=None, title="Programme Officer"):
    return {"title": title, "location": location, "description": text, "remote": remote,
            "countries": countries or [], "remote_scope": scope}


CASES = [
    # (job, country, expected)
    (job("Worldwide", scope="worldwide"), "KE", "yes"),
    (job("Anywhere in the world"), "EC", "yes"),
    (job("Remote", "You can work from anywhere."), "CO", "yes"),
    (job("Remote"), "KE", "unknown"),
    (job("Remote - US"), "US", "yes"),
    (job("Remote - US"), "CO", "no"),
    (job("Austin, TX (Remote)"), "US", "yes"),
    (job("Austin, TX (Remote)"), "DE", "no"),
    (job("Worldwide", "Candidates must be based in the United States.", scope="worldwide"), "KE", "no"),
    (job("Worldwide", "Candidates must be based in the United States.", scope="worldwide"), "US", "yes"),
    (job("Remote", "You must be legally authorized to work in the UK."), "GB", "yes"),
    (job("Remote", "You must be legally authorized to work in the UK."), "IE", "no"),
    (job("Remote", "We are only hiring in Canada and Mexico at this time."), "MX", "yes"),
    (job("Remote", "We are only hiring in Canada and Mexico at this time."), "US", "no"),
    (job("LATAM"), "EC", "yes"),
    (job("LATAM"), "US", "no"),
    (job("Remote (EMEA)"), "KE", "yes"),
    (job("Remote (EMEA)"), "BR", "no"),
    (job("Remote", "This role is open to candidates based in Europe."), "DE", "yes"),
    (job("Remote", "This role is open to candidates based in Europe."), "KE", "no"),
    (job("Remote", "Debes residir en Colombia para aplicar."), "CO", "yes"),
    (job("Remote", "Debes residir en Colombia para aplicar."), "EC", "no"),
    (job("Remoto", "Solo para candidatos residentes en México."), "MX", "yes"),
    (job("Remoto", "Se requiere permiso de trabajo en España."), "ES", "yes"),
    (job("Remoto", "Se requiere permiso de trabajo en España."), "AR", "no"),
    (job("Worldwide", "Must overlap with EST working hours.", scope="worldwide"), "CO", "yes"),
    (job("Worldwide", "Must overlap with EST working hours.", scope="worldwide"), "KE", "no"),
    (job("Worldwide", "Working hours: CET time zone.", scope="worldwide"), "KE", "yes"),
    (job("Worldwide", "Working hours: CET time zone.", scope="worldwide"), "PH", "no"),
    (job("Remote", "Availability between UTC-3 and UTC+3 is required."), "KE", "yes"),
    (job("Remote", "Availability between UTC-3 and UTC+3 is required."), "IN", "no"),
    (job("Worldwide", "This is a W2 position only.", scope="worldwide"), "KE", "unclear"),
    (job("Berlin", remote=False), "DE", "no"),
    (job("Remote", "We are a US-based company with a global team. Work from anywhere."), "KE", "yes"),
    (job("Remote - US only"), "CA", "no"),
    (job("Remote, UK-based"), "GB", "yes"),
    (job("", "", remote=None, title="Remote Data Analyst (LATAM)"), "PE", "yes"),
    (job("Kenya, Uganda, Tanzania (home-based)", remote=None), "KE", "yes"),
    (job("Kenya, Uganda, Tanzania (home-based)", remote=None), "NG", "no"),
    (job("Remote", countries=["BR", "AR"]), "BR", "yes"),
    (job("Atlanta, GA - Hybrid; Denver, CO - Hybrid; New York, NY"), "CO", "no"),
    (job("Atlanta, GA - Hybrid; Denver, CO - Hybrid; New York, NY"), "US", "yes"),
    (job("Denver, CO (Remote)"), "CO", "no"),
    (job("Bogotá, CO (Remote)"), "CO", "yes"),
    (job("Remote - Berlin, DE"), "DE", "yes"),
]


def test_forty_cases():
    assert len(CASES) >= 40


@pytest.mark.parametrize("j,country,expected", CASES)
def test_case(j, country, expected):
    assert open_to(who_can_apply(j), country) == expected, who_can_apply(j)


def test_en_dash_offsets_parse():
    from tools.who_can_apply import text_utc
    assert text_utc("Working hours: UTC–8 to UTC–5.") == text_utc("Working hours: UTC-8 to UTC-5.")
    assert text_utc("Overlap with GMT−3 is required.") == text_utc("Overlap with GMT-3 is required.")
    assert text_utc("Working hours: UTC-8 to UTC-5.")[0] < -5
