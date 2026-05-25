# *******************
# ** generator.py **
# *******************
# ROL VAN DIT BESTAND:INSTROOM-LAAG
# - Genereert deeltjes (ionen) aan de instroomopening met een instelbare frequentie (deeltjes/s).
# - De generator is frame-rate onafhankelijk via een accumulator (dt-gestuurd).
# - Beginposities worden in pixels gekozen (layout), daarna geconverteerd naar meters (SI) voor de fysica.
#
# Invariant:
# - Deze module bepaalt alleen startcondities (x_m, y_m, vx, vy, m_kg, q_c, kleur).
# - De verdere beweging en botsingen worden uitsluitend berekend in natuurkunde.py.


# Standaard bibliotheken en externe pakketten
import random
import math

# Projectmodules
from natuurkunde import Deeltje
from wereld import pixels_naar_meters
from configuratie import (
    DEELTJES_PER_SECONDE,
    DEELTJE_STRAAL_M,
    PIJP_X_MIN_PX,
    PIJP_X_MAX_PX,
    PIJP_Y_MAX_PX,
    PIJP_Y_MIN_PX,
    KLEUREN_PALET,
)


class InstroomGenerator:
    def __init__(
        self,
        pool: list,
        wegingen: list[float],
    ):
        self.deeltjes_per_seconde = float(DEELTJES_PER_SECONDE)
        self._accumulator = 0.0

        # DE ENIGE waarheid
        self.pool = pool
        self.wegingen = wegingen

        self.kleur_per_soort_id: dict[str, tuple[int, int, int]] = {}
        self._volgende_kleur_index = 0

    def _kleur_voor_ion(self, ion) -> tuple[int, int, int]:
        soort_id = ion.soort_id
        if soort_id not in self.kleur_per_soort_id:
            kleur = KLEUREN_PALET[self._volgende_kleur_index % len(KLEUREN_PALET)]
            self.kleur_per_soort_id[soort_id] = kleur
            self._volgende_kleur_index += 1
        return self.kleur_per_soort_id[soort_id]

    def update(self, dt, deeltjes, instellingen=None):
        # Geen actieve pool → niet instromen (bijv. vóór Start level)
        if not self.pool or not self.wegingen:
            return

        if instellingen is None:
            instellingen = {}
        factor = float(instellingen.get("bundeldichtheid", 1.0))
        # bundeldichtheid is een dimensionloze schaalfactor op de instroomintensiteit (0 = geen instroom).
        factor = max(0.0, factor)
        # Frame-rate onafhankelijke instroom:
        # accumulator += (deeltjes/s) * dt. Elke keer dat accumulator ≥ 1 wordt een deeltje toegevoegd.
        self._accumulator += self.deeltjes_per_seconde * factor * dt
        while self._accumulator >= 1.0:
            self._accumulator -= 1.0
            deeltjes.append(self._maak_deeltje(instellingen))

    def _maak_deeltje(self, instellingen: dict) -> Deeltje:
        # Startpositie in pixels
        y_px = random.uniform(PIJP_Y_MIN_PX, PIJP_Y_MAX_PX)
        x_px = random.uniform(PIJP_X_MIN_PX, PIJP_X_MAX_PX)

        # Kies ion volgens profiel (mono of mengsel)
        ion = random.choices(self.pool, weights=self.wegingen, k=1)[0]
        kleur = self._kleur_voor_ion(ion)

        # Omzetten naar meters
        x_m, y_m = pixels_naar_meters(x_px, y_px)

        # Beginvoorwaarde (startdynamica):
        # Het deeltje start met een beperkte injectiesnelheid zodat beweging direct zichtbaar is.
        # De dominante energietoename volgt later uit het versnellingsveld (E-veld) in natuurkunde.py.
        v_inject = random.uniform(
            150.0, 260.0
        )  # m/s (kleine startwaarde voor zichtbaarheid)

        # Bundelprofiel (instroomspreiding):
        # Meeste deeltjes krijgen een duidelijke hoekspreiding, wat leidt tot verlies op wanden.
        # Een kleiner deel krijgt een bijna-parallelle instroom, om doorlaat en selectie zichtbaar te maken.
        # 80%: brede hoekspreiding (realistische bundeldivergentie; veel deeltjes worden geometrisch uitgefilterd).
        hoek = random.uniform(-0.450, 0.450)

        # 20%: smalle hoekspreiding (quasi-gecollimeerde deelbundel; vergroot de kans op doorlaat).
        if random.random() < 0.20:
            hoek = random.uniform(-0.001, 0.001)
            # Voor de quasi-gecollimeerde bundel wordt de startpositie in het midden van de instroomopening gekozen.
            y_px = 0.5 * (PIJP_Y_MIN_PX + PIJP_Y_MAX_PX)
        vx = v_inject * math.cos(hoek)
        vy = v_inject * math.sin(hoek)

        # Maak het deeltje aan met deze beginsnelheid
        # Constructie in SI-eenheden: positie (m), snelheid (m/s), massa (kg), lading (C).
        return Deeltje(
            x_m=x_m,
            y_m=y_m,
            vx=vx,
            vy=vy,
            straal_m=DEELTJE_STRAAL_M,
            m_kg=ion.massa_kg,
            q_c=ion.lading_c,
            kleur=kleur,
        )
