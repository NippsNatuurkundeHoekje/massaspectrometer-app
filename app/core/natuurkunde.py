# ************************************************************
# ** Fysica-engine: beweging van deeltjes in E- en B-velden **
# ************************************************************
# Dit bestand bevat de natuurkundige kern van het model.
# Hier wordt de beweging van ionen berekend op basis van elektrische
# en magnetische velden volgens de Lorentzkracht.
#
# AANNAMES:
# - Ionen worden gemodelleerd als puntdeeltjes
# - Er is geen interactie tussen ionen onderling
# - Elektrische en magnetische velden zijn homogeen
# - Het model is tweedimensionaal (x,y)
# - Relativistische effecten worden genegeerd

# OPBOUW VAN HET MODEL IN DIT BESTAND:
# 1) Veldfuncties: elektrisch_veld(...) en magnetisch_veld_z(...)
#    -> leveren per regio het veld terug op basis van instellingen (schaalfactoren kunnen aanwezig zijn).
# 2) Hulpfuncties voor startwaarden/locks (level-engine):
#    -> bereken_v_uit_u_acc_sim, bereken_u_selector_voor_v_sim, kies_u_acc_locked_binnen_detector
# 3) Bewegingsintegrator:
#    -> boris_stap_2d(...) voor stabiele integratie met magnetisch veld
# 4) Update-loop:
#    -> update_deeltjes(...) voert de recursieve tijdstap uit, doet botsingsdetectie en maakt detector-hits.


# Standaard bibliotheek imports
import math
import random

# Projectmodules imports
from dataclasses import dataclass
from app.core.wereld import (
    bepaal_locatie_id_met_muis,
    bepaal_contact_m,
    clamp_naar_detector_m,
    CONTACT_DETECTOR,
    LOCATIE_VERSNELLINGSVELD,
    LOCATIE_SELECTORVELD,
    LOCATIE_ANALYSEKAMER,
    CONTACT_WAND,
)

from app.config.configuratie import (
    SELECTOR_PLAATAFSTAND_M,
    UACC_VOLT,
    ACCELERATIE_PLAATAFSTAND_M,
    SIMULATIE_SCHAAL_EVELD,
    B_ANALYSE_TESLA,
    SIMULATIE_SCHAAL_BVELD,
    B_SELECTOR_TESLA,
    U_SELECTOR_VOLT,
    SIMULATIE_SCHAAL_ESELECTOR,
    SIMULATIE_SCHAAL_BSELECTOR,
    MAX_STEP_PX,
    PX_PER_METER,
    MAX_SUBSTEPS,
)


# DetectorHit is een meetresultaat:
# wanneer een deeltje de detector raakt, slaan we de (x,y)-positie op in meters.
# Deze data wordt later gebruikt voor histogrammen/visualisatie.
@dataclass(frozen=True)
class DetectorHit:
    x_m: float
    y_m: float
    kleur: tuple
    detector_id: str


# Deeltje beschrijft één ion in het model.
# Grootheden:
# - (x_m, y_m): positie in meters
# - (vx, vy): snelheid in m/s
# - m_kg: massa in kg
# - q_c: lading in Coulomb (teken bepaalt kromrichting)
# - straal_m: kleine "fysieke" straal voor botsingsdetectie (visueel mag groter zijn)
@dataclass
class Deeltje:
    x_m: float
    y_m: float
    vx: float
    vy: float
    straal_m: float
    kleur: tuple[int, int, int]
    m_kg: float
    q_c: float
    actief: bool = True


# Elektrisch veld per regio:
# - Versnellingsveld: E = U_acc / d_acc
# - Selectorveld:     E = U_sel / d_sel
# Eventuele schaalfactoren (in configuratie) staan toe om numerieke stabiliteit/visualisatie af te stemmen.
# Bij schaal = 1.0 vallen deze factoren weg en blijft de formule E = U/d ongewijzigd.
# Richtingconventie in dit model:
# - In het versnellingsveld werkt het elektrische veld langs de x-as (Ex) en veroorzaakt het versnelling in x-richting.
# - In de snelheidsselector werkt het elektrische veld langs de y-as (Ey) en compenseert het (idealiter) de magnetische afbuiging.
# De functienaam levert de veldsterkte (scalaire grootte) terug; de componentkeuze (Ex of Ey) gebeurt in update_deeltjes(...).
def elektrisch_veld(locatie_id: str, instellingen: dict) -> float:
    if locatie_id == LOCATIE_VERSNELLINGSVELD:
        u_acc_v = instellingen.get("u_acc_V", UACC_VOLT)
        # E_acc = U/d (homogeen veld tussen platen); SIMULATIE_SCHAAL_EVELD is configureerbaar (nu 1.0).
        return (u_acc_v / ACCELERATIE_PLAATAFSTAND_M) * SIMULATIE_SCHAAL_EVELD
    if locatie_id == LOCATIE_SELECTORVELD:
        u_sel = instellingen.get("U_selector_V", U_SELECTOR_VOLT)
        # E_sel = U/d (homogeen veld in selector); SIMULATIE_SCHAAL_ESELECTOR is configureerbaar (nu 1.0).
        return (u_sel / SELECTOR_PLAATAFSTAND_M) * SIMULATIE_SCHAAL_ESELECTOR
    return 0.0


# Magnetisch veld staat in dit 2D-model loodrecht op het scherm (z-richting).
# Daardoor werkt de Lorentzkracht q(v × B) als een kromming van de baan in het (x,y)-vlak.
# Eventuele schaalfactoren zijn configureerbaar; bij schaal = 1.0 blijft B ongewijzigd.
# In 2D wordt B uitsluitend als z-component gemodelleerd.
# Daardoor geldt voor v=(vx,vy,0) dat v×B leidt tot een versnelling in het (x,y)-vlak.
# Het teken van q bepaalt de kromrichting; het teken van bz bepaalt de draairichting van het veld.
def magnetisch_veld_z(locatie_id: str, instellingen: dict) -> float:
    if locatie_id == LOCATIE_ANALYSEKAMER:
        b = instellingen.get("B_analyse_T", B_ANALYSE_TESLA)
        return b * SIMULATIE_SCHAAL_BVELD
    if locatie_id == LOCATIE_SELECTORVELD:
        b = instellingen.get("B_selector_T", B_SELECTOR_TESLA)
        return b * SIMULATIE_SCHAAL_BSELECTOR
    return 0.0


# Afgeleide grootheden voor UI/diagnostiek:
# - E_selector = U_selector / d
# - v_selectie = E_selector / B_selector  (ideale selectorvoorwaarde)
# Deze waarden sturen de integratie niet aan; ze worden uitsluitend ter informatie opgeslagen in ui_state["meters"].
def bereken_selector_meters(instellingen: dict) -> dict:
    """Geef afgeleide grootheden voor de snelheidsselector terug (voor UI)."""
    u_sel = float(instellingen.get("U_selector_V", U_SELECTOR_VOLT))
    b_sel = float(instellingen.get("B_selector_T", B_SELECTOR_TESLA))

    # E = U/d
    if SELECTOR_PLAATAFSTAND_M > 0:
        e_sel = u_sel / SELECTOR_PLAATAFSTAND_M
    else:
        e_sel = 0.0

    # v = E/B
    if abs(b_sel) > 1e-12:
        v_sel = e_sel / b_sel
    else:
        v_sel = 0.0

    # Opmerking: de integrator gebruikt rechtstreeks de instellingen (U_selector_V, B_selector_T) via elektrisch_veld(...)
    # en magnetisch_veld_z(...). De hier berekende waarden zijn afgeleide grootheden voor interpretatie/rapportage.
    return {"E_selector_Vpm": e_sel, "v_selectie_ms": v_sel}


# --- helpers voor level-engine / startwaarden (gebaseerd op simulatie-schaal) ---
# LET OP (architectuur):
# Deze helpers horen conceptueel bij "instellingen kiezen" (policy/level-engine).
# Ze staan hier omdat ze direct leunen op de geschaalde sim-grootheden.
# De bewegingsfysica zelf zit in boris_stap_2d(...) en update_deeltjes(...).


def _haal_q_m_uit_ion(ion) -> tuple[float, float]:
    """
    Ondersteunt zowel Ion (ionen.py) als Deeltje (natuurkunde.py):
    - Ion: massa_kg, lading_c
    - Deeltje: m_kg, q_c
    Geeft (q_abs, m) terug.
    """
    m = getattr(ion, "massa_kg", None)
    if m is None:
        m = getattr(ion, "m_kg", 0.0)
    q = getattr(ion, "lading_c", None)
    if q is None:
        q = getattr(ion, "q_c", 0.0)
    try:
        m = float(m)
        q = float(q)
    except Exception:
        return 0.0, 0.0
    return abs(q), m


# Startwaarde-berekening (policy):
# Deze functie wordt gebruikt om een beginsnelheid te kiezen die consistent is met een gekozen U_acc.
# De uitkomst is een initialisatie; de verdere baan volgt uit numerieke integratie in update_deeltjes(...).
def bereken_v_uit_u_acc_sim(u_acc_v: float, ion) -> float:
    """
    Snelheid na versnelling, consistent met het simulatieveld:
    E_acc wordt geschaald met SIMULATIE_SCHAAL_EVELD.
    Werk/energie in sim: q * U_acc * SIMULATIE_SCHAAL_EVELD.
    """
    # Theorie:
    # Versnellen over potentiaalverschil U geeft kinetische energie:
    #   q * U_eff = 1/2 m v^2
    # => v = sqrt(2 q U_eff / m)
    # In deze simulatie gebruiken we U_eff = U * SIMULATIE_SCHAAL_EVELD.
    q_abs, m = _haal_q_m_uit_ion(ion)
    if q_abs <= 0.0 or m <= 0.0:
        return 0.0
    u = float(u_acc_v)
    if u <= 0.0:
        return 0.0
    # v = sqrt(2 q U_eff / m), met U_eff = U * SIMULATIE_SCHAAL_EVELD
    return (2.0 * q_abs * u * float(SIMULATIE_SCHAAL_EVELD) / m) ** 0.5


# Instrumentinstelling (policy):
# Deze functie bepaalt een U_selector die hoort bij een gewenste doorlaatsnelheid v.
# Dit ondersteunt levels waarbij instellingen automatisch gekozen worden, zonder het antwoord te verklappen.
def bereken_u_selector_voor_v_sim(v_ms: float, b_selector_t: float) -> float:
    """
    Kies U_selector zodat de selector in de sim 'recht' is:
    Voorwaarde in sim: E_sim = v * B_sim
    E_sim = (U/d) * SIMULATIE_SCHAAL_ESELECTOR
    B_sim = B * SIMULATIE_SCHAAL_BSELECTOR
    => U = v * B * d * (SIMULATIE_SCHAAL_BSELECTOR / SIMULATIE_SCHAAL_ESELECTOR)
    """
    # Selectorvoorwaarde (ideaal):
    # qE en q(v×B) moeten elkaar opheffen -> E = vB -> v = E/B.
    # Hier rekenen we terug welke U_selector nodig is voor een gewenste v (binnen de sim-schalen).
    v = float(v_ms)
    b = float(b_selector_t)
    if v <= 0.0 or abs(b) <= 1e-12:
        return 0.0
    schaal = float(SIMULATIE_SCHAAL_BSELECTOR) / float(SIMULATIE_SCHAAL_ESELECTOR)
    return v * b * float(SELECTOR_PLAATAFSTAND_M) * schaal


def kies_u_acc_locked_binnen_detector(
    pool: list,
    b_analyse_max_T: float,
    detector_lengte_m: float,
    marge_m: float = 0.005,
    u_min: float = 100.0,
    u_max: float = 40000.0,
) -> float:
    """
    Kies Uacc zó dat het 'worst-case' ion (max m/q) in deze run bij B_analyse_max
    een diameter D <= detector_lengte_m - marge_m kan hebben.
    Borgt meetbaarheid in locked levels (zonder inhoudelijke aanwijzing over het juiste antwoord; alleen instrument-instelling).

    Afleiding:
      r = m v / (q B), D = 2r
      v = sqrt(2 q U_eff / m), U_eff = U * SIMULATIE_SCHAAL_EVELD
      => D = (2/B) * sqrt(2 m U_eff / q)
      => U = ( (D*B/2)^2 ) * (q/(2m)) / SIMULATIE_SCHAAL_EVELD
    """
    # Didactisch/experimenteel doel:
    # In locked levels wordt U_acc vastgezet, maar de meetopstelling moet een detecteerbaar spoor opleveren.
    # Daarom wordt U_acc zodanig gekozen dat zelfs het worst-case ion (grootste m/q) bij B_analyse_max
    # binnen de detectorlengte blijft (meetbaarheid als randvoorwaarde, geen inhoudelijke hint).
    if not pool:
        return float(UACC_VOLT)

    # worst-case = grootste m/q
    max_m_over_q = 0.0
    for ion in pool:
        q, m = _haal_q_m_uit_ion(ion)
        if q > 0.0 and m > 0.0:
            max_m_over_q = max(max_m_over_q, m / q)

    if max_m_over_q <= 0.0:
        return float(UACC_VOLT)

    frac = random.uniform(0.5, 0.9)
    D = max(0.001, frac * (detector_lengte_m - marge_m))
    B = float(b_analyse_max_T)
    if B <= 0.0:
        return float(UACC_VOLT)

    # q/m = 1/(m/q)
    q_over_m = 1.0 / max_m_over_q
    U_eff = ((D * B) / 2.0) ** 2 * (q_over_m / 2.0)
    U = U_eff / float(SIMULATIE_SCHAAL_EVELD)

    return max(float(u_min), min(float(u_max), float(U)))


def boris_stap_2d(ion: Deeltje, ex: float, ey: float, bz: float, dt: float):
    """
    Boris-integrator (2D) voor geladen deeltjes in velden E=(ex,ey,0) en B=(0,0,bz).

    Doel:
    - Numeriek stabiele integratie van de Lorentzkracht: F = q(E + v × B).
    - Bij uitsluitend magnetisch veld (E=0) blijft de snelheidsgrootte fysisch constant
      (B verricht geen arbeid). De Boris-methode benadert dit gedrag beter dan een
      expliciete Euler-stap.

    Methode (schematisch):
    1) Half-step elektrische impuls ("half E-kick")
    2) Rotatie van de snelheid door het magnetisch veld (B-rotatie)
    3) Half-step elektrische impuls ("half E-kick")

    Vergelijking met expliciete Euler:
    - Euler (expliciet): v_{n+1} = v_n + a_n·dt, x_{n+1} = x_n + v_n·dt
      Bij rotatieproblemen kan Euler numeriek energie/drift introduceren (stabiliteitsprobleem).
    - Boris: splitst E en B zodanig dat de B-stap een (bij benadering) zuivere rotatie is.
    """

    # q_over_m = q/m bepaalt de koppeling tussen velden en versnelling/rotatie.
    q_over_m = ion.q_c / ion.m_kg

    # Numerieke structuur:
    # De snelheid wordt eerst half aangepast door E (impuls).
    # Daarna volgt een rotatiestap door B die (bij E=0) de snelheidsgrootte conserveert.
    # Tot slot volgt de tweede halve E-impuls. Deze symmetrische opbouw vermindert numerieke drift.

    # 1) half E-kick
    vx_min = ion.vx + q_over_m * ex * (0.5 * dt)
    vy_min = ion.vy + q_over_m * ey * (0.5 * dt)

    # 2) B-rotatie
    # Rotatie-parameter:
    # t = (q/m) * B * (dt/2). Dit is de dimensionloze maat voor de rotatiehoek (voor kleine hoeken: t ≈ θ/2).
    # s = 2t/(1+t^2) volgt uit de algebra van de Boris-rotatie en zorgt voor een stabiele, bij benadering
    # orthogonale rotatie van de snelheid in het (x,y)-vlak.
    t = q_over_m * bz * (0.5 * dt)  # scalar (tz)
    s = 2.0 * t / (1.0 + t * t)  # scalar

    # B-effect:
    # Het magnetische deel van de Lorentzkracht is q(v×B). In 2D met B in z-richting levert dit
    # een rotatie van de snelheidsvector in het (x,y)-vlak.
    # v' = v- + v- x t  (t in z-richting)
    # (vx, vy, 0) x (0,0,t) = (vy*t, -vx*t, 0)
    vx_prime = vx_min + vy_min * t
    vy_prime = vy_min - vx_min * t

    # v+ = v- + v' x s
    # (vx', vy', 0) x (0,0,s) = (vy'*s, -vx'*s, 0)
    vx_plus = vx_min + vy_prime * s
    vy_plus = vy_min - vx_prime * s

    # 3) half E-kick
    ion.vx = vx_plus + q_over_m * ex * (0.5 * dt)
    ion.vy = vy_plus + q_over_m * ey * (0.5 * dt)


# update_deeltjes(...) is de recursieve tijdstap van het model:
# Voor elk deeltje wordt de toestand iteratief bijgewerkt:
#   (x, y, vx, vy)_{t+dt} hangt af van (x, y, vx, vy)_{t}
# Dit gebeurt per frame met een vaste dt, eventueel opgesplitst in sub-tijdstappen (dt_sub)
# om botsingsdetectie en stabiliteit te verbeteren.
def update_deeltjes(deeltjes, dt, instellingen=None):
    hits = []
    if instellingen is None:
        instellingen = {}

    # max_step_m bepaalt de maximale verplaatsing per (sub)stap in meters.
    # Dit voorkomt dat een deeltje "door" een wand/detector heen springt bij grote snelheden.
    max_step_m = MAX_STEP_PX / PX_PER_METER

    for ion in deeltjes:
        if not ion.actief:
            continue

        # Veiligheidsstop:
        # Als een deeltje numeriek "explodeert" (extreme snelheden/posities), wordt het uitgezet.
        # Dit is geen fysica-keuze, maar voorkomt vastlopers door instabiele parameters.
        if (
            abs(ion.vx) > 1e7
            or abs(ion.vy) > 1e7
            or abs(ion.x_m) > 1e4
            or abs(ion.y_m) > 1e4
        ):
            ion.actief = False
            continue

        # Bepaal hoeveel substeps nodig zijn op basis van verwachte verplaatsing dit frame
        # (afstand per frame, niet "snelheid-drempel").
        dx = ion.vx * dt
        dy = ion.vy * dt
        stap_lengte = math.hypot(dx, dy)
        n_sub = (
            1 if stap_lengte <= max_step_m else int(math.ceil(stap_lengte / max_step_m))
        )
        if n_sub > MAX_SUBSTEPS:
            n_sub = MAX_SUBSTEPS

        dt_sub = dt / n_sub

        # Sub-tijdstappen binnen één frame beperken grote sprongen.
        # Dit verhoogt de nauwkeurigheid van botsingsdetectie en contactclassificatie.
        # Visualisatie wordt nog steeds per frame bijgewerkt; de dynamica wordt berekend met dt_sub.
        # 'substep' is uitsluitend een lusindex.
        for substep in range(n_sub):
            if not ion.actief:
                break

            # Regio-detectie:
            # De opstelling is in wereld.py gedefinieerd als zones (versneller, selector, analysekamer, detector).
            # Per sub-stap wordt bepaald in welke zone het deeltje zich bevindt; velden worden daarop gebaseerd.
            locatie_id = bepaal_locatie_id_met_muis(ion.x_m, ion.y_m)

            # Bewaar "vorige" info voor detector-regel (analysekamer + rechts->links)
            locatie0 = locatie_id
            vx0 = ion.vx

            # Veldtoewijzing per zone:
            # - Versnellingsveld: Ex ≠ 0, Ey = 0
            # - Selectorveld:     Ey ≠ 0, Ex = 0, Bz ≠ 0
            # - Analysegebied:    Ex = Ey = 0, Bz ≠ 0
            #
            # Hiermee ontstaat:
            # - versnelling in x door Ex (energie-invoer via E-veld),
            # - selectie/compensatie in y door Ey in aanwezigheid van Bz,
            # - cirkelbeweging in analysekamer door Bz.
            ex = (
                elektrisch_veld(locatie_id, instellingen)
                if locatie_id == LOCATIE_VERSNELLINGSVELD
                else 0.0
            )
            ey = (
                elektrisch_veld(locatie_id, instellingen)
                if locatie_id == LOCATIE_SELECTORVELD
                else 0.0
            )
            bz = magnetisch_veld_z(locatie_id, instellingen)

            # Integratiekeuze:
            # Bij Bz ≠ 0 wordt de Boris-integrator gebruikt om de magnetische rotatie numeriek stabiel te behandelen.
            # Bij Bz = 0 resteert uitsluitend E-versnelling; een expliciete Euler-stap is dan toereikend.
            if bz != 0.0:  # != wil zeggen: is niet gelijk aan
                boris_stap_2d(ion, ex=ex, ey=ey, bz=bz, dt=dt_sub)

            # Zonder magnetisch veld wordt een expliciete Euler-stap toegepast voor E-versnelling:
            # a = (q/m)·E  ->  v_{n+1} = v_n + a·dt_sub
            else:
                ion.vx = ion.vx + (ion.q_c / ion.m_kg) * ex * dt_sub
                ion.vy = ion.vy + (ion.q_c / ion.m_kg) * ey * dt_sub

            # Positie-update (recursief):
            # x_{n+1} = x_n + v_x,n+1 * dt_sub
            # y_{n+1} = y_n + v_y,n+1 * dt_sub
            # De snelheid is hier reeds geüpdatet; daardoor wordt de nieuwe snelheid gebruikt voor de verplaatsing.
            ion.x_m = ion.x_m + ion.vx * dt_sub
            ion.y_m = ion.y_m + ion.vy * dt_sub

            # Contactstraal:
            # Voor botsingsdetectie wordt een begrensde effectieve straal gebruikt.
            # Dit voorkomt dat visuele vergroting (tekenstraal) leidt tot onrealistische, te vroege botsingen.
            STRAAL_CONTACT_MAX_M = (
                0.0005  # 0.5 mm (bij PX_PER_METER ≈ 5000 komt dit overeen met ~2.5 px)
            )

            straal_contact_m = min(ion.straal_m, STRAAL_CONTACT_MAX_M)
            contact_type, contact_id = bepaal_contact_m(
                ion.x_m, ion.y_m, straal_contact_m
            )

            # AANNAME: een wandcontact betekent botsing met de opstelling; het deeltje wordt verwijderd.
            if contact_type == CONTACT_WAND:
                ion.actief = False
                break

            if contact_type == CONTACT_DETECTOR:
                # Detectorhit:
                # Een detectorcontact beëindigt het deeltje. Indien het deeltje uit de analysekamer komt en richting detector beweegt,
                # wordt de hit geregistreerd als meetpunt voor verdere analyse (histogram).
                if (
                    locatie0 == LOCATIE_ANALYSEKAMER
                    and vx0 < 0
                    and contact_id is not None
                ):
                    # De hitpositie wordt naar het detector-interval geclamped zodat het meetpunt binnen de detectorstrip valt.
                    x_hit_m, y_hit_m = clamp_naar_detector_m(
                        contact_id, ion.x_m, ion.y_m
                    )

                    # Registratie van het meetpunt in SI-eenheden (meters) voor reproduceerbare analyse en histogramvorming.
                    hits.append(
                        DetectorHit(
                            x_m=x_hit_m,
                            y_m=y_hit_m,
                            kleur=ion.kleur,
                            detector_id=contact_id,
                        )
                    )
                ion.actief = False
                break

    return hits
