# *************
# wereld.py **
# *************
# ROL VAN DIT BESTAND: GEOMETRIE-LAAG
# - Definieert de opstelling als rechthoeken in pixels (pygame.Rect).
# - Biedt conversies tussen SI-eenheden (meters) en schermcoördinaten (pixels).
# - Classificeert (a) in welke regio een punt valt en (b) welk contact een deeltje heeft (wand/detector/geen).
#
# Invariant:
# - wereld.py rekent niet aan snelheden, krachten of integratie.
# - natuurkunde.py gebruikt wereld.py uitsluitend voor geometrische classificatie.

# Standaard bibliotheken en externe pakketten
from __future__ import annotations
import pygame

# Project modules
from dataclasses import dataclass
from app.config.configuratie import PX_PER_METER

# ------------------------------------------------------------
# 1) Box-definities (PIXELS)
# ------------------------------------------------------------
# De rechthoeken zijn in pixels vastgelegd omdat de achtergrondafbeelding en UI-layout pixelgebaseerd zijn.
# SI-positie (meters) wordt uitsluitend via PX_PER_METER geconverteerd voor collision- en regiobepaling.

INSTROOM_PIJP = pygame.Rect(106, 311, 12, 123)
VERSNELLINGSVELD = pygame.Rect(104, 338, 100, 190)
SELECTORVELD = pygame.Rect(240, 419, 500, 30)
ANALYSEKAMER = pygame.Rect(781, 10, 334, 516)
DETECTOR_BOVEN = pygame.Rect(775, 10, 15, 401)
VERSNELLER_BRON = pygame.Rect(118, 255, 65, 70)
SELECTOR_BRON = pygame.Rect(450, 250, 65, 70)
VERSNELLER_PLAAT_PLUS = pygame.Rect(92, 338, 14, 190)
VERSNELLER_PLAAT_MIN = pygame.Rect(204, 338, 14, 190)
SELECTOR_PLAAT_PLUS = pygame.Rect(240, 403, 500, 20)
SELECTOR_PLAAT_MIN = pygame.Rect(240, 445, 500, 20)
COLLIMATOR_BOVEN = pygame.Rect(149, 338, 8, 90)
COLLIMATOR_ONDER = pygame.Rect(149, 438, 8, 90)
SELECTOR_RUIMTE_BOVEN = pygame.Rect(
    SELECTOR_PLAAT_PLUS.left,
    SELECTOR_PLAAT_PLUS.top - 80,
    SELECTOR_PLAAT_PLUS.width,
    80,
)
SELECTOR_RUIMTE_ONDER = pygame.Rect(
    SELECTOR_PLAAT_MIN.left,
    SELECTOR_PLAAT_MIN.bottom,
    SELECTOR_PLAAT_MIN.width,
    70,
)
WANDEN: list[pygame.Rect] = [
    # Randen rondom versnellingsveld en versnellingskamer
    pygame.Rect(85, 528, 135, 6),  # onderrand
    pygame.Rect(85, 334, 135, 6),  # bovenrand
    pygame.Rect(92, 334, 13, 200),  # linkerrand
    pygame.Rect(203, 334, 13, 87),  # rechterrand boven
    pygame.Rect(203, 446, 13, 87),  # rechterrand onder
    pygame.Rect(149, 340, 8, 89),  # collimator boven
    pygame.Rect(149, 437, 8, 90),  # collimator onder
    # Randen rondom Selectorveld en kamer
    pygame.Rect(237, 401, 507, 20),  # bovenrand
    pygame.Rect(237, 447, 507, 20),  # onderrand
    pygame.Rect(237, 334, 6, 86),  # linker bovenrand
    pygame.Rect(237, 447, 6, 86),  # linker onderrand
    pygame.Rect(740, 334, 6, 86),  # rechter bovenrand
    pygame.Rect(740, 447, 6, 86),  # rechter onderrand
    # Randen rondom analysekamer
    pygame.Rect(775, 2, 346, 9),  # bovenrand
    pygame.Rect(775, 525, 345, 9),  # onderrand
    pygame.Rect(775, 2, 9, 409),  # linker bovenrand
    pygame.Rect(775, 456, 9, 79),  # linker onderrand
    pygame.Rect(1111, 2, 9, 533),  # rechterrand
]


# ------------------------------------------------------------
# 2) Locatie-IDs en regio-rects (één bron van waarheid)
# ------------------------------------------------------------
# Locatie-IDs (strings) worden in meerdere bestanden gebruikt (o.a. natuurkunde.py).
# Houd deze waarden dus stabiel.
LOCATIE_BUITEN = "buiten"
LOCATIE_INSTROOM = "instroom_pijp"
LOCATIE_VERSNELLINGSVELD = "versnellingsveld"
LOCATIE_SELECTORVELD = "selectorveld"
LOCATIE_ANALYSEKAMER = "analysekamer"
LOCATIE_DETECTOR_BOVEN = "detector_boven"


# Overlap-prioriteit:
# Sommige rects kunnen in elkaars buurt liggen of visueel overlappen in pixelruimte.
# Daarom wordt een vaste prioriteitsvolgorde gebruikt: detector heeft voorrang op kamer,
# zodat een punt op de detector niet als "analysekamer" wordt geclassificeerd.
REGIOS: dict[str, pygame.Rect] = {
    LOCATIE_INSTROOM: INSTROOM_PIJP,
    LOCATIE_VERSNELLINGSVELD: VERSNELLINGSVELD,
    LOCATIE_SELECTORVELD: SELECTORVELD,
    LOCATIE_ANALYSEKAMER: ANALYSEKAMER,
    LOCATIE_DETECTOR_BOVEN: DETECTOR_BOVEN,
}

# Prioriteit bij overlap: detectorstukken eerst (dan analysekamer, etc.)
_LOCATIE_PRIORITEIT: list[str] = [
    LOCATIE_DETECTOR_BOVEN,
    LOCATIE_ANALYSEKAMER,
    LOCATIE_SELECTORVELD,
    LOCATIE_VERSNELLINGSVELD,
    LOCATIE_INSTROOM,
]

_LOCATIE_VOLGORDE = [(loc_id, REGIOS[loc_id]) for loc_id in _LOCATIE_PRIORITEIT]

# Contacttypes zijn labels.
# De betekenis (deeltje verdwijnt, hit registreren, etc.) wordt in natuurkunde.py toegepast.
CONTACT_GEEN = "geen"
CONTACT_WAND = "wand"
CONTACT_DETECTOR = "detector"


# Afronding naar int is geschikt voor botstests; subpixel-positie blijft behouden in meters in de fysica.
def meters_naar_pixels(x_m: float, y_m: float) -> tuple[int, int]:
    """Converteer meter-coordinaten naar pixel-coordinaten."""
    return int(x_m * PX_PER_METER), int(y_m * PX_PER_METER)


def pixels_naar_meters(x_px: float, y_px: float) -> tuple[float, float]:
    """Converteer pixel-coordinaten naar meter-coordinaten."""
    return x_px / PX_PER_METER, y_px / PX_PER_METER


def bepaal_locatie_id_met_muis(x_m: float, y_m: float) -> str:
    """
    Geef locatie-id terug voor een punt (x_m, y_m).
    Wereld bepaalt dit; natuurkunde hoeft geen pixels te zien.
    """
    x_px, y_px = meters_naar_pixels(x_m, y_m)
    for locatie_id, rect in _LOCATIE_VOLGORDE:
        if rect.collidepoint(x_px, y_px):
            return locatie_id
    return LOCATIE_BUITEN


# ------------------------------------------------------------
# 3 Helpers
# ------------------------------------------------------------


# Hulpfunctie voor UI/wereld: punttest in pixelruimte.
def punt_in_rect(punt_px: tuple[int, int], rect: pygame.Rect) -> bool:
    return rect.collidepoint(punt_px)


# Schermbegrenzing met marge: voorkomt dat objecten pas verdwijnen zodra ze exact buiten beeld zijn.
def buiten_scherm(
    x_px: int, y_px: int, scherm_breedte: int, scherm_hoogte: int, marge: int = 30
) -> bool:
    return (
        x_px < -marge
        or x_px > scherm_breedte + marge
        or y_px < -marge
        or y_px > scherm_hoogte + marge
    )


# Deze methode is snel en voldoende nauwkeurig voor kleine cirkels (deeltjes) tegen rechthoekige wanden.
def cirkel_raakt_rect(x_px: int, y_px: int, straal_px: int, rect: pygame.Rect) -> bool:
    """
    Snelle circle-rect overlap test:
    - clamp circle center to rect
    - check afstand <= straal
    """
    dichtst_x = max(rect.left, min(x_px, rect.right))
    dichtst_y = max(rect.top, min(y_px, rect.bottom))
    dx = x_px - dichtst_x
    dy = y_px - dichtst_y
    return (dx * dx + dy * dy) <= (straal_px * straal_px)


def deeltje_raakt_wand(x_px: int, y_px: int, straal_px: int) -> bool:
    """True als cirkel een van de WANDEN raakt."""
    for wand in WANDEN:
        if cirkel_raakt_rect(x_px, y_px, straal_px, wand):
            return True
    return False


def bepaal_contact_m(x_m: float, y_m: float, straal_m: float) -> tuple[str, str | None]:
    """
    Classificeer contact voor een deeltje-cirkel (in meters).

    Returns:
        (contact_type, contact_id)
        - contact_type: CONTACT_GEEN | CONTACT_WAND | CONTACT_DETECTOR
        - contact_id: None of LOCATIE_DETECTOR_BOVEN
    """
    x_px, y_px = meters_naar_pixels(x_m, y_m)
    straal_px = max(1, int(straal_m * PX_PER_METER))

    # Detectorcontact krijgt voorrang op wandcontact zodat meetpunten niet worden gemaskeerd door algemene wanden.
    if cirkel_raakt_rect(x_px, y_px, straal_px, DETECTOR_BOVEN):
        return CONTACT_DETECTOR, LOCATIE_DETECTOR_BOVEN

    # Dan pas: algemene wanden
    if deeltje_raakt_wand(x_px, y_px, straal_px):
        return CONTACT_WAND, None

    return CONTACT_GEEN, None


def clamp_naar_detector_m(
    detector_id: str, x_m: float, y_m: float
) -> tuple[float, float]:
    """
    Clamp een (x_m, y_m) naar het dichtstbijzijnde punt IN de detector-rect (in pixels),
    zodat hits visueel op de detectorstrip terechtkomen.
    """
    # Dit beïnvloedt uitsluitend de gerapporteerde hitpositie; de contactbeslissing zelf gebeurt vóór het clampen.

    rect = REGIOS.get(detector_id)
    if rect is None:
        return x_m, y_m

    x_px, y_px = meters_naar_pixels(x_m, y_m)

    # clamp naar binnenkant rect (right/bottom zijn exclusief)
    x_px = max(rect.left, min(rect.right - 1, x_px))
    y_px = max(rect.top, min(rect.bottom - 1, y_px))

    return pixels_naar_meters(x_px, y_px)


# ------------------------------------------------------------
# 4) Debug tekenen (box-kaders over achtergrond)
# ------------------------------------------------------------
@dataclass
class DebugBoxStijl:
    dikte: int = 2
    alpha: int = 160  # 0..255


def teken_debug_boxen(scherm: pygame.Surface, stijl: DebugBoxStijl | None = None):
    """
    Tekent rechthoekkaders om de geometrie visueel te verifiëren tijdens ontwikkeling.
    Let op: gebruikt semi-transparante surfaces.
    """

    if stijl is None:
        stijl = DebugBoxStijl()

    overlay = pygame.Surface(scherm.get_size(), pygame.SRCALPHA)

    def kader(rect: pygame.Rect, kleur: tuple[int, int, int, int]):
        pygame.draw.rect(overlay, kleur, rect, stijl.dikte)

    # Regio's
    kader(INSTROOM_PIJP, (255, 180, 0, 180))
    kader(VERSNELLINGSVELD, (255, 180, 0, 180))
    kader(SELECTORVELD, (255, 180, 0, 180))
    kader(ANALYSEKAMER, (255, 180, 0, 180))
    kader(DETECTOR_BOVEN, (255, 180, 0, 180))
    kader(VERSNELLER_BRON, (255, 180, 0, 180))
    kader(SELECTOR_BRON, (255, 180, 0, 180))
    kader(VERSNELLER_PLAAT_PLUS, (255, 180, 0, 180))
    kader(VERSNELLER_PLAAT_MIN, (255, 180, 0, 180))
    kader(SELECTOR_PLAAT_PLUS, (255, 180, 0, 180))
    kader(SELECTOR_PLAAT_MIN, (255, 180, 0, 180))
    kader(COLLIMATOR_BOVEN, (255, 180, 0, 180))
    kader(COLLIMATOR_ONDER, (255, 180, 0, 180))
    kader(SELECTOR_RUIMTE_BOVEN, (0, 200, 255, 120))
    kader(SELECTOR_RUIMTE_ONDER, (0, 200, 255, 120))

    # Wanden
    # for w in WANDEN:
    #    kader(w, KLEUR_WAND)
    scherm.blit(overlay, (0, 0))


def resolve_click_target(pos_px: tuple[int, int]) -> str | None:
    """
    Map een klikpositie (pixels) naar een 'world-key' string.
    Alleen opstelling (geen UI).
    """
    # Click-targets worden gebruikt voor contextuele uitleg (robot/infoteksten) en staan los van de fysica.

    x, y = pos_px

    # Prioriteit volgt level(fase) relevantie: detector en instroom krijgen voorrang op algemene zones.
    if DETECTOR_BOVEN.collidepoint(x, y):
        return "detector"

    if INSTROOM_PIJP.collidepoint(x, y):
        return "instroom"

    if COLLIMATOR_BOVEN.collidepoint(x, y) or COLLIMATOR_ONDER.collidepoint(x, y):
        return "versneller.collimator"

    if VERSNELLINGSVELD.collidepoint(x, y):
        return "versneller.veld"

    if SELECTORVELD.collidepoint(x, y):
        return "selector.veld"

    if SELECTOR_PLAAT_PLUS.collidepoint(x, y) or SELECTOR_PLAAT_MIN.collidepoint(x, y):
        return "selector.platen"

    # Dan pas de ruimte-zones
    if SELECTOR_RUIMTE_BOVEN.collidepoint(x, y) or SELECTOR_RUIMTE_ONDER.collidepoint(
        x, y
    ):
        return "selector.ruimte"

    if ANALYSEKAMER.collidepoint(x, y):
        return "analyse.kamer"

    # Spanningsbronnen
    if VERSNELLER_BRON.collidepoint(x, y):
        return "versneller.bron"

    if SELECTOR_BRON.collidepoint(x, y):
        return "selector.bron"

    # Platen
    if VERSNELLER_PLAAT_PLUS.collidepoint(x, y) or VERSNELLER_PLAAT_MIN.collidepoint(
        x, y
    ):
        return "versneller.platen"

    return None
