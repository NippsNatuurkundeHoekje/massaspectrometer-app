# *********************
# ** configuratie.py **
# *********************
# ROL VAN DIT BESTAND:
# - Centrale configuratie (constants) voor simulatie, geometrische conversies en UI.
# - Bevat didactische regels (levels/unlocks) en parametergrenzen (sliders).
#
# Invariant:
# - Geen uitvoerlogica, geen fysische integratie, geen rendering.
# - Wijzigingen hier veranderen alleen instellingen/parameters, niet de modelstructuur.


# ***************
# Simulatie/loop*
# ***************
FPS = 60  # Frames per seconde

# --- Ontwikkel-/diagnostiekopties (geen effect op modeldefinitie) ---
DEBUG_SELECTOR = False
DEBUG_SELECTOR_ONLY_FIRST_ION = False
DEBUG_SELECTOR_EVERY_N_FRAMES = 15  # print 1x per 15 frames
DEBUG_BOXEN = False  # Visualiseer geometrische hitboxes (alleen voor verificatie tijdens ontwikkeling).

# Conversie tussen SI (meters) en scherm (pixels):
# Posities worden in natuurkunde.py in meters bijgehouden; rendering/collisiontests gebruiken pixels.
# MAX_STEP_PX en MAX_SUBSTEPS begrenzen de verplaatsing per (sub)stap om tunneling en instabiliteit te voorkomen.
PX_PER_METER = 5000  # 1 meter = 5000 pixels
MAX_STEP_PX = 2.0  # Maximaal aantal pixels per simulatiestap (voor stabiliteit)
MAX_SUBSTEPS = 60  # Maximaal aantal substeps per frame (noodrem)

# Instroominstellingen:
# DEELTJES_PER_SECONDE bepaalt de intensiteit van de gesimuleerde bundel (deeltjes/s).
# Dit is een model- en visualisatiekeuze (meer deeltjes = sneller histogram), geen natuurkundige constante.
DEELTJES_PER_SECONDE = 40  # Instroom-intensiteit (ionen per seconde)
MAX_DEELTJES = 20000  # Noodrem (normaal niet actief; opruimen gebeurt via ion.actief)

# Visuele deeltjesstraal:
# Wordt gebruikt voor weergave. Botsingsdetectie kan een aparte (effectieve) straal gebruiken in natuurkunde.py.
DEELTJE_STRAAL_M = 0.0005  # visuele straal (gekoppeld aan PX_PER_METER)

# Instroompositie (px, afgemeten op achtergrond)
PIJP_X_MIN_PX = 106
PIJP_X_MAX_PX = 110
INSTROOM_Y_PX = 435
PIJP_Y_MIN_PX = INSTROOM_Y_PX - 5
PIJP_Y_MAX_PX = INSTROOM_Y_PX + 5

# Schaalfactoren (numerieke/visualisatie-afstemming):
# De onderliggende formules blijven fysisch (Lorentzkracht, E=U/d).
# Indien schaal = 1.0 heeft de factor geen effect. SIMULATIE_TIJD_SCHAAL is bedoeld om de tijdstap
# te schalen naar een bruikbare simulatiesnelheid bij gegeven venster- en veldinstellingen.
SIMULATIE_SCHAAL_ESELECTOR = 1  # e-10
SIMULATIE_SCHAAL_BSELECTOR = 1  # e-6
SIMULATIE_SCHAAL_SNELHEID = 1  # e-5
SIMULATIE_TIJD_SCHAAL = 5e-8
SIMULATIE_SCHAAL_BVELD = 1  # e-6
SIMULATIE_SCHAAL_EVELD = 1  # e-12

# -------------------------------------------
# standaard instellingen acceleratiekamer---
# -------------------------------------------
UACC_VOLT = 15000.0  # Acceleratiespanning in Volt
ACCELERATIE_PLAATAFSTAND_M = 0.02  # Afstand tussen geladen platen in meter

# --------------------------------------------
# standaard instellingen snelheidsselector---
# --------------------------------------------
SELECTOR_PLAATAFSTAND_M = 0.006  # Afstand tussen platen in de selector
B_SELECTOR_TESLA = 0.25  # B-veld in de selector (Tesla)
U_SELECTOR_VOLT = 15000  # Voltage over de selector

# ---------------------------------------
# standaard instellingen analysekamer---
# ---------------------------------------
B_ANALYSE_TESLA = 0.25  # basiswaarde; teken = richting uit/in het scherm

# Kleurcodering:
# Elke ion-soort krijgt een vaste kleur zodat banen en histogrammen consistent te interpreteren zijn binnen één run.
KLEUREN_PALET = [
    (80, 200, 255),  # blauw
    (255, 80, 80),  # rood
    (180, 80, 255),  # paars
    (80, 255, 140),  # groen
    (180, 120, 00),  # donker oranje
]

# ****************************
# Levels (didactische opbouw)*
# ****************************
# Voor elk level wordt vastgelegd:
# - wat de leerling MAG instellen (unlock)
# - hoe het instroomprofiel per level is (mono / mengsel)
# - uit welke bak de ionen worden geloot
# - hoeveel ionen in het mengsel zitten
#
# Belangrijk:
# De concrete ionen worden per level-start random gekozen en elders opgeslagen
# (in ui_state). Dit bestand bevat dus de REGELS, niet het antwoord.

LEVEL_DEFINITIES: dict[int, dict] = {
    # Level 1–3: alleen B-veld analysekamer instellen (wennen)
    1: {
        "unlock": {
            "u_acc": False,
            "e_selector": False,
            "b_selector": False,
            "b_analyse": True,
        },
        "instroomprofiel": "mono_bak",
        "bak": "A",
        "mengsel_grootte": 1,
        "mengsel_weging": (1.0,),
        "omschrijving": "1 ion (basis), alleen B_analyse",
    },
    2: {
        "unlock": {
            "u_acc": False,
            "e_selector": False,
            "b_selector": False,
            "b_analyse": True,
        },
        "instroomprofiel": "mono_bak",
        "bak": "A",
        "mengsel_grootte": 1,
        "mengsel_weging": (1.0,),
        "omschrijving": "1 ion (herhaling), alleen B_analyse",
    },
    3: {
        "unlock": {
            "u_acc": False,
            "e_selector": False,
            "b_selector": False,
            "b_analyse": True,
        },
        "instroomprofiel": "mono_bak",
        "bak": "A",
        "mengsel_grootte": 1,
        "mengsel_weging": (1.0,),
        "omschrijving": "1 ion (andere bak), alleen B_analyse",
    },
    # Level 4–6: B_analyse + selector (E en B velden) instellen
    4: {
        "unlock": {
            "u_acc": False,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "B",
        "mengsel_grootte": 2,
        "mengsel_weging": (0.5, 0.5),
        "omschrijving": "2 ionen (makkelijk), selector + B_analyse",
    },
    5: {
        "unlock": {
            "u_acc": False,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "B",
        "mengsel_grootte": 2,
        "mengsel_weging": (0.5, 0.5),
        "omschrijving": "2 ionen (lastiger), selector + B_analyse",
    },
    6: {
        "unlock": {
            "u_acc": False,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "B",
        "mengsel_grootte": 2,
        "mengsel_weging": (0.5, 0.5),
        "omschrijving": "2 ionen (moeilijk), selector + B_analyse",
    },
    # Level 7–10: alles instellen (incl. Uacc), grotere mengsels/complexer/ladingsverschillen
    7: {
        "unlock": {
            "u_acc": True,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "C",
        "mengsel_grootte": 3,
        "mengsel_weging": (0.34, 0.33, 0.33),
        "omschrijving": "3 ionen (start complex), alles",
    },
    8: {
        "unlock": {
            "u_acc": True,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "C",
        "mengsel_grootte": 3,
        "mengsel_weging": (0.34, 0.33, 0.33),
        "omschrijving": "3 ionen (zware ladingen), alles",
    },
    9: {
        "unlock": {
            "u_acc": True,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "C",
        "mengsel_grootte": 3,
        "mengsel_weging": (0.34, 0.33, 0.33),
        "omschrijving": "3 ionen (negatief), alles",
    },
    10: {
        "unlock": {
            "u_acc": True,
            "e_selector": True,
            "b_selector": True,
            "b_analyse": True,
        },
        "instroomprofiel": "eenvoudig_mengsel_bak",
        "bak": "C",
        "mengsel_grootte": 3,
        "mengsel_weging": (0.50, 0.25, 0.25),
        "omschrijving": "3 ionen (scheve weging), alles",
    },
}

# ******************
# Sliderdefinities *
# ******************
# Sliderdefinities koppelen UI aan modelparameters:
# - min/max definiëren het experimentele bereik
# - decimalen definieert resolutie van de weergave
# - standaard is de startwaarde bij reset/nieuw level (tenzij level-logic dit overschrijft)
SLIDER_DEFINITIES = {
    "u_acc_V": {
        "label": "Versnellingsspanning",
        "min": 0.0,
        "max": 40000.0,
        "eenheid": "V",
        "decimalen": 0,
        "standaard": 15000.0,
    },
    "U_selector_V": {
        "label": "Selectorspanning",
        "min": 0.0,
        "max": 40000.0,
        "eenheid": "V",
        "decimalen": 0,
        "standaard": 15000.0,
    },
    "B_selector_T": {
        "label": "Magnetisch veld",
        "min": 0.0,
        "max": 1.5,
        "eenheid": "T",
        "decimalen": 3,
        "standaard": 0.25,
    },
    "B_analyse_T": {
        "label": "Magnetisch veld",
        "min": 0.0,
        "max": 1.5,
        "eenheid": "T",
        "decimalen": 3,
        "standaard": 0.25,
    },
    "bundeldichtheid": {
        "label": "Bundeldichtheid",
        "min": 0.0,
        "max": 3.0,
        "eenheid": "×",
        "decimalen": 2,
        "standaard": 1.0,
    },
}
