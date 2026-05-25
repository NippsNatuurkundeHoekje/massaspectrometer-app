# ******************
# ** weergave.py **
# ******************
# ROL VAN DIT BESTAND: WEERGAVE-LAAG
# - Renderen van de simulatie (deeltjesbanen en detectorhits) en UI-elementen in pixelruimte.
# - Terugschrijven van layout-informatie (rechthoeken) naar ui_state voor hit-testing in interactie.py/hoofd.py.
#
# Invariant:
# - weergave.py wijzigt geen natuurkundige toestand (geen snelheden, geen krachten).
# - Mutaties in ui_state zijn beperkt tot render-only data (layout-rects, scroll-clamping, caches).


# Standaardbibliotheken en externe pakketten
import pygame
import math

# Projectmodules
from natuurkunde import Deeltje
from configuratie import DEBUG_BOXEN, SLIDER_DEFINITIES, PX_PER_METER
from wereld import DETECTOR_BOVEN, ANALYSEKAMER
from fonts import get_font

# Module constanten en caches
_detector_surface = None
_lettertype_groot = None
_lettertype_klein = None


# -------------------------------------------------------------
# Public API: deeltjes en detectorhits
# -------------------------------------------------------------
def teken_deeltjes(scherm: pygame.Surface, deeltjes: list[Deeltje]):
    """Teken detectorhits (accumulatie) + deeltjes als cirkels; interne eenheid is meter."""

    # Eerst detectorpixels (blijven staan)
    if _detector_surface is not None:
        scherm.blit(_detector_surface, (0, 0))

    # Daarna de bewegende deeltjes
    for ion in deeltjes:
        if not ion.actief:
            continue
        if ion.x_m is None or ion.y_m is None:
            if DEBUG_BOXEN:
                print("ONGELDIG DEELTJE:", ion)
            continue

        # Conversie SI → pixels:
        # posities blijven in meters in de fysica; rendering gebruikt PX_PER_METER.
        # De tekenstraal is een visuele representatie; botsingsdetectie gebruikt een aparte (effectieve) straal in natuurkunde.py.
        x_px = int(ion.x_m * PX_PER_METER)
        y_px = int(ion.y_m * PX_PER_METER)
        straal_px = max(1, int(ion.straal_m * PX_PER_METER))

        pygame.draw.circle(scherm, ion.kleur, (x_px, y_px), straal_px)


def registreer_detector_hits(scherm: pygame.Surface, hits: list):
    """
    Visualisatie-only: zet 1 pixel per hit op een interne accumulatie-surface.
    hits komen uit natuurkunde.update_deeltjes().
    Definitie van de visualisatie:
    - Elke hit wordt als één pixel (hit.kleur) geplot op een transparante accumulatielaag.
    - De laag wordt niet automatisch gewist; reset gebeurt expliciet via reset_detectorlaag().
    """
    global _detector_surface

    if _detector_surface is None or _detector_surface.get_size() != scherm.get_size():
        _detector_surface = pygame.Surface(scherm.get_size(), pygame.SRCALPHA)
        _detector_surface.fill((0, 0, 0, 0))  # transparant

    for hit in hits:
        x_px = int(hit.x_m * PX_PER_METER)
        y_px = int(hit.y_m * PX_PER_METER)

        if 0 <= x_px < scherm.get_width() and 0 <= y_px < scherm.get_height():
            _detector_surface.set_at((x_px, y_px), hit.kleur)


def reset_detectorlaag():
    global _detector_surface
    _detector_surface = None


def teken_ui(scherm, ui_state):
    _zorg_voor_lettertypes()

    # layout is render-output (geen input):
    # De UI-elementen worden getekend en hun rechthoeken worden vastgelegd.
    # Deze rechthoeken vormen de bron van waarheid voor hit-testing (interactie.py) en mogen daarom niet “geschat” worden.
    layout = {
        "knoppen": {},
        "sliders": {},
        "target_kleur_vakjes": [],
        "overlays": {},
    }

    # ---- paneel onderin ----
    marge = 12
    paneel_hoogte = 245
    rechtergrens_ui = scherm.get_width() - marge  # altijd binnen scherm

    # UI-paneel schaalt mee met vensterbreedte, met minimale breedte voor leesbaarheid.
    paneel_breedte = max(200, rechtergrens_ui - marge)
    paneel = pygame.Rect(
        marge,
        scherm.get_height() - paneel_hoogte - marge,
        paneel_breedte,
        paneel_hoogte,
    )

    _teken_paneel(scherm, paneel)

    # ---- kolomindeling (4 kolommen; gewogen) ----
    binnen_marge = 10
    kolom_tussenruimte = 5
    y0 = paneel.y + binnen_marge

    # Beschikbare breedte binnen paneel
    beschikbaar = paneel.width - 2 * binnen_marge - 3 * kolom_tussenruimte

    # Kolomindeling is een visualisatiekeuze:
    # schuifjes krijgen extra ruimte voor labels/waarden; actieknoppen bewust compacter.
    # Deze verdeling beïnvloedt geen simulatie, alleen de leesbaarheid van de UI.
    gewicht_ion = 1.2
    gewicht_schuifjes = 2.8  # breder voor tekst + panelen
    gewicht_robot = 1.1  # smaller
    gewicht_acties = 0.9  # iets smaller, nog steeds bruikbaar

    som_gewichten = gewicht_ion + gewicht_schuifjes + gewicht_robot + gewicht_acties

    breedte_ion = int(beschikbaar * (gewicht_ion / som_gewichten))
    breedte_schuifjes = int(beschikbaar * (gewicht_schuifjes / som_gewichten))
    breedte_robot = int(beschikbaar * (gewicht_robot / som_gewichten))
    breedte_acties = beschikbaar - (
        breedte_ion + breedte_schuifjes + breedte_robot
    )  # rest

    kolom1_x = paneel.x + binnen_marge
    kolom2_x = kolom1_x + breedte_ion + kolom_tussenruimte
    kolom3_x = kolom2_x + breedte_schuifjes + kolom_tussenruimte
    kolom4_x = kolom3_x + breedte_robot + kolom_tussenruimte

    # ---- data ----
    niveau = int(ui_state.get("level", 1))
    kleuren = ui_state.get("kleuren", [(220, 60, 60), (60, 200, 90), (70, 130, 240)])
    labels = ui_state["ion_labels"]
    waarden = ui_state.get("values", {})
    vergrendeld = ui_state.get("locked", {})
    verborgen = ui_state.get("verborgen", {})
    knoppen = ui_state.get("buttons", {})
    doel_kleur_index = ui_state.get("target_kleur_index")

    # ------------------
    # ---- kolom 1 ----
    # ------------------
    _teken_tekst(scherm, "Target", kolom1_x, y0)
    niveau_label = pygame.Rect(kolom1_x + 120, y0 - 2, 60, 22)
    pygame.draw.rect(scherm, (35, 35, 44), niveau_label, border_radius=10)
    pygame.draw.rect(scherm, (80, 80, 92), niveau_label, 1, border_radius=10)
    _teken_tekst(
        scherm, f"Lvl {niveau}", niveau_label.x + 10, niveau_label.y + 3, klein=True
    )

    target_rects = _teken_kleurkeuze(
        scherm,
        kolom1_x,
        y0 + 26,
        kleuren,
        doel_kleur_index,
        vergrendeld.get("target", False),
    )
    layout["target_kleur_vakjes"] = target_rects

    invoer_teksten = ui_state.get("ion_invoer", [""] * len(kleuren))
    actief_index = ui_state.get("ion_invoer_actief", None)

    vakjes = _teken_legenda_met_invoer(
        scherm, kolom1_x, y0 + 92, kleuren, labels, invoer_teksten, actief_index
    )
    # teruggeven voor hoofd.py (alleen data, geen input)
    layout["ion_invoer_vakjes"] = vakjes

    # --- knop "Indienen" in legenda (bij antwoord, niet bij acties) ---
    rows = min(len(kleuren), len(labels))
    submit_x = kolom1_x + 100  # sluit aan bij invoervakjes
    submit_y = y0 + rows * 18
    submit_rect = pygame.Rect(submit_x, submit_y, 90, 22)

    _teken_knop(
        scherm,
        submit_rect,
        "Indienen",
        vergrendeld.get("submit", False),
    )
    layout["knoppen"]["submit"] = submit_rect

    # ------------------
    # ---- kolom 2 ----
    # ------------------
    _teken_tekst(scherm, "Instellingen", kolom2_x, y0)

    # Stijl: exact als robotpaneel (zelfde kleuren + radius)
    KAART_VULLING = (28, 28, 34)
    KAART_RAND = (80, 80, 92)
    KAART_RADIUS = 12

    # Lokale tekenhelper: uitsluitend gebruikt binnen teken_ui voor consistente kaart-styling.
    # De helper wordt lokaal gehouden om de publieke API van weergave.py beperkt te houden.
    def _teken_kaart(rechthoek, titel):
        pygame.draw.rect(scherm, KAART_VULLING, rechthoek, border_radius=KAART_RADIUS)
        pygame.draw.rect(scherm, KAART_RAND, rechthoek, 1, border_radius=KAART_RADIUS)
        if titel:
            _teken_tekst(scherm, titel, rechthoek.x + 10, rechthoek.y + 7, klein=True)

    # Layout binnen kolom 2
    kolom2_breedte = breedte_schuifjes
    _zorg_voor_lettertypes()
    kaart_marge_boven = _lettertype_groot.get_linesize() - 6

    kaart_tussenruimte = 5
    kaart_hoogte = 46

    kaart_x = kolom2_x
    kaart_y = y0 + kaart_marge_boven + 6

    # Inwendige padding binnen kaart
    pad_x = 12
    pad_y = 12

    # Sliderbreedtes binnen kaarten
    slider_breedte_half = (kolom2_breedte - 14 - 2 * pad_x) // 2
    slider_breedte_vol = kolom2_breedte - 2 * pad_x

    # Kaart-definities: (titel, [(sleutel, mode, dx_px)])
    # mode: "vol" of "half"
    KAARTEN = [
        ("", [("u_acc_V", "vol", 0)]),
        (
            "",
            [
                ("U_selector_V", "half", 0),
                ("B_selector_T", "half", slider_breedte_half + 14),
            ],
        ),
        ("", [("B_analyse_T", "vol", 0)]),
        ("", [("bundeldichtheid", "vol", 0)]),
    ]

    for titel, items in KAARTEN:
        kaart = pygame.Rect(kaart_x, kaart_y, kolom2_breedte, kaart_hoogte)
        _teken_kaart(kaart, titel)

        # sliders tekenen + rects opslaan
        kaart_locked = False
        for sleutel, mode, dx in items:
            d = _def(sleutel)
            breedte = slider_breedte_vol if mode == "vol" else slider_breedte_half

            _teken_slider(
                scherm,
                kaart.x + pad_x + dx,
                kaart.y + pad_y,
                breedte,
                d["label"],
                waarden.get(sleutel, d["standaard"]),
                eenheid=d["eenheid"],
                decimalen=d["decimalen"],
                verborgen=verborgen.get(sleutel, False),
                min_waarde=d["min"],
                max_waarde=d["max"],
            )

            # Hitbox-registratie:
            # Deze rechthoek wordt gebruikt voor muisinteractie met de slider in interactie.py.
            # Afmetingen volgen de getekende slider (niet de volledige kaart).
            layout["sliders"][sleutel] = pygame.Rect(
                kaart.x + pad_x + dx, kaart.y + pad_y, breedte, 42
            )
            kaart_locked = kaart_locked or bool(vergrendeld.get(sleutel, False))

        if kaart_locked:
            _teken_slot_overlay(scherm, kaart, radius=KAART_RADIUS, alpha=180)

        kaart_y += kaart_hoogte + kaart_tussenruimte

    # ------------------------------------------------------
    # ---- kolom 3 (robot placeholder; alleen tekenen) ----
    # ------------------------------------------------------
    # Robot wordt in robot.py getekend; dit blok tekent uitsluitend het vak (achtergrond + rand)
    # zodat de UI-layout stabiel blijft, ook wanneer robotcontent wisselt.
    robot_marge_boven = 2
    robot_marge_onder = 2
    robot_marge_zijkant = 10  # maakt 'm bewust minder breed dan de kolom

    robot_x = kolom3_x + robot_marge_zijkant
    robot_y = paneel.y + robot_marge_boven
    robot_breedte = max(40, breedte_robot - 2 * robot_marge_zijkant)
    robot_hoogte = max(40, paneel.height - (robot_marge_boven + robot_marge_onder))

    robot_vak = pygame.Rect(robot_x, robot_y, robot_breedte, robot_hoogte)

    pygame.draw.rect(scherm, (28, 28, 34), robot_vak, border_radius=12)
    pygame.draw.rect(scherm, (80, 80, 92), robot_vak, 1, border_radius=12)

    # ------------------
    # ---- kolom 4 ----
    # ------------------
    _teken_tekst(scherm, "Acties", kolom4_x, y0)

    knop_hoogte = 34
    tussenruimte = 5
    knop_breedte = min(200, breedte_acties)
    eerste_knop_y = y0 + 26

    # Start level
    level_status = ui_state.get("level_status", "idle")
    start_level_tekst = "Start level" if level_status != "running" else "Herstart level"

    start_level_rechthoek = pygame.Rect(
        kolom4_x, eerste_knop_y, knop_breedte, knop_hoogte
    )
    _teken_knop(
        scherm,
        start_level_rechthoek,
        start_level_tekst,
        vergrendeld.get("start_level", False),
        actief=(level_status == "running"),
        prominent=True,
    )
    layout["knoppen"]["start_level"] = start_level_rechthoek

    # Volgende knoppen één stap omlaag
    eerste_knop_y += knop_hoogte + tussenruimte

    # Start meting (prominent + status)
    meting_actief = bool(knoppen.get("meting", False))
    meting_tekst = "Meting actief" if meting_actief else "Start meting"

    meting_rechthoek = pygame.Rect(kolom4_x, eerste_knop_y, knop_breedte, knop_hoogte)
    _teken_knop(
        scherm,
        meting_rechthoek,
        meting_tekst,
        vergrendeld.get("meting", False),
        meting_actief,
        prominent=True,
    )
    layout["knoppen"]["meting"] = meting_rechthoek

    # Play/Pause
    pause_rechthoek = pygame.Rect(
        kolom4_x,
        eerste_knop_y + (knop_hoogte + tussenruimte),
        knop_breedte,
        knop_hoogte,
    )
    _teken_knop(
        scherm,
        pause_rechthoek,
        "Play/Pause",
        vergrendeld.get("pause", False),
        knoppen.get("pause", False),
    )
    layout["knoppen"]["pause"] = pause_rechthoek

    # Reset detector
    reset_det_rechthoek = pygame.Rect(
        kolom4_x,
        eerste_knop_y + 2 * (knop_hoogte + tussenruimte),
        knop_breedte,
        knop_hoogte,
    )
    _teken_knop(
        scherm,
        reset_det_rechthoek,
        "Reset detector",
        vergrendeld.get("reset_det", False),
    )
    layout["knoppen"]["reset_det"] = reset_det_rechthoek

    # Reset sim
    reset_sim_rechthoek = pygame.Rect(
        kolom4_x,
        eerste_knop_y + 3 * (knop_hoogte + tussenruimte),
        knop_breedte,
        knop_hoogte,
    )
    _teken_knop(
        scherm,
        reset_sim_rechthoek,
        "Reset sim",
        vergrendeld.get("reset_sim", False),
    )
    layout["knoppen"]["reset_sim"] = reset_sim_rechthoek

    # Eén centrale “output” + backwards compatible keys (gedrag blijft identiek)
    ui_state["layout"] = layout
    ui_state["knop_rechthoeken"] = layout["knoppen"]
    ui_state["slider_rechthoeken"] = layout["sliders"]
    ui_state["target_kleur_vakjes"] = layout["target_kleur_vakjes"]
    ui_state["ion_invoer_vakjes"] = layout["ion_invoer_vakjes"]


def _hist_bepaal_range(
    # Y-range selectie (meters):
    # 1) handmatige zoom (indien ingesteld) voor reproduceerbare inspectie;
    # 2) auto-range rond de gemeten hits voor vergroting van detail;
    # 3) fallback: volledige detectorhoogte wanneer geen meetdata beschikbaar is.
    # De range wordt altijd begrensd tot de fysieke detectorgrenzen.
    hist: dict,
    y_hits: list[float],
    det_y_min_m: float,
    det_y_max_m: float,
) -> tuple[float, float]:
    # 1) Handmatige zoom heeft voorrang indien een zoom_range_m is ingesteld.
    zoom = hist.get("zoom_range_m")
    if zoom and len(zoom) == 2:
        y_min_m = max(det_y_min_m, float(zoom[0]))
        y_max_m = min(det_y_max_m, float(zoom[1]))
        return y_min_m, y_max_m

    # 2) Auto-zoom rond de hits.
    if len(y_hits) >= 2:
        y_lo = min(y_hits)
        y_hi = max(y_hits)
        span_hits = max(1e-9, y_hi - y_lo)

        marge = 0.10 * span_hits
        y_min_m = max(det_y_min_m, y_lo - marge)
        y_max_m = min(det_y_max_m, y_hi + marge)

        # als hits vrijwel gelijk zijn: forceer 2 mm venster
        if (y_max_m - y_min_m) < 0.002:
            mid = 0.5 * (y_min_m + y_max_m)
            y_min_m = max(det_y_min_m, mid - 0.001)
            y_max_m = min(det_y_max_m, mid + 0.001)
        return y_min_m, y_max_m

    # 3) Geen hits → hele detector
    return float(det_y_min_m), float(det_y_max_m)


def _hist_counts(
    y_hits: list[float], bins: int, y_min_m: float, y_max_m: float
) -> list[int]:
    counts = [0] * bins
    # Binning:
    # Detectorhits y (meters) worden uniform over [y_min_m, y_max_m) verdeeld in 'bins' klassen.
    # De output is een frequentieverdeling (aantallen per bin), onafhankelijk van de pixelresolutie.
    span = y_max_m - y_min_m
    if span <= 0:
        return counts

    for y in y_hits:
        if y < y_min_m or y >= y_max_m:
            continue
        k = int((y - y_min_m) / span * bins)
        if 0 <= k < bins:
            counts[k] += 1
    return counts


# Tick-afstand (percentage-as):
# Kies een 'nette' stapgrootte volgens de 1–2–5–10 reeks op orde van grootte.
# Doel: leesbare gridlijnen, onafhankelijk van het absolute maximum.
def _nice_step_pct(x: float) -> float:
    if x <= 0:
        return 1.0
    exp = math.floor(math.log10(x))
    base = 10**exp
    f = x / base
    if f <= 1:
        step = 1
    elif f <= 2:
        step = 2
    elif f <= 5:
        step = 5
    else:
        step = 10
    return step * base


# Tick-afstand (mm-as):
# Zelfde 1–2–5–10 logica als _nice_step_pct, maar toegepast op millimeterlabels.
# Doel: consistente, interpreteerbare x-as labels bij verschillende zoomniveaus.
def _nice_step_mm(x: float) -> float:
    if x <= 0:
        return 0.1
    exp = math.floor(math.log10(x))
    base = 10**exp
    f = x / base
    if f <= 1:
        step = 1
    elif f <= 2:
        step = 2
    elif f <= 5:
        step = 5
    else:
        step = 10
    return step * base


def _hist_x_ticks_mm(
    y_min_m: float,
    y_max_m: float,
    y_ref_m: float,
) -> tuple[float, float, float, str, float, float, float]:
    # Definitie van de x-as (mm):
    # Afstand wordt gedefinieerd t.o.v. een referentielijn onder de detector:
    #   afstand_mm = (y_ref_m - y_m) * 1000
    # Hierdoor kunnen detectorposities als afstanden in mm worden weergegeven.
    #
    # Deze functie bepaalt:
    # - de linker/rechter asgrenzen in mm (op basis van y_min/y_max),
    # - een 'nette' tickafstand (mm) via _nice_step_mm,
    # - en het eerste/laatste ticklabel binnen het bereik.

    d_left_mm = (y_ref_m - y_max_m) * 1000.0
    d_right_mm = (y_ref_m - y_min_m) * 1000.0
    d_min_mm = min(d_left_mm, d_right_mm)
    d_max_mm = max(d_left_mm, d_right_mm)
    d_span_mm = max(1e-9, d_max_mm - d_min_mm)

    rough_step = d_span_mm / 5.0
    step_mm = _nice_step_mm(rough_step)

    if step_mm >= 1.0:
        fmt = "{:.0f} mm"
    elif step_mm >= 0.1:
        fmt = "{:.1f} mm"
    else:
        fmt = "{:.2f} mm"

    tick0 = math.ceil(d_min_mm / step_mm) * step_mm
    tickN = math.floor(d_max_mm / step_mm) * step_mm

    return d_min_mm, d_max_mm, d_span_mm, fmt, tick0, tickN, step_mm


def _hist_teken_y_grid(
    s: pygame.Surface,
    plot: pygame.Rect,
    font_small,
    C_GRID,
    C_AXIS,
    C_TEXT,
    y_top_pct: float,
    step_pct: float,
):
    # Y-grid in procenten:
    # De y-as toont percentages t.o.v. total_hits binnen de gekozen y-range.
    # y_top_pct is een naar boven afgerond maximum, gebaseerd op 'nette' step_pct.

    t = 0.0
    while t <= y_top_pct + 1e-9:
        frac = t / y_top_pct
        y = plot.bottom - int(frac * plot.height)

        pygame.draw.line(s, C_GRID, (plot.left, y), (plot.right, y), 1)
        pygame.draw.line(s, C_AXIS, (plot.left - 4, y), (plot.left, y), 1)

        lbl = font_small.render(f"{int(t)}%", True, C_TEXT)
        s.blit(lbl, (8, y - lbl.get_height() // 2))

        t += step_pct


def _hist_teken_x_grid(
    s: pygame.Surface,
    plot: pygame.Rect,
    font_small,
    C_GRID,
    C_AXIS,
    C_TEXT,
    y_min_m: float,
    y_max_m: float,
    y_ref_m: float,
):
    # X-grid:
    # Tickposities worden berekend in mm (afstand-conventie) en vervolgens lineair teruggezet naar pixel-x.
    # De grid blijft stabiel onder zoom doordat ticks op 'nette' mm-stappen vallen.

    d_min_mm, d_max_mm, d_span_mm, fmt, tick0, tickN, step_mm = _hist_x_ticks_mm(
        y_min_m, y_max_m, y_ref_m
    )

    t = tick0
    max_ticks = 50
    n = 0
    while t <= tickN + 1e-9 and n < max_ticks:
        frac = (t - d_min_mm) / d_span_mm
        x = plot.left + int(frac * plot.width)

        pygame.draw.line(s, C_GRID, (x, plot.top), (x, plot.bottom), 1)
        pygame.draw.line(s, C_AXIS, (x, plot.bottom), (x, plot.bottom + 4), 1)

        lbl = font_small.render(fmt.format(t), True, C_TEXT)
        s.blit(lbl, (x - lbl.get_width() // 2, plot.bottom + 6))

        t += step_mm
        n += 1


def teken_histogram(scherm: pygame.Surface, ui_state: dict):
    """
    Histogram van detectorhits (y in meters) als UI-overlay.
    - Data in SI (meters), alleen tekenen in pixels.
    - Y-as: percentages t.o.v. total_hits binnen range.
    - X-as: afstand (mm) over detectorhoogte (y-range).
    """
    # Motivatie percentage-as:
    # Percentages normaliseren voor het aantal deeltjes/hits en maken runs onderling vergelijkbaar.
    _zorg_voor_lettertypes()
    font_title = _lettertype_groot
    font_small = _lettertype_klein

    hist = ui_state.get("histogram")
    if not hist:
        return

    y_hits = hist.get("y_hits_m", [])
    y_gemiddeld = (sum(y_hits) / len(y_hits)) if y_hits else None
    if not y_hits:
        return

    bins = int(hist.get("bins", 80))
    if bins < 10:
        bins = 10

    # Detector-range in absolute wereldcoördinaten (meters), afgeleid uit wereld.py (DETECTOR_BOVEN).
    det_y_min_m = DETECTOR_BOVEN.top / PX_PER_METER
    det_y_max_m = DETECTOR_BOVEN.bottom / PX_PER_METER

    # Referentiepunt voor x-as-definitie: vaste offset (22 px) onder de detector, om mm-afstanden te labelen.
    REFERENTIE_ONDER_PX = 22
    y_ref_m = (DETECTOR_BOVEN.bottom + REFERENTIE_ONDER_PX) / PX_PER_METER

    y_min_m, y_max_m = _hist_bepaal_range(hist, y_hits, det_y_min_m, det_y_max_m)
    if y_max_m <= y_min_m:
        return

    counts = _hist_counts(y_hits, bins, y_min_m, y_max_m)
    total_hits = sum(counts)
    if total_hits <= 0:
        total_hits = 1

    max_pct = (max(counts) / total_hits) * 100.0 if counts else 0.0
    max_pct = max(1e-6, max_pct)

    step_pct = _nice_step_pct(max_pct / 4.0)
    y_top_pct = math.ceil(max_pct / step_pct) * step_pct
    y_top_pct = max(step_pct, y_top_pct)

    # ---- UI inset (identiek)
    inset_w, inset_h = 360, 220
    inset = pygame.Rect(360, 18, inset_w, inset_h)

    s = pygame.Surface((inset_w, inset_h), pygame.SRCALPHA)

    C_BG = (18, 18, 22, 220)
    C_BORDER = (90, 90, 110, 220)
    C_TEXT = (245, 245, 245)
    C_GRID = (60, 60, 70, 120)
    C_AXIS = (230, 230, 230, 220)

    s.fill(C_BG)
    pygame.draw.rect(s, C_BORDER, s.get_rect(), 1, border_radius=8)

    title = font_title.render("Detectorhits (y)", True, C_TEXT)
    s.blit(title, (10, 8))

    pad_l, pad_r, pad_t, pad_b = 44, 10, 46, 52
    plot = pygame.Rect(pad_l, pad_t, inset_w - pad_l - pad_r, inset_h - pad_t - pad_b)

    _hist_teken_y_grid(s, plot, font_small, C_GRID, C_AXIS, C_TEXT, y_top_pct, step_pct)
    _hist_teken_x_grid(
        s, plot, font_small, C_GRID, C_AXIS, C_TEXT, y_min_m, y_max_m, y_ref_m
    )

    pygame.draw.line(s, C_AXIS, (plot.left, plot.bottom), (plot.right, plot.bottom), 1)
    pygame.draw.line(s, C_AXIS, (plot.left, plot.top), (plot.left, plot.bottom), 1)

    # ---- Gemiddelde-indicator (verticale lijn + vlag) ----
    d_left_mm = (y_ref_m - y_max_m) * 1000.0
    d_right_mm = (y_ref_m - y_min_m) * 1000.0
    d_min_mm = min(d_left_mm, d_right_mm)
    d_max_mm = max(d_left_mm, d_right_mm)
    d_span_mm = max(1e-9, d_max_mm - d_min_mm)

    d_gem_mm = None
    if y_gemiddeld is not None:
        d_gem_mm = (y_ref_m - y_gemiddeld) * 1000.0

    if d_gem_mm is not None and d_min_mm <= d_gem_mm <= d_max_mm:
        frac_g = (d_gem_mm - d_min_mm) / d_span_mm
        x_g = plot.left + int(frac_g * plot.width)

        # verticale lijn door het plot
        pygame.draw.line(s, (255, 90, 90, 230), (x_g, plot.top), (x_g, plot.bottom), 2)

        # klein vlaggetje bovenin
        pygame.draw.line(
            s, (255, 90, 90, 230), (x_g, plot.top - 2), (x_g, plot.top - 14), 2
        )
        pygame.draw.polygon(
            s,
            (255, 90, 90, 230),
            [(x_g, plot.top - 14), (x_g + 12, plot.top - 10), (x_g, plot.top - 6)],
        )

        # label (mm)
        lbl = font_small.render(f"gem = {d_gem_mm:.2f} mm", True, (255, 220, 220))
        s.blit(lbl, (min(x_g + 6, plot.right - lbl.get_width()), plot.top - 28))

    # ---- Bars (identiek per pixelkolom)
    for px in range(plot.width):
        i = int(px / plot.width * bins)
        if i < 0:
            i = 0
        elif i >= bins:
            i = bins - 1

        pct = (counts[i] / total_hits) * 100.0
        h = int((pct / y_top_pct) * plot.height)
        x = plot.left + px
        y_top = plot.bottom - h

        # Altijd-zichtbare balk (geen alpha): voorkomt “ik zie niks”-effect
        frac_kleur = max(0.0, min(1.0, pct / y_top_pct))
        r = int(70 + 160 * frac_kleur)
        g = int(190 - 90 * frac_kleur)
        b = int(255 - 60 * frac_kleur)

        pygame.draw.line(s, (r, g, b), (x, plot.bottom), (x, y_top), 1)

    note = font_small.render(
        f"Bins: {bins}   Hits: {len(y_hits)}", True, (235, 235, 235)
    )
    s.blit(note, (10, inset_h - 16))

    scherm.blit(s, inset.topleft)


# -------------------------------------------------------------
# Private helpers: generiek tekenen
# -------------------------------------------------------------
def _zorg_voor_lettertypes():
    global _lettertype_groot, _lettertype_klein
    if _lettertype_groot is None:
        _lettertype_groot = get_font(22)
    if _lettertype_klein is None:
        _lettertype_klein = get_font(18)


def _teken_paneel(scherm, rechthoek):
    """Tekent een paneel met achtergrond + rand."""
    pygame.draw.rect(scherm, (40, 40, 48), rechthoek, border_radius=12)
    pygame.draw.rect(scherm, (100, 100, 112), rechthoek, 1, border_radius=12)


def _teken_tekst(scherm, tekst, x, y, kleur=(235, 235, 235), klein=False):
    _zorg_voor_lettertypes()
    font = _lettertype_klein if klein else _lettertype_groot
    oppervlak = font.render(tekst, True, kleur)
    scherm.blit(oppervlak, (x, y))


def _teken_slot_overlay(scherm, rechthoek, radius=12, alpha=170):
    """
    Donkere overlay die exact over een kaart/paneeltje valt,
    inclusief afgeronde hoeken (zelfde stijl als kaartjes/robot).
    """
    overlay = pygame.Surface((rechthoek.width, rechthoek.height), pygame.SRCALPHA)

    # Rond vlak (dus geen “rechte” hoeken die buiten het kaartje vallen)
    pygame.draw.rect(
        overlay,
        (0, 0, 0, alpha),
        overlay.get_rect(),
        border_radius=radius,
    )
    scherm.blit(overlay, rechthoek.topleft)

    # Randje zoals de kaarten
    pygame.draw.rect(scherm, (110, 110, 120), rechthoek, 1, border_radius=radius)

    # LOCK-badge rechtsboven (zoals in jouw UI) + tekst perfect gecentreerd
    _zorg_voor_lettertypes()
    font = _lettertype_klein
    txt = "LOCK"
    txt_w, txt_h = font.size(txt)

    badge_pad = 8
    badge_w = max(54, txt_w + 16)
    badge_h = max(18, txt_h + 6)

    badge_x = rechthoek.right - badge_w - badge_pad
    badge_y = rechthoek.top + badge_pad
    badge = pygame.Rect(badge_x, badge_y, badge_w, badge_h)

    pygame.draw.rect(scherm, (40, 40, 48), badge, border_radius=8)
    pygame.draw.rect(scherm, (120, 120, 130), badge, 1, border_radius=8)

    tx = badge.centerx - txt_w // 2
    ty = badge.centery - txt_h // 2
    scherm.blit(font.render(txt, True, (235, 235, 235)), (tx, ty))


def _formatteer_waarde(waarde, eenheid, decimalen=2):
    try:
        return f"{float(waarde):.{decimalen}f} {eenheid}".rstrip()
    except Exception:
        return f"{waarde} {eenheid}".rstrip()


def _def(sleutel):
    return SLIDER_DEFINITIES[sleutel]


# -------------------------------------------------------------
# Private helpers: specifieke UI-elementen
# -------------------------------------------------------------
def _teken_slider(
    scherm,
    x,
    y,
    breedte,
    label,
    waarde,
    *,
    eenheid,
    decimalen,
    verborgen,
    min_waarde,
    max_waarde,
):
    _zorg_voor_lettertypes()
    font = _lettertype_klein

    # Compacte slider: 1 tekstregel (label links, waarde rechts) + baan
    top_pad = 4
    baan_pad_top = 4
    baan_hoogte = 6
    knop_straal = 7

    # Tekstregel
    tekst_y = y + top_pad
    scherm.blit(font.render(label, True, (235, 235, 235)), (x, tekst_y))

    waarde_tekst = (
        "???" if verborgen else _formatteer_waarde(waarde, eenheid, decimalen)
    )
    vw, vh = font.size(waarde_tekst)
    scherm.blit(
        font.render(waarde_tekst, True, (235, 235, 235)), (x + breedte - vw, tekst_y)
    )

    # Baan direct onder tekst
    baan_y = tekst_y + font.get_linesize() + baan_pad_top
    pygame.draw.rect(
        scherm,
        (85, 85, 95),
        pygame.Rect(x, baan_y, breedte, baan_hoogte),
        border_radius=3,
    )

    # Knop positie
    try:
        v = float(waarde)
        if float(max_waarde) == float(min_waarde):
            positie = 0.0
        else:
            positie = (v - float(min_waarde)) / (float(max_waarde) - float(min_waarde))
        positie = max(0.0, min(1.0, positie))
    except Exception:
        positie = 0.0

    knop_x = int(x + positie * breedte)
    knop_y = baan_y + baan_hoogte // 2
    pygame.draw.circle(scherm, (230, 230, 230), (knop_x, knop_y), knop_straal)


def _teken_knop(scherm, rechthoek, tekst, vergrendeld, actief=False, prominent=False):
    # Basiskleuren
    if prominent and not vergrendeld:
        # Opvallende "meting"-knop: 3D/shadow + glow
        schaduw = rechthoek.move(3, 3)
        pygame.draw.rect(scherm, (8, 8, 10), schaduw, border_radius=12)

        achtergrond = (60, 55, 20) if actief else (55, 48, 18)  # warm/meetkleurig
        pygame.draw.rect(scherm, achtergrond, rechthoek, border_radius=12)

        # Highlight randen (3D)
        pygame.draw.line(
            scherm,
            (235, 235, 245),
            (rechthoek.left + 4, rechthoek.top + 4),
            (rechthoek.right - 5, rechthoek.top + 4),
            2,
        )
        pygame.draw.line(
            scherm,
            (235, 235, 245),
            (rechthoek.left + 4, rechthoek.top + 4),
            (rechthoek.left + 4, rechthoek.bottom - 5),
            2,
        )

        # Glow rand
        pygame.draw.rect(scherm, (255, 200, 0), rechthoek, 2, border_radius=12)

    else:
        # Jouw bestaande rustige stijl
        achtergrond = (50, 50, 62) if actief else (30, 30, 36)
        pygame.draw.rect(scherm, achtergrond, rechthoek, border_radius=10)
        pygame.draw.rect(scherm, (80, 80, 92), rechthoek, 1, border_radius=10)

    # Tekst
    _zorg_voor_lettertypes()
    oppervlak = _lettertype_groot.render(tekst, True, (235, 235, 235))
    scherm.blit(
        oppervlak,
        (
            rechthoek.centerx - oppervlak.get_width() // 2,
            rechthoek.centery - oppervlak.get_height() // 2,
        ),
    )

    # Lock overlay
    if vergrendeld:
        _teken_slot_overlay(scherm, rechthoek)


def _teken_kleurkeuze(scherm, x, y, kleuren, geselecteerd_index, vergrendeld):
    _teken_tekst(scherm, "Kies target-ion (kleur)", x, y)
    vak = 22
    tussenruimte = 8
    y0 = y + 26

    rects = []
    for i, kleur in enumerate(kleuren):
        rechthoek = pygame.Rect(x + i * (vak + tussenruimte), y0, vak, vak)
        rects.append(rechthoek)

        pygame.draw.rect(scherm, kleur, rechthoek, border_radius=4)
        pygame.draw.rect(scherm, (90, 90, 100), rechthoek, 1, border_radius=4)

        if geselecteerd_index == i:
            pygame.draw.rect(
                scherm,
                (245, 245, 245),
                rechthoek.inflate(6, 6),
                2,
                border_radius=6,
            )

    if vergrendeld:
        totale_breedte = len(kleuren) * vak + (len(kleuren) - 1) * tussenruimte
        _teken_slot_overlay(
            scherm,
            pygame.Rect(x - 6, y0 - 6, totale_breedte + 12, vak + 12),
            radius=10,
            alpha=180,
        )

    return rects


def _teken_legenda_met_invoer(
    scherm, x, y, kleuren, labels, invoer_teksten, actief_index
):
    _teken_tekst(scherm, "Legenda", x, y)
    yy = y + 24

    vakjes = []
    vak_x = x + 100
    vak_breedte = 70
    vak_hoogte = 18

    for i in range(min(len(kleuren), len(labels))):
        pygame.draw.rect(
            scherm, kleuren[i], pygame.Rect(x, yy + i * 22, 14, 14), border_radius=3
        )
        _teken_tekst(scherm, labels[i], x + 20, yy + i * 22 + 2, klein=True)

        r = pygame.Rect(vak_x, yy + i * 22 - 1, vak_breedte, vak_hoogte)

        randkleur = (200, 200, 220) if (actief_index == i) else (80, 80, 92)
        pygame.draw.rect(scherm, (30, 30, 36), r, border_radius=6)
        pygame.draw.rect(scherm, randkleur, r, 1, border_radius=6)

        tekst = invoer_teksten[i] if i < len(invoer_teksten) else ""
        _zorg_voor_lettertypes()
        font = _lettertype_klein
        txt = tekst if tekst else "...."
        th = font.size(txt)[1]
        tx = r.x + 8
        ty = r.centery - th // 2
        scherm.blit(font.render(txt, True, (235, 235, 235)), (tx, ty))

        vakjes.append(r)

    return vakjes


def teken_ionenkaart(scherm: pygame.Surface, ui_state: dict):
    """
    Render-only overlay: toont ionenkaart boven de analysekamer.
    - Nette kolommen met vaste x-posities (geen spatie-uitlijning).
    - Scroll via ui_state["ionenkaart_scroll"] (muiswiel boven analysekamer).
    """
    if not ui_state.get("show_ionenkaart", False):
        return

    items = ui_state.get("ionenkaart_items", [])
    if not items:
        return

    _zorg_voor_lettertypes()
    font_title = _lettertype_groot
    font_small = _lettertype_klein

    inset = ANALYSEKAMER.inflate(-16, -16)

    s = pygame.Surface((inset.width, inset.height), pygame.SRCALPHA)
    C_BG = (14, 18, 26, 220)
    C_BORDER = (210, 235, 255, 210)
    C_TEXT = (245, 250, 255)
    C_DIM = (205, 215, 230)

    s.fill(C_BG)
    pygame.draw.rect(s, C_BORDER, s.get_rect(), 1, border_radius=10)

    title = font_title.render("Ionenkaart", True, C_TEXT)
    s.blit(title, (12, 10))

    # Korte hint die NOOIT buiten beeld valt
    hint_txt = "Wiel: scroll  |  RMB: sluit"
    hint = font_small.render(hint_txt, True, C_DIM)
    hint_x = max(12, inset.width - hint.get_width() - 12)
    s.blit(hint, (hint_x, 14))

    # Sorteer stabiel
    items_sorted = sorted(
        items,
        key=lambda d: (
            float(d.get("massa_u", 0.0)),
            int(d.get("lading_e", 0)),
            str(d.get("code", "")),
        ),
    )

    # Layout
    x0 = 12
    y0 = 44
    regel_h = 18

    # Kolommen (vaste pixels)
    col_code = x0
    col_massa = x0 + 150
    col_q = x0 + 270

    # Header
    s.blit(font_small.render("ion", True, C_DIM), (col_code, y0))
    s.blit(font_small.render("massa (u)", True, C_DIM), (col_massa, y0))
    s.blit(font_small.render("q", True, C_DIM), (col_q, y0))
    y = y0 + regel_h + 2

    max_regels = max(4, (inset.height - y - 24) // regel_h)

    # Scroll clamp
    scroll = int(ui_state.get("ionenkaart_scroll", 0))
    scroll = max(0, min(scroll, max(0, len(items_sorted) - max_regels)))
    ui_state["ionenkaart_scroll"] = (
        scroll  # Render-only normalisatie van scroll-offset (geen fysische invloed).
    )

    start = scroll
    end = min(len(items_sorted), start + max_regels)

    for it in items_sorted[start:end]:
        code = str(it.get("code", ""))
        massa_u = float(it.get("massa_u", 0.0))
        lading_e = int(it.get("lading_e", 0))
        qtxt = (
            f"{lading_e}+" if lading_e > 0 else (f"{lading_e}" if lading_e < 0 else "0")
        )

        s.blit(font_small.render(code, True, C_TEXT), (col_code, y))
        s.blit(font_small.render(f"{massa_u:.3f}", True, C_TEXT), (col_massa, y))
        s.blit(font_small.render(qtxt, True, C_TEXT), (col_q, y))
        y += regel_h

    footer = font_small.render(f"{start+1}-{end} / {len(items_sorted)}", True, C_DIM)
    s.blit(footer, (12, inset.height - 18))

    scherm.blit(s, inset.topleft)


def teken_formulekaart(scherm: pygame.Surface, ui_state: dict):
    """
    Render-only overlay: formulekaart linksboven.
    Nu met scroll (muiswiel boven kaart): ui_state["formulekaart_scroll_px"].
    """
    _zorg_voor_lettertypes()
    font_title = _lettertype_groot
    font_small = _lettertype_klein

    inset_w, inset_h = 330, 220
    inset = pygame.Rect(18, 18, inset_w, inset_h)

    # Exporteer rechthoek voor hit-testing.
    # interactie.py gebruikt deze layout-rect als bron van waarheid voor scroll-detectie.
    layout = ui_state.setdefault("layout", {})
    overlays = layout.setdefault("overlays", {})
    overlays["formulekaart"] = inset

    # Styling (zelfde familie als ionenkaart/histogram)
    C_BG = (14, 18, 26, 190)
    C_BORDER = (210, 235, 255, 210)
    C_TEXT = (245, 250, 255)
    C_DIM = (190, 210, 230)

    s = pygame.Surface((inset_w, inset_h), pygame.SRCALPHA)
    s.fill(C_BG)
    pygame.draw.rect(s, C_BORDER, s.get_rect(), 1, border_radius=8)

    title = font_title.render("Formules (ion bepalen)", True, C_TEXT)
    s.blit(title, (12, 10))

    # Inhoud (regels)
    regels = [
        ("Versneller:", C_DIM),
        ("½ m v² = q·Uacc", C_TEXT),
        ("→ v = √(2 q Uacc / m)", C_TEXT),
        ("", C_TEXT),
        ("Selector (E×B):", C_DIM),
        ("E = Uselector / d", C_TEXT),
        ("v = E / Bselector", C_TEXT),
        ("d = 6,0 mm (plaatafstand)", C_TEXT),
        ("", C_TEXT),
        ("Analysekamer (B):", C_DIM),
        ("r = (m v) / (q Banalyse)", C_TEXT),
        ("D = 2r  (let op: D is diameter, weergegeven in het histogram)", C_TEXT),
        ("", C_TEXT),
        ("Combineren:", C_DIM),
        ("m/q = (r·B)/v", C_TEXT),
        ("→ match m/q met ionenkaart", C_TEXT),
    ]

    footer = "Scroll met muiswiel"

    # Viewport (ruimte tussen titel en footer)
    pad_l, pad_r = 12, 12
    pad_top = 44
    pad_bottom = 26  # ruimte voor footer
    view = pygame.Rect(
        pad_l, pad_top, inset_w - pad_l - pad_r, inset_h - pad_top - pad_bottom
    )

    # Bouw “layout items” met vaste hoogtes zodat scroll robuust is
    regel_h = font_small.get_linesize()
    spacer_h = 8  # voor lege regels

    items = []
    for txt, kleur in regels:
        if txt == "":
            items.append(("__SPACER__", None, spacer_h))
        else:
            items.append((txt, kleur, regel_h))

    content_h = sum(h for _, _, h in items)
    max_scroll = max(0, content_h - view.height)

    scroll_px = int(ui_state.get("formulekaart_scroll_px", 0))
    scroll_px = max(0, min(max_scroll, scroll_px))
    ui_state["formulekaart_scroll_px"] = (
        scroll_px  # Render-only normalisatie van scroll-offset.
    )

    # Clip tekenen binnen viewport: render alleen zichtbare items
    y_cursor = view.top - scroll_px
    for txt, kleur, h in items:
        if y_cursor + h < view.top:
            y_cursor += h
            continue
        if y_cursor > view.bottom:
            break

        if txt != "__SPACER__":
            s.blit(font_small.render(txt, True, kleur), (view.left, y_cursor))
        y_cursor += h

    # Footer + scroll-indicator
    s.blit(font_small.render(footer, True, C_DIM), (12, inset_h - 18))
    if max_scroll > 0:
        info = f"scroll {scroll_px}/{max_scroll}"
        s.blit(
            font_small.render(info, True, C_DIM),
            (inset_w - 12 - font_small.size(info)[0], inset_h - 18),
        )

    scherm.blit(s, inset.topleft)
