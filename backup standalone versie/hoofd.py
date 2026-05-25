# **************************************
# ** Massaspectrometer hoofdprogramma **
# **************************************

# ROL VAN DIT BESTAND: REGIE-LAAG
# - Initialisatie van Pygame, assets en globale toestand (ui_state)
# - Hoofdloop: events → acties → state-update → simulatie-update → rendering
# - Level-logica: instroompool, locks en startwaarden per level en fase
# - Koppeling tussen modules:
#   interactie.py (events → acties), natuurkunde.py (dynamica), wereld.py (geometrie), weergave.py (rendering)
#
# Dit bestand bevat geen natuurkundige afleiding; het orkestreert de uitvoering van het model.

# Standaard bibliotheken en externe pakketten
import pygame
import sys
import random

# Projectmodules
from interactie import verwerk_muis_events
from robot import RobotCoach, RobotCoachConfiguratie
from robot_teksten import get_intro, get_hint, get_info, get_startup, zeg, zegf
from ionen import maak_ion_pool_en_wegingen, ion_code, ALLE_IONEN
from generator import InstroomGenerator
from wereld import (
    teken_debug_boxen,
    bepaal_locatie_id_met_muis,
    LOCATIE_SELECTORVELD,
)
from natuurkunde import (
    bereken_selector_meters,
    update_deeltjes,
    bereken_v_uit_u_acc_sim,
    bereken_u_selector_voor_v_sim,
    kies_u_acc_locked_binnen_detector,
)
from configuratie import (
    FPS,
    DEBUG_BOXEN,
    LEVEL_DEFINITIES,
    SIMULATIE_TIJD_SCHAAL,
    SLIDER_DEFINITIES,
    KLEUREN_PALET,
)
from weergave import (
    teken_deeltjes,
    registreer_detector_hits,
    teken_ui,
    reset_detectorlaag,
    teken_histogram,
    teken_ionenkaart,
    teken_formulekaart,
)

# Bestanden met bronafbeeldingen
ACHTERGROND_BESTAND = "bronbestanden/massaspectrometer_achtergrond.png"
ROBOT_BESTAND = "bronbestanden/robot.gif"

# ui_state is de centrale toestand voor UI (user interface) en simulatie.
# Belangrijkste substructuren:
# - values: fysieke/experimentele instellingen (U_acc, U_selector, B-velden, bundeldichtheid)
# - locked: didactische lock-status per instelling/knop (level-afhankelijk)
# - buttons: runtime-toggles (pauze, meting)
# - histogram: meetdata (detectorhits) en weergaveparameters
# - meters: afgeleide grootheden (UI/diagnostiek), geen input voor de integrator
#
# Invariant: natuurkunde.py rekent uitsluitend op basis van waarden uit values (instellingen),
# en levert meetresultaten (hits) terug; weergave.py visualiseert ui_state zonder natuurkunde te wijzigen.

ui_state = {
    "level": 1,
    "kleuren": list(KLEUREN_PALET),
    "ion_labels": ["Ion A", "Ion B", "Ion C", "Ion D", "Ion E"],
    "level_status": "idle",  # "idle" of "running"
    "target_kleur_index": None,
    "ion_invoer_actief": None,
    "values": {
        "u_acc_V": 15000.0,
        "U_selector_V": 15000.0,
        "B_selector_T": 0.25,
        "B_analyse_T": 0.00,
        "bundeldichtheid": 1.0,
    },
    "locked": {
        "target": False,
        "u_acc_V": False,
        "U_selector_V": False,
        "B_selector_T": False,
        "B_analyse_T": False,
        "bundeldichtheid": False,
        "pause": False,
        "reset_sim": False,
        "reset_det": False,
        "start_level": False,
        "meting": False,
        "submit": False,
    },
    "verborgen": {
        "u_acc_V": False,
    },
    "schuifjes_slepen": {
        "start_muis_x": None,
        "start_waarde": None,
    },
    "buttons": {
        "pause": False,
        "meting": False,  # Start meting: pas na klikken 'start-meting' detectorhits registreren
    },
    "actieve_slider": None,  # sleutelnaam van actieve slider of None
    "meters": {
        "E_selector_Vpm": 0.0,
        "v_selectie_ms": 0.0,
    },
    "histogram": {"y_hits_m": [], "bins": 50, "y_expected_m": None},
    "selector_gekalibreerd": False,
    "show_ionenkaart": False,
    "ionenkaart_items": [],
    "ionenkaart_scroll": 0,
    "formulekaart_scroll": 0,
}

# reset invoer + feedback per kleurvak bij levelstart
ui_state["ion_invoer"] = [""] * len(ui_state["kleuren"])
ui_state["ion_feedback"] = [""] * len(ui_state["kleuren"])
_SUPERS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")


# **********************************
# ** HULPFUNCTIES VOOR HOOFDLOOP  **
# **********************************


# Normalisatie van leerlinginvoer voor vergelijking met de run-oplossing:
# - verwijder spaties en superscripts (¹²³⁺⁻)
# - maak letters lowercase
# - negeer isotopengetallen (didactische keuze: focus op element + lading)
def _norm_ion(s: str) -> str:
    s = (s or "").strip().replace(" ", "")
    s = s.translate(_SUPERS).lower()
    s = "".join(ch for ch in s if not ch.isdigit())
    return s


# Begrens een waarde tot het toegestane interval van een slider/parameter.
# Deze functie voorkomt ongeldige waarden na muisinteractie of automatische kalibratie.
def _klem(v: float, vmin: float, vmax: float) -> float:
    return max(vmin, min(vmax, v))


# Reset van meetdata voor een nieuwe meting/run.
# De keuze om bins te behouden en alleen hits te wissen houdt de UI-instelling stabiel.
def _reset_histogram(ui_state: dict):
    hist = ui_state.setdefault(
        "histogram", {"y_hits_m": [], "bins": 50, "y_expected_m": None}
    )
    hist["y_hits_m"].clear()
    hist["y_expected_m"] = None


def _kies_uacc(pool):
    return kies_u_acc_locked_binnen_detector(
        pool=pool,
        b_analyse_max_T=1.5,
        detector_lengte_m=0.08,
        marge_m=0.005,
    )


# ****************************************
# ** LEVEL EN RUN CONFIGURATIE FUNCTIES **
# ****************************************
def _bouw_ionenkaart_items() -> list[dict]:
    """
    Unieke lijst van alle ionen (alle bakken) als hulpmiddel.
    Output dicts matchen weergave.teken_ionenkaart().
    """
    uniek = {}
    for ion in ALLE_IONEN:
        code = ion_code(ion)
        if code not in uniek:
            uniek[code] = {
                "code": code,
                "massa_u": float(getattr(ion, "massa_u", 0.0)),
                "lading_e": int(getattr(ion, "lading_e", 0)),
            }
    return sorted(
        uniek.values(), key=lambda d: (d["massa_u"], d["lading_e"], d["code"])
    )


def _configureer_level(ui_state: dict, instroom: InstroomGenerator, kies_pool: bool):
    """Stel locks, instroom (optioneel) en didactische startwaarden in op basis van huidig level."""
    # Modelleercyclus (regie-perspectief):
    # - Definieer per level welke parameters door de gebruiker aangepast mogen worden (locked/unlocked).
    # - Kies per run de instroom (pool + wegingen) die als 'onbekende' set ionen fungeert.
    # - Stel startwaarden in die het experiment mogelijk maken, zonder de oplossing expliciet prijs te geven.
    #
    # Invariant: deze functie wijzigt alleen ui_state/instroomconfiguratie; de fysica blijft in natuurkunde.py.

    # -------------------------
    # 0) Level valideren
    # -------------------------
    level = int(ui_state.get("level", 1))
    if level not in LEVEL_DEFINITIES:
        level = max(1, min(level, max(LEVEL_DEFINITIES.keys())))
        ui_state["level"] = level

    level_def = LEVEL_DEFINITIES[level]

    # -------------------------
    # 1) UI-locks volgens level fase
    # -------------------------
    unlock = level_def.get("unlock", {})
    ui_state.setdefault("locked", {})
    locked = ui_state["locked"]
    locked["u_acc_V"] = not bool(unlock.get("u_acc", False))
    locked["U_selector_V"] = not bool(unlock.get("e_selector", False))
    locked["B_selector_T"] = not bool(unlock.get("b_selector", False))
    locked["B_analyse_T"] = not bool(unlock.get("b_analyse", False))

    # Als alleen locks moeten worden geupdate: klaar.
    if not kies_pool:
        return

    # -------------------------
    # 2) Instroom: kies per run ion(en) en bewaar run-oplossing
    # -------------------------
    profiel = level_def.get("instroomprofiel", "mono_bak")
    bak = level_def.get("bak", "A")
    mengsel_grootte = int(level_def.get("mengsel_grootte", 1))
    mengsel_weging = tuple(level_def.get("mengsel_weging", (1.0,)))

    pool, wegingen = maak_ion_pool_en_wegingen(
        instroomprofiel=profiel,
        bak=bak,
        mengsel_aantal=mengsel_grootte,
        mengsel_weging=mengsel_weging,
    )

    instroom.pool = pool
    instroom.wegingen = wegingen
    instroom.kleur_per_soort_id = {}
    instroom._volgende_kleur_index = random.randrange(len(ui_state["kleuren"]))

    ui_state["run_ionen"] = [ion_code(i) for i in pool]

    # -------------------------
    # 3) Level(fase) startwaarden (enige plek waar values gezet worden)
    # -------------------------
    waarden = ui_state.setdefault("values", {})
    ion = pool[0] if pool else None

    def _set_locked(key: str, value: float):
        if locked.get(key, False):
            waarden[key] = float(value)

    def _set_unlocked(key: str, value: float):
        if not locked.get(key, False):
            waarden[key] = float(value)

    # analysekamer start altijd neutraal
    waarden["B_analyse_T"] = 0.0

    # ---------- level 7+ : alles door leerling ----------
    if level >= 7:
        _set_unlocked("u_acc_V", 0.0)
        _set_unlocked("U_selector_V", 100.0)
        _set_unlocked("B_selector_T", 0.10)
        return

    # ---------- level 4–6 : Uacc door programma (locked), selector door leerling (start expres fout) ----------
    if 4 <= level <= 6:
        u_acc = _kies_uacc(pool)

        _set_locked("u_acc_V", u_acc)
        _set_unlocked("U_selector_V", 100.0)
        _set_unlocked("B_selector_T", 0.10)

        return

    # ---------- level 1–3 : alles door programma (perfect, maar alleen als locked) ----------
    if ion is None:
        return

    u_acc = _kies_uacc(pool)
    _set_locked("u_acc_V", u_acc)

    # B_selector: voorkom 0
    b_sel = float(waarden.get("B_selector_T", 0.25))
    if abs(b_sel) <= 1e-12:
        b_sel = 0.25
    _set_locked("B_selector_T", b_sel)

    # U_selector perfect alleen als selector locked is
    if locked.get("U_selector_V", False) and locked.get("B_selector_T", False):
        v = bereken_v_uit_u_acc_sim(float(waarden.get("u_acc_V", u_acc)), ion)
        if v > 0.0:
            u_sel = bereken_u_selector_voor_v_sim(
                v, float(waarden.get("B_selector_T", b_sel))
            )
            umin = float(SLIDER_DEFINITIES["U_selector_V"]["min"])
            umax = float(SLIDER_DEFINITIES["U_selector_V"]["max"])
            u_sel = max(umin, min(umax, float(u_sel)))
            _set_locked("U_selector_V", u_sel)


def _reset_sim_artefacts(ui_state: dict, deeltjes: list):
    # reset sim-artefacts (geen rest-staat)
    deeltjes.clear()
    ui_state["selector_gekalibreerd"] = False
    ui_state["buttons"]["meting"] = False
    reset_detectorlaag()
    _reset_histogram(ui_state)


def _reset_leerling_ui(ui_state: dict):
    # reset leerling-UI
    ui_state["target_kleur_index"] = None
    ui_state["ion_invoer_actief"] = None
    ui_state["ion_invoer"] = [""] * len(ui_state["kleuren"])
    ui_state["ion_feedback"] = [""] * len(ui_state["kleuren"])


# Start level: reset simulatie + UI naar beginstaat
def _start_level(
    ui_state: dict, instroom: InstroomGenerator, robot: RobotCoach, deeltjes: list
):
    # reset sim-artefacts en leerling-UI naar beginstaat
    _reset_sim_artefacts(ui_state, deeltjes)
    _reset_leerling_ui(ui_state)

    _configureer_level(ui_state, instroom, kies_pool=True)

    # level mag nu pas echt lopen (pas na pool + startwaarden)
    ui_state["level_status"] = "running"

    # robot intro uit robot_teksten.py
    lvl = int(ui_state.get("level", 1))
    robot.zeg(get_intro(lvl, fallback=""))
    ui_state["hint_step"] = 0


def _check_antwoord(ui_state: dict, instroom: InstroomGenerator, robot, deeltjes: list):
    if ui_state.get("level_status") != "running":
        zeg(robot, "no_level")
        return

    target = ui_state.get("target_kleur_index")
    if target is None:
        zeg(robot, "no_target")
        return

    run = ui_state.get("run_ionen", [])
    if not run:
        zeg(robot, "geen_pool")
        return

    ingevuld = ui_state["ion_invoer"][target]

    # Beoordelingslogica:
    # Het antwoord wordt vergeleken met de run-oplossing (ion_code), onafhankelijk van de meetdata.
    # Meetdata ondersteunt interpretatie, maar is niet strikt vereist om invoer te kunnen beoordelen.
    if not ui_state["histogram"]["y_hits_m"]:
        ui_state["ion_feedback"][target] = "Je hebt nog geen meetdata."

    verwacht_norm = {_norm_ion(x) for x in run}
    ingevuld_norm = _norm_ion(ingevuld)

    # 1) Check dit ene ingevulde ion
    if ingevuld_norm in verwacht_norm:
        ui_state["ion_feedback"][target] = "Correct."
        zeg(robot, "correct")
    else:
        ui_state["ion_feedback"][target] = "Niet correct. Probeer het opnieuw."
        lvl = int(ui_state.get("level", 1))
        step = int(ui_state.get("hint_step", 0))
        robot.zeg(get_hint(lvl, step=step))
        return

    # 2) Mengsel-regel: tussendoor invullen mag, maar level-up pas als ALLES voorkomt in de invoer
    gevonden = set()
    for txt in ui_state.get("ion_invoer", []):
        t = _norm_ion(txt)
        if t in verwacht_norm:
            gevonden.add(t)

    ontbrekend = len(verwacht_norm - gevonden)
    if ontbrekend > 0:
        robot.zeg(f"Goed. Je mist nog {ontbrekend} ion(en).")
        return

    # 3) Alles goed → level omhoog en reset naar idle
    ui_state["level"] = min(ui_state["level"] + 1, max(LEVEL_DEFINITIES.keys()))
    ui_state["level_status"] = "idle"
    # --- HARD RESET VAN RUN-STATE (anders blijft oud spul zichtbaar/ingevuld) ---
    for d in deeltjes:
        d.actief = False
    deeltjes.clear()  # verwijder bestaande deeltjes van het scherm

    # invoervelden + feedback leegmaken
    n = len(ui_state.get("kleuren", [])) or 5
    ui_state["ion_invoer"] = [""] * n
    ui_state["ion_feedback"] = [""] * n

    # hints en kalibratie resetten voor volgende run
    ui_state["hint_step"] = 0
    ui_state["selector_gekalibreerd"] = False

    ui_state["buttons"]["meting"] = False
    ui_state["target_kleur_index"] = None
    ui_state["ion_invoer_actief"] = None
    reset_detectorlaag()
    _reset_histogram(ui_state)
    _configureer_level(ui_state, instroom, kies_pool=False)
    robot.zeg("Alles goed. Klik op 'Start level' voor het volgende level.")


# Auto-kalibreer selector U-waarde op basis van eerste deeltje in selectorveld
def _auto_kalibreer_selector(ui_state: dict, deeltjes: list):
    # Automatische kalibratie is uitsluitend actief wanneer U_selector en B_selector locked zijn.
    # Doel: een consistente, reproduceerbare uitgangssituatie creëren voor levels waarin de selector
    # als 'gegeven instrumentinstelling' fungeert. De kalibratie gebruikt de eerste actieve deeltje-waarde
    # in het selectorveld als representatieve v_x en zet U_selector via de ideale selectorvoorwaarde.
    locked = ui_state.get("locked", {})
    if (
        ui_state.get("level_status") != "running"
        or ui_state.get("selector_gekalibreerd", False)
        or not locked.get("U_selector_V", False)
        or not locked.get("B_selector_T", False)
    ):
        return

    for d in deeltjes:
        if not getattr(d, "actief", True):
            continue
        loc = bepaal_locatie_id_met_muis(d.x_m, d.y_m)
        if loc == LOCATIE_SELECTORVELD:
            vx_in = abs(float(d.vx))
            b_sel = float(ui_state["values"].get("B_selector_T", 0.25))
            if vx_in > 0 and abs(b_sel) > 1e-12:
                ui_state["values"]["U_selector_V"] = float(
                    bereken_u_selector_voor_v_sim(vx_in, b_sel)
                )
            ui_state["selector_gekalibreerd"] = True
            return


# **************************************************
# Hoofd simulatiestap + hit/histogram verwerking **
# **************************************************
def _simuleer_frame(scherm, ui_state, instroom, deeltjes, dt, dt_sim):
    """Voert één simulatiestap uit en verwerkt hits/histogram zoals in de hoofdloop."""
    # Datastroom per frame:
    # 1) (optioneel) instroomgenerator voegt nieuwe deeltjes toe (afhankelijk van level_status)
    # 2) update_deeltjes(...) integreert dynamica en levert detectorhits (meetpunten)
    # 3) bij 'meting' worden hits geregistreerd (detectorlaag + histogram in ui_state)
    # 4) inactieve deeltjes worden verwijderd om de lijst beheersbaar te houden

    waarden = ui_state.get("values", {})
    instellingen = dict(waarden)
    knoppen = ui_state["buttons"]

    if knoppen.get("pause", False):
        hits = []
    else:
        if ui_state.get("level_status") == "running" and getattr(
            instroom, "pool", None
        ):
            instroom.update(dt, deeltjes, instellingen)

        _auto_kalibreer_selector(ui_state, deeltjes)
        hits = update_deeltjes(deeltjes, dt_sim, instellingen)

    ui_state["meters"].update(bereken_selector_meters(waarden))
    # Histogram marker: verwachte y (indien beschikbaar)
    hist = ui_state.setdefault(
        "histogram", {"y_hits_m": [], "bins": 50, "y_expected_m": None}
    )
    hist["y_expected_m"] = ui_state.get("meters", {}).get(
        "y_expected_m", hist.get("y_expected_m")
    )

    if knoppen.get("meting", False):
        registreer_detector_hits(scherm, hits)
        hist = ui_state["histogram"]["y_hits_m"]
        for hit in hits:
            hist.append(float(hit.y_m))

    # Verwijder alle deeltjes die niet meer actief zijn (bv. gebotst of buiten beeld);
    # we vervangen de inhoud van de bestaande lijst zodat alle verwijzingen intact blijven.
    deeltjes[:] = [d for d in deeltjes if d.actief]


def _teken_frame(scherm, basis_achtergrond, ballon_surface, robot, deeltjes, ui_state):
    """Tekenen in exact dezelfde volgorde als nu."""
    # De tekenvolgorde bepaalt de visuele hiërarchie: overlays (kaarten/UI/histogram) liggen boven de baanplot.
    scherm.blit(basis_achtergrond, (0, 0))
    teken_deeltjes(scherm, deeltjes)
    teken_ionenkaart(scherm, ui_state)  # overlay boven analysekamer
    teken_ui(scherm, ui_state)
    teken_formulekaart(scherm, ui_state)
    teken_histogram(scherm, ui_state)

    if DEBUG_BOXEN:
        teken_debug_boxen(scherm)

    robot.teken(scherm)
    ballon_surface.fill((0, 0, 0, 0))
    robot.teken_tekstballon(ballon_surface)
    scherm.blit(ballon_surface, (0, 0))


# ********************************************************
# UI-interactie helpers (schuifjes + reset van meting) **
# ********************************************************
def _precisie_factor(mods: int) -> float:
    # Resolutie van parameterinstelling via toetsen:
    # SHIFT verlaagt de gevoeligheid (fijnere afstelling), CTRL verlaagt verder.
    # Dit simuleert instrument-resolutie: grote stappen voor verkennen, kleine stappen voor finetuning.
    if mods & pygame.KMOD_SHIFT:
        return 0.10
    if mods & pygame.KMOD_CTRL:
        return 0.01
    return 1.00


def _stop_meting_en_reset(ui_state: dict, robot=None, melding: str | None = None):
    knoppen = ui_state.setdefault("buttons", {})
    if knoppen.get("meting", False):
        knoppen["meting"] = False
        reset_detectorlaag()
        _reset_histogram(ui_state)
        if robot and melding:
            robot.zeg(melding)


def _schuifje_min_max_decimalen(sleutel: str) -> tuple[float, float, int]:
    definitie = SLIDER_DEFINITIES[sleutel]
    vmin, vmax = float(definitie["min"]), float(definitie["max"])
    decimalen = int(definitie.get("decimalen", definitie.get("decimals", 0)))
    return vmin, vmax, decimalen


def _schuifje_waarde_via_rechthoek(
    sleutel: str, muis_x: int, rechthoek: pygame.Rect
) -> float:
    vmin, vmax, decimalen = _schuifje_min_max_decimalen(sleutel)
    t = (muis_x - rechthoek.x) / max(1, rechthoek.width)
    t = _klem(float(t), 0.0, 1.0)
    return round(vmin + t * (vmax - vmin), decimalen)


def _schuifje_waarde_via_sleep(
    ui_state: dict, sleutel: str, muis_x: int, rechthoek: pygame.Rect, mods: int
) -> float:
    vmin, vmax, decimalen = _schuifje_min_max_decimalen(sleutel)

    sleep = ui_state.get("schuifjes_slepen", {})
    start_x = sleep.get("start_muis_x", muis_x)
    start_v = float(sleep.get("start_waarde", ui_state["values"].get(sleutel, vmin)))

    dx = float(muis_x - start_x)

    # Precisie aanpassen met modifier keys (SHIFT = 10x fijner, CTRL = 100x fijner)
    precisie = _precisie_factor(mods)  # 0.1 (SHIFT) / 0.01 (CTRL) / 1.0
    dv_per_px = (vmax - vmin) / max(1.0, float(rechthoek.width)) * precisie

    nieuw = start_v + dx * dv_per_px
    nieuw = _klem(float(nieuw), vmin, vmax)
    return round(nieuw, decimalen)


def _schuifje_stap_grootte(sleutel: str) -> float:
    vmin, vmax, _ = _schuifje_min_max_decimalen(sleutel)
    if sleutel.endswith("_V"):
        return 200.0
    if sleutel.endswith("_T"):
        return 0.1
    return (vmax - vmin) / 200.0


def _schuifje_waarde_via_muiswiel(
    ui_state: dict, sleutel: str, dy: int, mods: int
) -> float:
    vmin, vmax, decimalen = _schuifje_min_max_decimalen(sleutel)
    stap = _schuifje_stap_grootte(sleutel)

    # SHIFT fijner, CTRL nóg fijner
    if mods & pygame.KMOD_SHIFT:
        stap /= 10.0
    elif mods & pygame.KMOD_CTRL:
        stap /= 100.0

    huidig = float(ui_state["values"].get(sleutel, vmin))
    nieuw = huidig + float(dy) * float(stap)
    nieuw = _klem(float(nieuw), vmin, vmax)
    return round(nieuw, decimalen)


# ****************************
# ** Actie-router vanuit UI **
# ****************************
# interactie.py zet ruwe Pygame-events om in semantische acties (bijv. "knop", "slider_drag").
# Deze functie vertaalt die acties naar wijzigingen in ui_state en naar calls die level-/meetlogica uitvoeren.
# Hiermee blijft event-parsing gescheiden van state-mutatie (architectuurscheiding).
def _verwerk_acties(
    acties: list[tuple], ui_state: dict, instroom, robot, deeltjes: list
):
    # -------------------------
    # Kleine verwerkers
    # -------------------------
    # Lokale verwerkers houden de mapping "actie → effect" compact en beperken de scope.
    # Voor de beoordeling is relevant dat de semantiek per actie expliciet en traceerbaar blijft.

    def _verwerk_ballon_sluiten(_actie):
        robot.verberg_ballon()

    def _verwerk_set_target(actie):
        ui_state["target_kleur_index"] = int(actie[1])

    def _verwerk_focus_invoer(actie):
        ui_state["ion_invoer_actief"] = int(actie[1])

    def _verwerk_wereld_info(actie):
        sleutel = actie[1]
        level = int(ui_state.get("level", 1))
        tekst = get_info(level, sleutel)
        if tekst:
            robot.zeg(tekst)

    def _verwerk_toggle_ionenkaart(_actie):
        ui_state["show_ionenkaart"] = not bool(ui_state.get("show_ionenkaart", False))

    def _verwerk_ionenkaart_scroll(actie):
        dy = int(actie[1])
        ui_state["ionenkaart_scroll"] = max(
            0, int(ui_state.get("ionenkaart_scroll", 0)) - dy
        )

    def _verwerk_formulekaart_scroll(actie):
        # ev.y = +1 omhoog / -1 omlaag (pygame)
        dy = int(actie[1])
        stap_px = 24  # scrollsnelheid; 24px ≈ 1-1.5 regel
        ui_state["formulekaart_scroll_px"] = (
            int(ui_state.get("formulekaart_scroll_px", 0)) - dy * stap_px
        )

    # -------------------------
    # Knoppen: via tabel
    # -------------------------
    def _knop_submit(_actie):
        _check_antwoord(ui_state, instroom, robot, deeltjes)

    def _knop_start_level(_actie):
        _start_level(ui_state, instroom, robot, deeltjes)

    def _knop_meting(_actie):
        if ui_state.get("level_status") != "running":
            zeg(robot, "no_level")
            return
        if ui_state.get("target_kleur_index") is None:
            zeg(robot, "no_target")
            return

        knoppen = ui_state.setdefault("buttons", {})
        knoppen["meting"] = not bool(knoppen.get("meting", False))
        if knoppen["meting"]:
            reset_detectorlaag()
            _reset_histogram(ui_state)
            zeg(robot, "meting_start")
        else:
            zeg(robot, "meting_stop")

    def _knop_pause(_actie):
        knoppen = ui_state.setdefault("buttons", {})
        knoppen["pause"] = not bool(knoppen.get("pause", False))

    def _reset_meting_zonder_bericht(reset_simulatie: bool):
        # Hergebruik centrale sim-reset (zelfde gedrag, minder duplicatie)
        if reset_simulatie:
            _reset_sim_artefacts(ui_state, deeltjes)
        else:
            # zelfde als _reset_sim_artefacts maar zonder deeltjes.clear()
            ui_state["selector_gekalibreerd"] = False
            ui_state["buttons"]["meting"] = False
            reset_detectorlaag()
            _reset_histogram(ui_state)

    def _knop_reset_det(_actie):
        _reset_meting_zonder_bericht(reset_simulatie=False)

    def _knop_reset_sim(_actie):
        _reset_meting_zonder_bericht(reset_simulatie=True)

    KNOP_VERWERKERS = {
        "submit": _knop_submit,
        "start_level": _knop_start_level,
        "meting": _knop_meting,
        "pause": _knop_pause,
        "reset_det": _knop_reset_det,
        "reset_sim": _knop_reset_sim,
    }

    def _verwerk_knop(actie):
        knop_id = actie[1]
        fn = KNOP_VERWERKERS.get(knop_id)
        if fn:
            fn(actie)

    # -------------------------
    # Schuifjes: generiek
    # -------------------------
    def _verwerk_schuifje_start(actie):
        sleutel = actie[1]
        muis_x = int(actie[2])
        rechthoek = ui_state.get("slider_rechthoeken", {}).get(sleutel)
        if not rechthoek:
            return

        _stop_meting_en_reset(
            ui_state,
            robot=robot,
            melding="Meting gepauzeerd: instellingen gewijzigd. Start meting opnieuw.",
        )

        ui_state["actieve_slider"] = sleutel
        sleep = ui_state.setdefault(
            "schuifjes_slepen", {"start_muis_x": None, "start_waarde": None}
        )
        sleep["start_muis_x"] = muis_x
        sleep["start_waarde"] = float(ui_state["values"].get(sleutel, 0.0))

        ui_state["values"][sleutel] = _schuifje_waarde_via_rechthoek(
            sleutel, muis_x, rechthoek
        )

    def _verwerk_schuifje_slepen(actie):
        sleutel = actie[1]
        muis_x = int(actie[2])
        mods = int(actie[3])
        rechthoek = ui_state.get("slider_rechthoeken", {}).get(sleutel)
        if not rechthoek:
            return

        ui_state["values"][sleutel] = _schuifje_waarde_via_sleep(
            ui_state, sleutel, muis_x, rechthoek, mods
        )

        if ui_state.setdefault("buttons", {}).get("meting", False):
            ui_state["buttons"]["meting"] = False
            _reset_histogram(ui_state)

    def _verwerk_schuifje_einde(_actie):
        ui_state["actieve_slider"] = None
        sleep = ui_state.setdefault(
            "schuifjes_slepen", {"start_muis_x": None, "start_waarde": None}
        )
        sleep["start_muis_x"] = None
        sleep["start_waarde"] = None

    def _verwerk_schuifje_wiel(actie):
        sleutel = actie[1]
        dy = int(actie[2])
        mods = int(actie[3])

        ui_state["values"][sleutel] = _schuifje_waarde_via_muiswiel(
            ui_state, sleutel, dy, mods
        )

        if ui_state.setdefault("buttons", {}).get("meting", False):
            ui_state["buttons"]["meting"] = False
            _reset_histogram(ui_state)

    # -------------------------
    # Acties: router
    # -------------------------
    ACTIE_VERWERKERS = {
        "ballon_sluit": _verwerk_ballon_sluiten,
        "set_target": _verwerk_set_target,
        "focus_invoer": _verwerk_focus_invoer,
        "world_info": _verwerk_wereld_info,
        "toggle_ionenkaart": _verwerk_toggle_ionenkaart,
        "ionenkaart_scroll": _verwerk_ionenkaart_scroll,
        "formulekaart_scroll": _verwerk_formulekaart_scroll,
        "knop": _verwerk_knop,
        "slider_start": _verwerk_schuifje_start,
        "slider_drag": _verwerk_schuifje_slepen,
        "slider_end": _verwerk_schuifje_einde,
        "slider_wheel": _verwerk_schuifje_wiel,
    }

    for actie in acties:
        fn = ACTIE_VERWERKERS.get(actie[0])
        if fn:
            fn(actie)


# ******************************
# ** START DE HOOFDSIMULATIE  **
# ******************************
def start():
    pygame.init()

    # Eerst bronbestanden laden (zonder convert)
    try:
        achtergrond_onbewerkt = pygame.image.load(ACHTERGROND_BESTAND)
    except pygame.error as fout:
        print(f"Kan achtergrond niet laden: {ACHTERGROND_BESTAND}\nFout: {fout}")
        pygame.quit()
        sys.exit()

    # Venster = grootte van achtergrond (jouw eerdere aanpak)
    breedte, hoogte = achtergrond_onbewerkt.get_size()
    scherm = pygame.display.set_mode((breedte, hoogte))
    # Overlay-laag voor tekstballon (transparant)
    ballon_surface = pygame.Surface(scherm.get_size(), pygame.SRCALPHA)
    pygame.display.set_caption("Massaspectrometer – simulatie met robot-coach")
    klok = pygame.time.Clock()

    # Nu pas optimaliseren
    achtergrond = (
        achtergrond_onbewerkt.convert()
        if achtergrond_onbewerkt.get_alpha() is None
        else achtergrond_onbewerkt.convert_alpha()
    )
    # Vooraf samengestelde achtergrondlaag voor efficiënte rendering (1x samenvoegen, daarna blitten).
    basis_achtergrond = pygame.Surface((breedte, hoogte)).convert()
    basis_achtergrond.fill((0, 0, 0))  # evt. een andere egale kleur
    basis_achtergrond.blit(achtergrond, (0, 0))

    # Robot-coach onderin
    try:
        robot_configuratie = RobotCoachConfiguratie(
            robot_afbeelding=ROBOT_BESTAND,
            paneel_hoogte=220,
        )
        robot = RobotCoach(breedte, hoogte, robot_configuratie)
        robot.zeg(get_startup())
    except Exception as fout:
        print(f"Robot afbeelding kon niet worden geladen:\n{fout}")
        pygame.quit()
        sys.exit()
    deeltjes = []

    # 1) Maak instroom-object zonder pool-keuze (pool wordt door hoofd.py bepaald)
    #    NB: dit vereist dat InstroomGenerator geen pool meer maakt in __init__
    instroom = InstroomGenerator(pool=[], wegingen=[])

    # 2) Pas t locks toe voor huidig level
    _configureer_level(ui_state, instroom, kies_pool=False)

    # Ionenkaart = alle ionen uit alle bakken (hulpkaart, niet run-afhankelijk)
    ui_state["ionenkaart_items"] = _bouw_ionenkaart_items()

    actief = True
    while actief:
        dt = klok.tick(FPS) / 1000.0
        dt = min(dt, 1.0 / FPS)  # voorkom grote stappen bij lag en opstart
        dt_sim = dt * SIMULATIE_TIJD_SCHAAL
        events = pygame.event.get()
        for gebeurtenis in events:
            if gebeurtenis.type == pygame.QUIT:
                actief = False
                continue

            # bestaande invoer (robot)
            robot.verwerk_gebeurtenis(gebeurtenis)

            # Toetsinvoer: alleen actief wanneer een invoervak geselecteerd is en het level draait.
            if gebeurtenis.type == pygame.KEYDOWN:
                actief_i = ui_state.get("ion_invoer_actief")

                # alleen typen als er een invoervak actief is
                if actief_i is None:
                    continue

                # alleen typen in een running level (anders is het rommelig)
                if ui_state.get("level_status") != "running":
                    zeg(robot, "no_level")
                    continue

                invoer = ui_state["ion_invoer"][actief_i]

                if gebeurtenis.key == pygame.K_RETURN:
                    _check_antwoord(ui_state, instroom, robot, deeltjes)
                    continue

                if gebeurtenis.key == pygame.K_BACKSPACE:
                    ui_state["ion_invoer"][actief_i] = invoer[:-1]
                    continue

                ch = gebeurtenis.unicode
                if ch and len(ch) == 1 and (ch.isalnum() or ch in "+-⁺⁻¹²³⁴⁵⁶⁷⁸⁹⁰"):
                    ui_state["ion_invoer"][actief_i] = (invoer + ch)[:10]

        # ---- Muis-interactie in 1 keer via interactie.py ----
        acties = verwerk_muis_events(events, ui_state, robot)
        _verwerk_acties(acties, ui_state, instroom, robot, deeltjes)

        # ---------- EINDE GEBEURTENISSENLOOP ----------

        # Simulatie + robot
        _simuleer_frame(scherm, ui_state, instroom, deeltjes, dt, dt_sim)
        robot.update(dt)

        # Tekenen
        _teken_frame(
            scherm, basis_achtergrond, ballon_surface, robot, deeltjes, ui_state
        )
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    start()
