# **************
# ** robot.py **
# **************
# ROL VAN DIT BESTAND: UITLEG-/COACHING-LAAG
# - Beheert een visuele coach (GIF-animatie) en een tekstballon voor contextuele uitleg.
# - Levert uitsluitend UI-elementen: frames, rechthoeken voor hit-testing, en tekstlayout.
#
# Invariant:
# - Geen invloed op natuurkundige toestand of simulatie-uitkomst.
# - Enige state betreft animatie (spreekt/frame-index) en ballon-layout (rect/scrolling/clamping).

# Robot-coach: altijd zichtbaar onderin (fotolijst).
# Idle = frame 0 (stilstaand). Alleen animeren wanneer spreekt=True.

# Standaard bibliotheken en externe pakketten
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import pygame

# Pillow wordt gebruikt om GIF-frames betrouwbaar te decoderen (pygame leest GIF niet frame-voor-frame).
from PIL import Image

# Projectmodules
from fonts import get_font


def gif_afbeeldingen_laden(pad: str) -> List[pygame.Surface]:
    """Lees alle frames uit een GIF met Pillow en zet ze om naar pygame surfaces.
    Contract:
    - Output is een niet-lege lijst pygame.Surface-objecten met alpha (RGBA).
    - Bij een lege GIF of decodeerfout wordt een RuntimeError opgegooid.
    """
    afbeelding = Image.open(pad)
    frames: List[pygame.Surface] = []
    try:
        while True:
            frame = afbeelding.convert("RGBA")
            surf = pygame.image.fromstring(
                frame.tobytes(), frame.size, "RGBA"
            ).convert_alpha()
            frames.append(surf)
            afbeelding.seek(afbeelding.tell() + 1)
    except EOFError:
        pass

    if not frames:
        raise RuntimeError(f"Geen frames gevonden in GIF: {pad}")
    return frames


def schaal_frames_naar_hoogte(
    frames: List[pygame.Surface], doel_hoogte: int
) -> List[pygame.Surface]:
    """Schaal frames naar een vaste hoogte, behoud aspect ratio.
    Motivatie:
    - Hoogte is leidend om de robot visueel consistent in het paneel te plaatsen.
    - smoothscale wordt gebruikt om aliasing bij schaalverkleining te beperken.
    """
    uitvoer: List[pygame.Surface] = []
    for f in frames:
        breedte, hoogte = f.get_size()
        if hoogte <= 0:
            continue
        schaalfactor = doel_hoogte / hoogte
        nieuwe_breedte = max(1, int(breedte * schaalfactor))
        nieuwe_hoogte = max(1, int(hoogte * schaalfactor))
        uitvoer.append(pygame.transform.smoothscale(f, (nieuwe_breedte, nieuwe_hoogte)))

    if not uitvoer:
        raise RuntimeError("Schalen mislukt: geen geldige frames.")
    return uitvoer


def wrap_tekst(
    lettertype: pygame.font.Font, tekst: str, max_width_px: int
) -> List[str]:
    """
    Word-wrap MET respect voor '\n' (paragrafen/lege regels blijven bestaan).
    """
    # Tekstlayout-doel:
    # - Respecteer expliciete regeleindes (\n) als paragrafen.
    # - Voorkom onnodige verticale ruimte door meerdere lege regels te comprimeren.
    # - Verwijder lege regels boven/onder om de balloninhoud visueel te centreren.

    if not tekst:
        return []

    max_width_px = max(10, int(max_width_px))
    uitvoer: List[str] = []

    # Split op echte regeleindes en behoud lege regels
    bron_regels = tekst.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    for bron in bron_regels:
        if bron.strip() == "":
            uitvoer.append("")  # lege regel blijft leeg
            continue

        woorden = bron.split()
        huidig = ""

        for w in woorden:
            test = (huidig + " " + w).strip()
            if lettertype.size(test)[0] <= max_width_px:
                huidig = test
            else:
                if huidig:
                    uitvoer.append(huidig)
                huidig = w

        if huidig:
            uitvoer.append(huidig)

    # Compress: meerdere lege regels achter elkaar -> max 1
    gecomprimeerd: List[str] = []
    leeg = False
    for r in uitvoer:
        if r == "":
            if not leeg:
                gecomprimeerd.append(r)
            leeg = True
        else:
            gecomprimeerd.append(r)
            leeg = False

    # Trim: geen lege regels boven/onder
    while gecomprimeerd and gecomprimeerd[0] == "":
        gecomprimeerd.pop(0)
    while gecomprimeerd and gecomprimeerd[-1] == "":
        gecomprimeerd.pop()

    return gecomprimeerd


@dataclass
class RobotCoachConfiguratie:
    robot_afbeelding: str
    ballon_bestand: str = "bronbestanden/tekstballon.png"
    ballon_schaal: float = 0.85  # 1.0 = originele grootte; later evt. 0.9/1.1
    # Layout-calibratie:
    # Offset is in pixels t.o.v. het robotframe en is afgestemd op de ballonafbeelding (ankerpunt).
    ballon_offset: Tuple[int, int] = (-450, -340)  # (dx, dy) t.o.v. bovenkant frame
    ballon_lettergrootte: int = 20
    ballon_tekstkleur: pygame.Color = field(
        default_factory=lambda: pygame.Color(20, 20, 20)
    )

    # UI-plaatsing
    paneel_hoogte: int = 220
    marge: int = 16
    frame_opvulling: int = 12

    # Animatie
    fps_spreekt: int = 12

    # Uiterlijk
    paneel_achtergrondkleur: pygame.Color = field(
        default_factory=lambda: pygame.Color(245, 245, 245)
    )
    # Visuele schaal van de robot binnen het paneel; beïnvloedt uitsluitend UI-layout.
    robot_hoogte: int = 220  # probeer 180–260


class RobotCoach:
    def __init__(
        self, scherm_breedte: int, scherm_hoogte: int, cfg: RobotCoachConfiguratie
    ):
        self.cfg = cfg
        self.scherm_breedte = scherm_breedte
        self.scherm_hoogte = scherm_hoogte

        onbewerkte_frames = gif_afbeeldingen_laden(cfg.robot_afbeelding)

        # Robothoogte in fotolijst
        doel_robot_hoogte = cfg.robot_hoogte
        self.frames = schaal_frames_naar_hoogte(onbewerkte_frames, doel_robot_hoogte)
        self.aantal_frames = len(self.frames)

        # Animatie-state
        self.spreekt = False
        self._animatie_timer = 0.0
        self._animatie_index = 0

        # Fotolijst (links in panel)
        frame_breedte, frame_hoogte = self.frames[0].get_size()

        # Layout-keuze:
        # De framepositie is afgestemd zodat de robot visueel in het paneel past en ruimte laat voor de ballon.
        x_verschuiving = int(0.669 * scherm_breedte)  # 0.3–0.45 werkt goed
        y_verschuiving = scherm_hoogte - (frame_hoogte + 2 * cfg.frame_opvulling) - 12

        self.frame_rechthoek = pygame.Rect(
            x_verschuiving,
            y_verschuiving,
            frame_breedte + 2 * cfg.frame_opvulling,
            frame_hoogte + 2 * cfg.frame_opvulling,
        )

        self.robot_positie = (
            self.frame_rechthoek.x + cfg.frame_opvulling,
            self.frame_rechthoek.y + cfg.frame_opvulling,
        )

        # Tekstballon (altijd op voorgrond; teken gebeurt in main als laatste)
        try:
            ballon_onbewerkt = pygame.image.load(self.cfg.ballon_bestand)
            ballon = ballon_onbewerkt.convert_alpha()
        except Exception as e:
            raise RuntimeError(
                f"Kan tekstballon niet laden: {self.cfg.ballon_bestand}\n{e}"
            )

        # Eerst vaste cfg-schaal toepassen (1x)
        if self.cfg.ballon_schaal != 1.0:
            bw, bh = ballon.get_size()
            ballon = pygame.transform.smoothscale(
                ballon,
                (
                    max(1, int(bw * self.cfg.ballon_schaal)),
                    max(1, int(bh * self.cfg.ballon_schaal)),
                ),
            )

        # Basis-ballon + cache voor dynamische schaling
        self._ballon_basis = ballon
        self._ballon_cache = {}  # key: (w, h) -> Surface

        # Ballon-anker:
        # Het staartpunt is in de ballonafbeelding gedefinieerd bij de rechteronderhoek.
        # De positionering houdt dit ankerpunt vast zodat de ballon consistent naar de robot wijst, ook bij schalen.
        basis_ballon_w, basis_ballon_h = self._ballon_basis.get_size()
        self._ballon_anker = (
            self.robot_positie[0] + self.cfg.ballon_offset[0] + basis_ballon_w,
            self.robot_positie[1] + self.cfg.ballon_offset[1] + basis_ballon_h,
        )

        self._ballon_tekst: Optional[str] = None
        self._ballon_rect: Optional[pygame.Rect] = None
        self._lettertype = get_font(self.cfg.ballon_lettergrootte)

    def ballon_rechthoek(self) -> Optional[pygame.Rect]:
        return self._ballon_rect

    def zet_spreken(self, spreekt: bool):
        """Zet animatie aan/uit."""
        self.spreekt = spreekt
        if not spreekt:
            self._animatie_timer = 0.0
            self._animatie_index = 0

    def zeg(self, tekst: str):
        """Toon ballon-tekst totdat leerling hem sluit (ESC of klik)."""
        self._ballon_tekst = (tekst or "").strip()
        self.zet_spreken(True)

    def verberg_ballon(self):
        """Verberg ballon direct en stop spreek-animatie."""
        self._ballon_tekst = None
        self._ballon_rect = None
        self.zet_spreken(False)

    def _ballon_surface_op_maat(self, w: int, h: int) -> pygame.Surface:
        """Geef een geschaalde ballon-surface terug (met caching)."""
        w = max(1, int(w))
        h = max(1, int(h))
        key = (w, h)
        s = self._ballon_cache.get(key)
        if s is None:
            s = pygame.transform.smoothscale(self._ballon_basis, key)
            self._ballon_cache[key] = s
        return s

    def _bereken_ballon_grootte_voor_tekst(self, tekst: str) -> tuple[int, int]:
        """
        Kies de kleinste ballon-schaal waarbij de gewrapte tekst past.
        Dit voorkomt 'vaste breedte' gedrag waardoor de ballon niet zichtbaar schaalt.
        """
        basis_w, basis_h = self._ballon_basis.get_size()

        # Moet matchen met teken_tekstballon:
        marge_x_frac = 0.12
        marge_y_frac = 0.18

        # Paint.net meting: staartje = 25% van totale hoogte
        staart_reserve_h_frac = 0.25

        # Staartje heeft geen invloed op breedte
        frac_tekst_w = 1.0 - 2.0 * marge_x_frac
        frac_tekst_h = 1.0 - 2.0 * marge_y_frac - staart_reserve_h_frac

        # Grenzen
        min_scale = 0.55
        max_scale = 1.75

        max_w_scherm = int(0.90 * self.scherm_breedte)
        max_h_scherm = int(0.90 * self.scherm_hoogte)

        regel_h = self._lettertype.get_linesize()

        def _past(scale: float) -> bool:
            w = int(basis_w * scale)
            h = int(basis_h * scale)

            # schermclamp check (we willen geen scales die toch niet kunnen)
            if w > max_w_scherm or h > max_h_scherm:
                return False

            tekst_w = max(10, int(frac_tekst_w * w))
            regels = wrap_tekst(self._lettertype, tekst, tekst_w)
            if not regels:
                regels = [""]

            benodigde_tekst_h = len(regels) * regel_h
            benodigde_ballon_h = int(benodigde_tekst_h / max(0.01, frac_tekst_h))

            # Hoogte past?
            return benodigde_ballon_h <= h

        # Zoek de kleinste schaal waarbij de tekst past.
        gekozen = None
        stappen = 25  # genoeg voor zichtbare scaling, snel genoeg
        for i in range(stappen):
            s = min_scale + (max_scale - min_scale) * (i / (stappen - 1))
            if _past(s):
                gekozen = s
                break

        if gekozen is None:
            gekozen = (
                max_scale  # anders: maximaal, en tekst wordt beneden eventueel afgekapt
            )

        w = int(basis_w * gekozen)
        h = int(basis_h * gekozen)

        # Laatste schermclamp met behoud aspect
        if w > max_w_scherm:
            w = max_w_scherm
            h = int(w * (basis_h / basis_w))
        if h > max_h_scherm:
            h = max_h_scherm
            w = int(h * (basis_w / basis_h))

        return max(1, w), max(1, h)

    def teken_tekstballon(self, scherm_oppervlak: pygame.Surface):
        """Teken ballon + tekst. Wordt als laatste overlay gerenderd zodat deze boven alle UI-elementen ligt."""
        if not self._ballon_tekst:
            return

        ballon_breedte, ballon_hoogte = self._bereken_ballon_grootte_voor_tekst(
            self._ballon_tekst
        )
        ballon_surface = self._ballon_surface_op_maat(ballon_breedte, ballon_hoogte)

        # 1) Positie: anker = rechteronderhoek van de ballonafbeelding (staart-tip)
        anker_x, anker_y = self._ballon_anker
        x = anker_x - ballon_breedte
        y = anker_y - ballon_hoogte

        # Clamp binnen scherm (veiligheidsnet)
        x = max(8, min(self.scherm_breedte - ballon_breedte - 8, x))
        y = max(8, min(self.scherm_hoogte - ballon_hoogte - 8, y))

        scherm_oppervlak.blit(ballon_surface, (x, y))
        self._ballon_rect = pygame.Rect(x, y, ballon_breedte, ballon_hoogte)

        # 2) Tekstgebied: marges + staart-reserve onderin (25% hoogte)
        marge_x = int(0.12 * ballon_breedte)
        marge_y = int(0.18 * ballon_hoogte)
        staart_reserve_h = int(0.25 * ballon_hoogte)

        tekst_breedte = max(10, ballon_breedte - 2 * marge_x)
        regels = wrap_tekst(self._lettertype, self._ballon_tekst, tekst_breedte)
        regel_hoogte = self._lettertype.get_linesize()

        content_top = y + marge_y
        content_bottom = y + ballon_hoogte - marge_y - staart_reserve_h
        content_h = max(1, content_bottom - content_top)

        tekst_h = len(regels) * regel_hoogte
        tekst_y = content_top + max(0, (content_h - tekst_h) // 2)

        # 3) Render regels (stop als het niet meer past)
        for line in regels:
            if tekst_y + regel_hoogte > content_bottom:
                break
            img = self._lettertype.render(line, True, self.cfg.ballon_tekstkleur)
            scherm_oppervlak.blit(img, (x + marge_x, tekst_y))
            tekst_y += regel_hoogte

    def verwerk_gebeurtenis(self, gebeurtenis: pygame.event.Event):
        """ESC of SPACE sluit ballon (en stopt spreken)."""
        if gebeurtenis.type == pygame.KEYDOWN and gebeurtenis.key in (
            pygame.K_SPACE,
            pygame.K_ESCAPE,
        ):
            self.verberg_ballon()

    def update(self, dt: float):
        # Update animatie alleen als self.spreekt waar is.
        if not self.spreekt or self.aantal_frames <= 1:
            return
        # Animatie verloopt dt-gestuurd; frame-index wordt geüpdatet met vaste stapduur (1/fps_spreekt).
        stap_tijd = 1.0 / max(1, self.cfg.fps_spreekt)
        self._animatie_timer += dt
        while self._animatie_timer >= stap_tijd:
            self._animatie_timer -= stap_tijd
            self._animatie_index = (self._animatie_index + 1) % self.aantal_frames

    def teken(self, scherm_oppervlak: pygame.Surface):
        # Render: idle gebruikt frame 0; spreken gebruikt de lopende animatie-index.
        frame = self.frames[self._animatie_index] if self.spreekt else self.frames[0]
        scherm_oppervlak.blit(frame, self.robot_positie)
