"""ISO-3166 countries: code | English | Spanish | UN M49 subregion | UTC offset range (standard time).

Subregions: NAF Northern Africa, EAF Eastern Africa, MAF Middle Africa, SAF Southern Africa,
WAF Western Africa, CAR Caribbean, CAM Central America, SAM South America, NAM Northern
America, CAS Central Asia, EAS Eastern Asia, SEA South-eastern Asia, SAS Southern Asia,
WAS Western Asia, EEU Eastern Europe, NEU Northern Europe, SEU Southern Europe,
WEU Western Europe, ANZ Australia and New Zealand, MEL Melanesia, MIC Micronesia, POL Polynesia.
"""

RAW = """
AF|Afghanistan|Afganistán|SAS|4.5|4.5
AL|Albania|Albania|SEU|1|1
DZ|Algeria|Argelia|NAF|1|1
AD|Andorra|Andorra|SEU|1|1
AO|Angola|Angola|MAF|1|1
AG|Antigua and Barbuda|Antigua y Barbuda|CAR|-4|-4
AR|Argentina|Argentina|SAM|-3|-3
AM|Armenia|Armenia|WAS|4|4
AU|Australia|Australia|ANZ|8|10
AT|Austria|Austria|WEU|1|1
AZ|Azerbaijan|Azerbaiyán|WAS|4|4
BS|Bahamas|Bahamas|CAR|-5|-5
BH|Bahrain|Baréin|WAS|3|3
BD|Bangladesh|Bangladés|SAS|6|6
BB|Barbados|Barbados|CAR|-4|-4
BY|Belarus|Bielorrusia|EEU|3|3
BE|Belgium|Bélgica|WEU|1|1
BZ|Belize|Belice|CAM|-6|-6
BJ|Benin|Benín|WAF|1|1
BT|Bhutan|Bután|SAS|6|6
BO|Bolivia|Bolivia|SAM|-4|-4
BA|Bosnia and Herzegovina|Bosnia y Herzegovina|SEU|1|1
BW|Botswana|Botsuana|SAF|2|2
BR|Brazil|Brasil|SAM|-5|-2
BN|Brunei|Brunéi|SEA|8|8
BG|Bulgaria|Bulgaria|EEU|2|2
BF|Burkina Faso|Burkina Faso|WAF|0|0
BI|Burundi|Burundi|EAF|2|2
CV|Cabo Verde|Cabo Verde|WAF|-1|-1
KH|Cambodia|Camboya|SEA|7|7
CM|Cameroon|Camerún|MAF|1|1
CA|Canada|Canadá|NAM|-8|-3.5
CF|Central African Republic|República Centroafricana|MAF|1|1
TD|Chad|Chad|MAF|1|1
CL|Chile|Chile|SAM|-4|-3
CN|China|China|EAS|8|8
CO|Colombia|Colombia|SAM|-5|-5
KM|Comoros|Comoras|EAF|3|3
CG|Congo|Congo|MAF|1|1
CD|DR Congo|República Democrática del Congo|MAF|1|2
CR|Costa Rica|Costa Rica|CAM|-6|-6
CI|Côte d'Ivoire|Costa de Marfil|WAF|0|0
HR|Croatia|Croacia|SEU|1|1
CU|Cuba|Cuba|CAR|-5|-5
CY|Cyprus|Chipre|WAS|2|2
CZ|Czechia|Chequia|EEU|1|1
DK|Denmark|Dinamarca|NEU|1|1
DJ|Djibouti|Yibuti|EAF|3|3
DM|Dominica|Dominica|CAR|-4|-4
DO|Dominican Republic|República Dominicana|CAR|-4|-4
EC|Ecuador|Ecuador|SAM|-5|-5
EG|Egypt|Egipto|NAF|2|2
SV|El Salvador|El Salvador|CAM|-6|-6
GQ|Equatorial Guinea|Guinea Ecuatorial|MAF|1|1
ER|Eritrea|Eritrea|EAF|3|3
EE|Estonia|Estonia|NEU|2|2
SZ|Eswatini|Esuatini|SAF|2|2
ET|Ethiopia|Etiopía|EAF|3|3
FJ|Fiji|Fiyi|MEL|12|12
FI|Finland|Finlandia|NEU|2|2
FR|France|Francia|WEU|1|1
GA|Gabon|Gabón|MAF|1|1
GM|Gambia|Gambia|WAF|0|0
GE|Georgia|Georgia|WAS|4|4
DE|Germany|Alemania|WEU|1|1
GH|Ghana|Ghana|WAF|0|0
GR|Greece|Grecia|SEU|2|2
GD|Grenada|Granada|CAR|-4|-4
GT|Guatemala|Guatemala|CAM|-6|-6
GN|Guinea|Guinea|WAF|0|0
GW|Guinea-Bissau|Guinea-Bisáu|WAF|0|0
GY|Guyana|Guyana|SAM|-4|-4
HT|Haiti|Haití|CAR|-5|-5
HN|Honduras|Honduras|CAM|-6|-6
HK|Hong Kong|Hong Kong|EAS|8|8
HU|Hungary|Hungría|EEU|1|1
IS|Iceland|Islandia|NEU|0|0
IN|India|India|SAS|5.5|5.5
ID|Indonesia|Indonesia|SEA|7|9
IR|Iran|Irán|SAS|3.5|3.5
IQ|Iraq|Irak|WAS|3|3
IE|Ireland|Irlanda|NEU|0|0
IL|Israel|Israel|WAS|2|2
IT|Italy|Italia|SEU|1|1
JM|Jamaica|Jamaica|CAR|-5|-5
JP|Japan|Japón|EAS|9|9
JO|Jordan|Jordania|WAS|3|3
KZ|Kazakhstan|Kazajistán|CAS|5|5
KE|Kenya|Kenia|EAF|3|3
KI|Kiribati|Kiribati|MIC|12|14
XK|Kosovo|Kosovo|SEU|1|1
KW|Kuwait|Kuwait|WAS|3|3
KG|Kyrgyzstan|Kirguistán|CAS|6|6
LA|Laos|Laos|SEA|7|7
LV|Latvia|Letonia|NEU|2|2
LB|Lebanon|Líbano|WAS|2|2
LS|Lesotho|Lesoto|SAF|2|2
LR|Liberia|Liberia|WAF|0|0
LY|Libya|Libia|NAF|2|2
LI|Liechtenstein|Liechtenstein|WEU|1|1
LT|Lithuania|Lituania|NEU|2|2
LU|Luxembourg|Luxemburgo|WEU|1|1
MO|Macao|Macao|EAS|8|8
MG|Madagascar|Madagascar|EAF|3|3
MW|Malawi|Malaui|EAF|2|2
MY|Malaysia|Malasia|SEA|8|8
MV|Maldives|Maldivas|SAS|5|5
ML|Mali|Malí|WAF|0|0
MT|Malta|Malta|SEU|1|1
MH|Marshall Islands|Islas Marshall|MIC|12|12
MR|Mauritania|Mauritania|WAF|0|0
MU|Mauritius|Mauricio|EAF|4|4
MX|Mexico|México|CAM|-8|-5
FM|Micronesia|Micronesia|MIC|10|11
MD|Moldova|Moldavia|EEU|2|2
MC|Monaco|Mónaco|WEU|1|1
MN|Mongolia|Mongolia|EAS|7|8
ME|Montenegro|Montenegro|SEU|1|1
MA|Morocco|Marruecos|NAF|1|1
MZ|Mozambique|Mozambique|EAF|2|2
MM|Myanmar|Myanmar|SEA|6.5|6.5
NA|Namibia|Namibia|SAF|2|2
NR|Nauru|Nauru|MIC|12|12
NP|Nepal|Nepal|SAS|5.75|5.75
NL|Netherlands|Países Bajos|WEU|1|1
NZ|New Zealand|Nueva Zelanda|ANZ|12|12
NI|Nicaragua|Nicaragua|CAM|-6|-6
NE|Niger|Níger|WAF|1|1
NG|Nigeria|Nigeria|WAF|1|1
KP|North Korea|Corea del Norte|EAS|9|9
MK|North Macedonia|Macedonia del Norte|SEU|1|1
NO|Norway|Noruega|NEU|1|1
OM|Oman|Omán|WAS|4|4
PK|Pakistan|Pakistán|SAS|5|5
PW|Palau|Palaos|MIC|9|9
PS|Palestine|Palestina|WAS|2|2
PA|Panama|Panamá|CAM|-5|-5
PG|Papua New Guinea|Papúa Nueva Guinea|MEL|10|10
PY|Paraguay|Paraguay|SAM|-3|-3
PE|Peru|Perú|SAM|-5|-5
PH|Philippines|Filipinas|SEA|8|8
PL|Poland|Polonia|EEU|1|1
PT|Portugal|Portugal|SEU|0|0
PR|Puerto Rico|Puerto Rico|CAR|-4|-4
QA|Qatar|Catar|WAS|3|3
RO|Romania|Rumania|EEU|2|2
RU|Russia|Rusia|EEU|2|12
RW|Rwanda|Ruanda|EAF|2|2
KN|Saint Kitts and Nevis|San Cristóbal y Nieves|CAR|-4|-4
LC|Saint Lucia|Santa Lucía|CAR|-4|-4
VC|Saint Vincent and the Grenadines|San Vicente y las Granadinas|CAR|-4|-4
WS|Samoa|Samoa|POL|13|13
SM|San Marino|San Marino|SEU|1|1
ST|Sao Tome and Principe|Santo Tomé y Príncipe|MAF|0|0
SA|Saudi Arabia|Arabia Saudí|WAS|3|3
SN|Senegal|Senegal|WAF|0|0
RS|Serbia|Serbia|SEU|1|1
SC|Seychelles|Seychelles|EAF|4|4
SL|Sierra Leone|Sierra Leona|WAF|0|0
SG|Singapore|Singapur|SEA|8|8
SK|Slovakia|Eslovaquia|EEU|1|1
SI|Slovenia|Eslovenia|SEU|1|1
SB|Solomon Islands|Islas Salomón|MEL|11|11
SO|Somalia|Somalia|EAF|3|3
ZA|South Africa|Sudáfrica|SAF|2|2
KR|South Korea|Corea del Sur|EAS|9|9
SS|South Sudan|Sudán del Sur|EAF|2|2
ES|Spain|España|SEU|0|1
LK|Sri Lanka|Sri Lanka|SAS|5.5|5.5
SD|Sudan|Sudán|NAF|2|2
SR|Suriname|Surinam|SAM|-3|-3
SE|Sweden|Suecia|NEU|1|1
CH|Switzerland|Suiza|WEU|1|1
SY|Syria|Siria|WAS|3|3
TW|Taiwan|Taiwán|EAS|8|8
TJ|Tajikistan|Tayikistán|CAS|5|5
TZ|Tanzania|Tanzania|EAF|3|3
TH|Thailand|Tailandia|SEA|7|7
TL|Timor-Leste|Timor Oriental|SEA|9|9
TG|Togo|Togo|WAF|0|0
TO|Tonga|Tonga|POL|13|13
TT|Trinidad and Tobago|Trinidad y Tobago|CAR|-4|-4
TN|Tunisia|Túnez|NAF|1|1
TR|Türkiye|Turquía|WAS|3|3
TM|Turkmenistan|Turkmenistán|CAS|5|5
TV|Tuvalu|Tuvalu|POL|12|12
UG|Uganda|Uganda|EAF|3|3
UA|Ukraine|Ucrania|EEU|2|2
AE|United Arab Emirates|Emiratos Árabes Unidos|WAS|4|4
GB|United Kingdom|Reino Unido|NEU|0|0
US|United States|Estados Unidos|NAM|-10|-5
UY|Uruguay|Uruguay|SAM|-3|-3
UZ|Uzbekistan|Uzbekistán|CAS|5|5
VU|Vanuatu|Vanuatu|MEL|11|11
VE|Venezuela|Venezuela|SAM|-4|-4
VN|Vietnam|Vietnam|SEA|7|7
YE|Yemen|Yemen|WAS|3|3
ZM|Zambia|Zambia|EAF|2|2
ZW|Zimbabwe|Zimbabue|EAF|2|2
"""

# Extra names seen in job ads (lower case) -> ISO code.
ALIASES = {
    "usa": "US", "u.s.": "US", "u.s.a.": "US", "us": "US", "united states of america": "US",
    "eeuu": "US", "ee. uu.": "US", "ee.uu.": "US", "estados unidos de américa": "US",
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB", "england": "GB", "scotland": "GB",
    "wales": "GB", "northern ireland": "GB",
    "czech republic": "CZ", "the netherlands": "NL", "holland": "NL", "deutschland": "DE",
    "españa": "ES", "espana": "ES", "brasil": "BR", "méxico": "MX", "perú": "PE", "panamá": "PA",
    "turkey": "TR", "turkiye": "TR", "ivory coast": "CI", "cote d'ivoire": "CI", "côte d’ivoire": "CI",
    "drc": "CD", "democratic republic of the congo": "CD", "republic of the congo": "CG",
    "south korea": "KR", "korea": "KR", "republic of korea": "KR", "viet nam": "VN",
    "russian federation": "RU", "uae": "AE", "emirates": "AE", "cape verde": "CV",
    "swaziland": "SZ", "burma": "MM", "macedonia": "MK", "east timor": "TL", "timor leste": "TL",
    "lao pdr": "LA", "syrian arab republic": "SY", "palestinian territories": "PS",
    "occupied palestinian territory": "PS", "gaza": "PS", "west bank": "PS",
    "sverige": "SE", "danmark": "DK", "norge": "NO", "österreich": "AT", "schweiz": "CH",
    "suisse": "CH", "belgië": "BE", "belgique": "BE", "italia": "IT", "polska": "PL", "suomi": "FI",
    "éire": "IE", "république démocratique du congo": "CD", "sénégal": "SN", "cameroun": "CM",
    "maroc": "MA", "algérie": "DZ", "tunisie": "TN", "kenia": "KE", "nigéria": "NG",
}

# Big cities that appear without a country.
CITIES = {
    "new york": "US", "nyc": "US", "san francisco": "US", "los angeles": "US", "seattle": "US",
    "chicago": "US", "boston": "US", "austin": "US", "denver": "US", "atlanta": "US", "miami": "US",
    "washington, dc": "US", "washington dc": "US", "toronto": "CA", "vancouver": "CA", "montreal": "CA",
    "london": "GB", "manchester": "GB", "edinburgh": "GB", "dublin": "IE", "paris": "FR", "berlin": "DE",
    "munich": "DE", "münchen": "DE", "hamburg": "DE", "frankfurt": "DE", "amsterdam": "NL",
    "rotterdam": "NL", "madrid": "ES", "barcelona": "ES", "lisbon": "PT", "lisboa": "PT", "porto": "PT",
    "brussels": "BE", "vienna": "AT", "wien": "AT", "zurich": "CH", "zürich": "CH", "geneva": "CH",
    "genève": "CH", "copenhagen": "DK", "stockholm": "SE", "oslo": "NO", "helsinki": "FI",
    "warsaw": "PL", "kraków": "PL", "krakow": "PL", "prague": "CZ", "budapest": "HU", "bucharest": "RO",
    "athens": "GR", "milan": "IT", "rome": "IT", "tallinn": "EE", "riga": "LV", "vilnius": "LT",
    "bangalore": "IN", "bengaluru": "IN", "mumbai": "IN", "delhi": "IN", "new delhi": "IN",
    "hyderabad": "IN", "pune": "IN", "chennai": "IN", "singapore": "SG", "tokyo": "JP", "sydney": "AU",
    "melbourne": "AU", "auckland": "NZ", "nairobi": "KE", "lagos": "NG", "cape town": "ZA",
    "johannesburg": "ZA", "cairo": "EG", "dubai": "AE", "tel aviv": "IL", "istanbul": "TR",
    "são paulo": "BR", "sao paulo": "BR", "rio de janeiro": "BR", "buenos aires": "AR",
    "bogotá": "CO", "bogota": "CO", "medellín": "CO", "medellin": "CO", "lima": "PE",
    "santiago": "CL", "mexico city": "MX", "ciudad de méxico": "MX", "cdmx": "MX", "quito": "EC",
    "guayaquil": "EC", "montevideo": "UY", "manila": "PH", "jakarta": "ID", "bangkok": "TH",
    "kuala lumpur": "MY", "ho chi minh": "VN", "hanoi": "VN", "karachi": "PK", "lahore": "PK",
    "dhaka": "BD", "accra": "GH", "kampala": "UG", "kigali": "RW", "addis ababa": "ET",
    "dar es salaam": "TZ", "the hague": "NL", "den haag": "NL", "bonn": "DE", "rome, italy": "IT",
}
