"""The text each job is embedded from: "passage: " + title + organisation + 1,500
characters of the ad, starting at a responsibilities or requirements heading when
the ad has one (company blurbs at the top say little about the work)."""
from __future__ import annotations

import re

AD_CHARS = 1500
_HEADING = re.compile(
    r"(?im)^\W{0,3}("
    r"(key |main |your |core |job |principal )?(responsibilities|duties|tasks)"
    r"|what you('| wi)ll (do|be doing)|the role|about the role|role description|job description"
    r"|your (role|mission|impact)|in this role|what we('re| are) looking for|requirements"
    r"|qualifications|who you are"
    r"|responsabilidades|funciones|tareas|requisitos|perfil( buscado)?|descripci[oó]n del (puesto|cargo)"
    r"|qu[eé] har[aá]s|tu rol|aufgaben|ihre aufgaben|deine aufgaben|missions?|vos missions"
    r")\b"
)


def ad_window(description: str, chars: int = AD_CHARS) -> str:
    d = description or ""
    m = _HEADING.search(d)
    start = m.start() if m and m.start() < len(d) - 200 else 0
    return re.sub(r"\s+", " ", d[start:start + chars]).strip()


def passage(title: str, organization: str, description: str) -> str:
    head = " | ".join(x for x in (title, organization) if x)
    return f"passage: {head}\n{ad_window(description)}"
