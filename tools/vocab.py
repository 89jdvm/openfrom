"""Public label lists, English and Spanish.

Role families and industries come from the earlier labelling study. Its "OUT"
codes (X1-X9, roles outside that study's scope) are renamed here to ordinary
role families, because on this site every role is in scope.
"""
from __future__ import annotations

# code: (English, Spanish)
ROLE_FAMILIES = {
    "R01": ("Sustainability & ESG", "Sostenibilidad y ESG"),
    "R02": ("Environmental & social safeguards", "Salvaguardas ambientales y sociales"),
    "R03": ("Social development, gender & rights", "Desarrollo social, género y derechos"),
    "R04": ("Agriculture, forestry & natural resources", "Agricultura, bosques y recursos naturales"),
    "R05": ("Enterprise & market development", "Desarrollo empresarial y de mercados"),
    "R06": ("Supply chain & procurement", "Cadena de suministro y compras"),
    "R07": ("Research & analysis", "Investigación y análisis"),
    "R08": ("Monitoring, evaluation & learning", "Monitoreo, evaluación y aprendizaje"),
    "R09": ("Programme & project management", "Gestión de programas y proyectos"),
    "R10": ("Management consulting", "Consultoría de gestión"),
    "R11": ("Policy, governance & public affairs", "Políticas públicas, gobernanza y asuntos públicos"),
    "R12": ("Partnerships, fundraising & grants", "Alianzas, recaudación de fondos y subvenciones"),
    "R13": ("Sales & business development", "Ventas y desarrollo de negocio"),
    "R14": ("Customer success & support", "Éxito y atención al cliente"),
    "R15": ("Marketing, communications & content", "Marketing, comunicación y contenidos"),
    "R16": ("Creative & media production", "Producción creativa y audiovisual"),
    "R17": ("Product, UX & business analysis", "Producto, UX y análisis de negocio"),
    "R18": ("Data analysis & BI", "Análisis de datos y BI"),
    "R19": ("AI enablement & AI data work", "Adopción de IA y trabajo con datos de IA"),
    "R20": ("Training & capacity building", "Formación y fortalecimiento de capacidades"),
    "R21": ("People, HR & recruiting", "Personas, RR. HH. y selección"),
    "R22": ("Operations & administration", "Operaciones y administración"),
    "R23": ("Finance, investment & risk", "Finanzas, inversión y riesgos"),
    "R24": ("General management", "Dirección general"),
    "R25": ("Translation & localisation", "Traducción y localización"),
    "R26": ("Software, IT & data engineering", "Software, TI e ingeniería de datos"),
    "R27": ("Engineering, architecture & construction", "Ingeniería, arquitectura y construcción"),
    "R28": ("Health & clinical", "Salud y clínica"),
    "R29": ("Law", "Derecho"),
    "R30": ("Accounting & audit", "Contabilidad y auditoría"),
    "R31": ("Teaching", "Docencia"),
    "R32": ("Hospitality, retail, trades & care", "Hostelería, comercio, oficios y cuidados"),
    "R33": ("Goods, works & field services", "Bienes, obras y servicios de campo"),
    "R34": ("Laboratory & science research", "Laboratorio e investigación científica"),
    "R00": ("Other", "Otro"),
}
OLD_TO_NEW = {"X1": "R26", "X2": "R27", "X3": "R28", "X4": "R29", "X5": "R30", "X6": "R31",
              "X7": "R32", "X8": "R33", "X9": "R34", "Z": "R00"}

INDUSTRIES = {
    "I01": ("Agriculture & food", "Agricultura y alimentación"),
    "I02": ("Forestry, land use & conservation", "Bosques, uso del suelo y conservación"),
    "I03": ("Energy & renewables", "Energía y renovables"),
    "I04": ("Climate & carbon services", "Clima y servicios de carbono"),
    "I05": ("Water, waste & environment", "Agua, residuos y medio ambiente"),
    "I06": ("Manufacturing & industry", "Manufactura e industria"),
    "I07": ("Consumer goods & retail", "Consumo y comercio minorista"),
    "I08": ("Logistics, transport & trade", "Logística, transporte y comercio"),
    "I09": ("Construction, real estate & infrastructure", "Construcción, inmobiliaria e infraestructura"),
    "I10": ("Mining & extractives", "Minería e hidrocarburos"),
    "I11": ("Banking, insurance & financial services", "Banca, seguros y servicios financieros"),
    "I12": ("Impact investing & development finance", "Inversión de impacto y financiación al desarrollo"),
    "I13": ("Software, internet & AI", "Software, internet e IA"),
    "I14": ("Consulting & professional services", "Consultoría y servicios profesionales"),
    "I15": ("International development", "Cooperación internacional"),
    "I16": ("Humanitarian response", "Acción humanitaria"),
    "I17": ("Human rights & civil society", "Derechos humanos y sociedad civil"),
    "I18": ("Public administration", "Administración pública"),
    "I19": ("Research & academia", "Investigación y academia"),
    "I20": ("Health & life sciences", "Salud y ciencias de la vida"),
    "I21": ("Education", "Educación"),
    "I22": ("Media, culture & creative industries", "Medios, cultura e industrias creativas"),
    "I23": ("Tourism, hospitality & events", "Turismo, hostelería y eventos"),
    "I24": ("Other or unclear", "Otro o sin determinar"),
}

# The "Impact sector" filter: industries whose work is public-interest by design,
# plus any job whose employer is an NGO, international organisation or public body.
IMPACT_INDUSTRIES = {"I02", "I04", "I05", "I12", "I15", "I16", "I17"}
IMPACT_EMPLOYERS = {"NGO", "INTL-ORG"}

SENIORITY = {
    "INTERN": ("Intern or trainee", "Prácticas"),
    "JUNIOR": ("Junior", "Junior"),
    "MID": ("Mid-level", "Intermedio"),
    "SENIOR": ("Senior", "Sénior"),
    "LEAD": ("Lead or director", "Jefatura o dirección"),
    "NS": ("Not stated", "Sin indicar"),
}

ENGAGEMENT = {
    "PERM": ("Permanent", "Indefinido"),
    "FIXED": ("Fixed-term", "Temporal"),
    "FREELANCE": ("Freelance or contract", "Freelance o por proyecto"),
    "IC": ("Consultancy", "Consultoría individual"),
    "FIRM": ("Firm contract", "Contrato con empresa"),
    "GRANT": ("Grant", "Subvención"),
    "VOLUNTEER": ("Volunteer", "Voluntariado"),
    "NS": ("Not stated", "Sin indicar"),
}

EMPLOYER_TYPES = {
    "COMPANY": ("Company", "Empresa"),
    "STARTUP": ("Startup", "Startup"),
    "CONSULTANCY": ("Consultancy", "Consultora"),
    "INTL-ORG": ("International organisation", "Organismo internacional"),
    "GOV": ("Government", "Gobierno"),
    "NGO": ("NGO or foundation", "ONG o fundación"),
    "RESEARCH": ("University or research", "Universidad o centro de investigación"),
    "AGENCY": ("Staffing agency", "Agencia de selección"),
    "NS": ("Unknown", "Desconocido"),
}


def role_code(old: str | None) -> str:
    if not old:
        return "R00"
    return OLD_TO_NEW.get(old, old if old in ROLE_FAMILIES else "R00")
