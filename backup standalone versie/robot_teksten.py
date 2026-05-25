# robot_teksten.py
# Alle robot-teksten op één plek (didactiek gescheiden van engine).
# Geen fysica; alleen begeleidingstekst.

from __future__ import annotations

from typing import Dict, List


ROBOT_TEKSTEN: Dict[int, Dict[str, List[str] | str]] = {
    # Levels 1–3: histogram lezen + B_analyse
    1: {
        "intro": "Level 1: één ion. Start het level, kies een kleur om te analyseren, en start daarna een meting.",
        "hints": [
            "Kies eerst een kleur in de legenda: dat is het ion dat je nu analyseert.",
            "Let op: in dit model is D de diameter (niet de straal).",
            "Zie je geen duidelijke inslag? Start meting opnieuw of verhoog de bundeldichtheid.",
        ],
    },
    2: {
        "intro": "Level 2: één ion. Je oefent opnieuw met het instellen van B_analyse en het aflezen van het histogram.",
        "hints": [
            "Zorg eerst dat je een stabiele inslagplek krijgt op de detector.",
            "Diameter D: kijk naar de afstandschaal in het histogram.",
            "Reset detector helpt als je beeld ‘vervuild’ is door oude hits.",
        ],
    },
    3: {
        "intro": "Level 3: één ion. Zelfde aanpak, maar de meting kan wat minder perfect zijn — dat hoort bij meten.",
        "hints": [
            "Een kleine spreiding in hits is normaal: kijk naar het centrum van de cluster.",
            "Als de bundel de detector mist: pas B_analyse aan en meet opnieuw.",
            "Blijf bij je meetgegevens: gokken mag, maar meten wint.",
        ],
    },
    # Levels 4–6: selector gebruiken (E/B) + B_analyse
    4: {
        "intro": "Level 4: twee ionen. Gebruik eerst de snelheidsselector (E en B) om een smalle bundel door te laten.",
        "hints": [
            "In de selector geldt: v ≈ E/B. Als je bundel breed is, laat je meerdere snelheden door.",
            "Probeer E of B te veranderen tot de bundel ‘rustiger’ en smaller wordt.",
            "Pas daarna B_analyse aan om de bundel netjes op de detector te krijgen.",
        ],
    },
    5: {
        "intro": "Level 5: twee ionen (lastiger). Je krijgt minder ‘makkelijke’ combinaties, maar dezelfde strategie werkt.",
        "hints": [
            "Werk in stappen: eerst selector (smal), daarna analysekamer (landing).",
            "Als je histogram rare dubbele pieken heeft: selector is waarschijnlijk te ‘open’.",
            "Reset detector, meet opnieuw, en vergelijk je D met mogelijke ionen.",
        ],
    },
    6: {
        "intro": "Level 6: twee ionen (moeilijk). Blijf systematisch: selector stabiliseren, dan pas identificeren.",
        "hints": [
            "Gebruik de meters als controle, niet als antwoord-generator.",
            "Als je niets zinnigs kunt matchen: verbeter eerst je meetkwaliteit (smalle bundel).",
            "Je hoeft niet in één keer goed te zitten: meten → bijstellen → opnieuw meten.",
        ],
    },
    # Levels 7–10: bak C, meervoudige lading ontdekken (m/q)
    7: {
        "intro": "Level 7: mengsel uit bak C. Soms past geen enkel 1+ ion netjes — dan moet je anders redeneren.",
        "hints": [
            "Past geen enkel 1+ ion bij jouw D? Dan meet je misschien niet ‘m’, maar iets als m/q.",
            "Verander U_acc en kijk hoe sterk D mee verandert. Te sterk? Dan kan q groter zijn dan 1.",
            "Probeer een ionnotatie met een andere lading (zoals 2+ of 3+) en kijk of dat wél logisch past.",
        ],
    },
    8: {
        "intro": "Level 8: complexer mengsel. Je doel is nog steeds: één gekozen kleur-ion correct identificeren.",
        "hints": [
            "Als 1+ niet past: denk aan m/q. De baan wordt bepaald door Lorentzkracht en lading speelt mee.",
            "Test je aanname: verander U_acc en observeer de trend in D (richting en ‘sterkte’).",
            "Zoek een kandidaat waarbij m/q overeenkomt met jouw meting (lading hoort in je antwoord).",
        ],
    },
    9: {
        "intro": "Level 9: dit level vraagt echt onderzoeksgedrag: hypothese → test → conclusie.",
        "hints": [
            "Een goede meting is het halve werk: maak de bundel zo smal mogelijk.",
            "Als je ‘net naast’ zit: bedenk dat de simulatie bewust wat onnauwkeurigheid heeft bij zware ionen.",
            "Kom je structureel niet uit met 1+? Dan is dat een aanwijzing, geen pech.",
        ],
    },
    10: {
        "intro": "Level 10: eindlevel. Laat zien dat je zowel de selector als het idee m/q beheerst.",
        "hints": [
            "Combineer alles: selector (smal) → analysekamer (landing) → histogram (D) → ion (met lading).",
            "Als meerdere opties lijken te passen: kies de meest consistente met je trend bij U_acc.",
            "Je antwoord moet altijd de lading laten zien (bijv. 2+).",
        ],
    },
}

# World-info teksten (klik op opstelling) per level.
# Keys moeten matchen met wereld.resolve_click_target().
ROBOT_INFO = {
    1: {
        "instroom": (
            "Invoerbuis (instroom)\n"
            "• Hier komen ionen binnen.\n"
            "• Bundeldichtheid beïnvloedt hoe scherp het histogram is.\n"
            "• Tip: eerst stabiele bundel, dan pas finetunen."
        ),
        "versneller.veld": (
            "Versnellingskamer (Uacc)\n"
            "• Versnelt ionen met elektrische spanning Uacc.\n"
            "• Relatie: ½ m v² = q·Uacc.\n"
            "• Te hoog Uacc? Dan zie je vaak: bundel raakt platen/randen of schiet langs de selector."
        ),
        "versneller.bron": (
            "Spanningsbron versneller\n"
            "• Deze spanning bepaalt hoe sterk ionen worden versneld.\n"
            "• Hogere Uacc → hogere snelheid van de ionen.\n"
            "• Te hoog ingesteld? Dan kan de bundel de selector missen.\n"
            "• Stel Uacc zo in dat de bundel netjes de selector binnenkomt."
        ),
        "versneller.platen": (
            "Versnellingsplaten\n"
            "• Tussen deze platen staat een elektrisch veld.\n"
            "• Het veld loopt van de + plaat naar de − plaat.\n"
            "• Dit veld versnelt de ionen in horizontale richting.\n"
            "• De spanning op de bron bepaalt hoe sterk dit veld is."
        ),
        "versneller.collimator": (
            "Collimator (boven & onder)\n"
            "• De collimator maakt de ionenbundel smal en evenwijdig.\n"
            "• Alleen ionen die recht door de opening gaan, komen verder.\n"
            "• Zonder goede collimatie wordt de bundel te breed.\n"
            "• Een brede bundel geeft onnauwkeurige metingen."
        ),
        "selector.veld": (
            "Snelheidsselector (E×B)\n"
            "• Alleen ionen met v = E/B gaan rechtdoor.\n"
            "• E = Uselector / d (d = 6,0 mm).\n"
            "• Als bundel kromt: E/B matcht niet."
        ),
        "selector.ruimte": (
            "Selector-ruimte\n"
            "• Dit is de zone rond het selectorveld.\n"
            "• Hier moet de bundel recht en smal door de selector.\n"
            "• Zie je een kromme of brede bundel? Dan is v ≠ E/B.\n"
            "• Pas Uselector of Bselector aan en meet opnieuw."
        ),
        "selector.bron": (
            "Spanningsbron selector\n"
            "• Deze spanning bepaalt de sterkte van het E-veld in de selector.\n"
            "• Samen met Bselector bepaalt dit welke snelheid wordt doorgelaten.\n"
            "• Alleen ionen met v = E / B gaan recht door.\n"
            "• Pas Uselector aan tot de bundel niet afbuigt."
        ),
        "selector.platen": (
            "Selectorplaten\n"
            "• Deze platen maken het elektrische veld in de selector.\n"
            "• Het E-veld werkt loodrecht op het magnetisch veld.\n"
            "• Ionen die te langzaam of te snel zijn, buigen af.\n"
            "• Alleen bij juiste instellingen blijft de bundel recht."
        ),
        "analyse.kamer": (
            "Analysekamer\n"
            "• In de analysekamer heerst een magnetisch veld (Banalyse) waardoor een ion in een cirkelbaan beweegt.\n"
            "• Straal: r = (m·v)/(q·B).\n"
            "• Met r en v bepaal je m/q → match met ionenkaart.\n"
            "• Rechtermuisknop in analysekamer: ionenkaart tonen/verbergen."
        ),
        "detector": (
            "Detector + histogram\n"
            "• Histogram ‘gem’ geeft gemiddelde afstand (Sgem in mm).\n"
            "• In dit model: r = Sgem/2.\n"
            "• Daarna: m/q = r·B / v."
        ),
    }
}

GENERIC = {
    # algemene flow
    "no_target": "Kies eerst een kleur in de legenda (welk ion je analyseert), daarna kun je meten.",
    "no_level": "Klik eerst op 'Start level' om de ionen te starten.",
    "geen_pool": "Er is geen ionenpool actief. Start level opnieuw.",
    "level_klaar": "Alles goed. Klik op 'Start level' voor het volgende level.",
    # meten / histogram
    "meting_start": "Meting gestart.",
    "meting_stop": "Meting gestopt.",
    "meting_gepauzeerd": "Meting gepauzeerd: instellingen gewijzigd. Start meting opnieuw.",
    "leeg_hist": "Je hebt nog geen meetdata.",
    "no_hits": "Je hebt (nog) geen meetdata. Start een meting en wacht op hits, of verhoog de bundeldichtheid.",
    # antwoordfeedback
    "correct": "Correct. Je hebt het ion goed geïdentificeerd.",
    "incorrect": "Niet correct. Probeer het opnieuw.",
    # variabel (format-strings)
    "mist_n_ionen": "Goed. Je mist nog {n} ion(en).",
}


STARTUP_TEKST = (
    "Welkom! Dit is een massaspectrometer-model.\n"
    "\n"
    "Zo werk je:\n"
    "• Klik met linkermuisknop op onderdelen van de opstelling voor uitleg.\n"
    "• In de analysekamer: rechtermuisknop = ionenkaart tonen/verbergen (wiel = scroll).\n"
    "• Schuifjes: Je kunt de schuifjes slepen (linkermuisknop ingedrukt houden), \n"
    "  maar handiger werkt het door scroll te gebruiken terwijl je met de muis boven het schuifje hangt, \n"
    "  daarbij is SHIFT = fijner (stap 10 of 20), CTRL = nóg fijner (stap 1 of 2).\n"
    "• Gebruik: formulekaart + histogram → bepaal r, v → bereken m/q → zoek ion op de kaart → noteer je antwoord in de ionnotatie (bijv. C2+).\n  "
    "Tip: Start level → kies targetkleur → start meting."
)


def zeg(robot, sleutel: str):
    robot.zeg(GENERIC[sleutel])


def zegf(robot, sleutel: str, **kwargs):
    robot.zeg(GENERIC[sleutel].format(**kwargs))


def get_startup() -> str:
    return STARTUP_TEKST


def get_intro(level: int, fallback: str = "") -> str:
    d = ROBOT_TEKSTEN.get(level, {})
    intro = d.get("intro")
    if isinstance(intro, str) and intro.strip():
        return intro
    return fallback or f"Level {level}."


def get_hint(level: int, step: int) -> str:
    d = ROBOT_TEKSTEN.get(level, {})
    hints = d.get("hints", [])
    if not isinstance(hints, list) or not hints:
        return "Hint: meet opnieuw en werk stap voor stap."
    i = max(0, min(int(step), len(hints) - 1))
    return str(hints[i])


def get_info(level: int, key: str, fallback: str = "") -> str:
    d = ROBOT_INFO.get(level) or ROBOT_INFO.get(1, {})
    txt = d.get(key)
    if isinstance(txt, str) and txt.strip():
        return txt
    return fallback or ""
