# ionen.py
# Ionenlijst + didactische "bakken" (A t/m D)
# Bron: Ionenlijst_massaspectrometer_didactische_bakken.docx

from __future__ import annotations

from dataclasses import dataclass
import random

# SI-constanten
U_KG = 1.66053906660e-27  # 1 atomaire massa-eenheid in kg
E_C = 1.602176634e-19  # elementaire lading in Coulomb


@dataclass(frozen=True)
class Ion:
    symbool: str  # bijv. "Na"
    isotoop: str  # bijv. "23Na" of "¹H" (mag tekst zijn)
    massa_u: float  # in u (atom. massa-eenheid)
    lading_e: int  # in veelvouden van e (kan negatief)
    bak: str  # "A", "B", "C", "D"

    @property
    def massa_kg(self) -> float:
        return self.massa_u * U_KG

    @property
    def lading_c(self) -> float:
        return self.lading_e * E_C

    @property
    def mq_u_per_e(self) -> float:
        # didactisch handig; teken zit in lading, maar m/q vaak als absolute waarde gebruikt
        if self.lading_e == 0:
            return float("inf")
        return self.massa_u / self.lading_e

    @property
    def soort_id(self) -> str:
        """Unieke sleutel voor 'soort' binnen de simulatie (voor kleuren, tellingen, etc.)."""
        return f"{self.symbool}|{self.isotoop}|{self.lading_e}"


def _ion(symbool: str, isotoop: str, massa_u: float, lading_e: int, bak: str) -> Ion:
    return Ion(
        symbool=symbool, isotoop=isotoop, massa_u=massa_u, lading_e=lading_e, bak=bak
    )


# ----------------------------
# Bakken (zoals in jouw document)
# ----------------------------

BAK_A: list[Ion] = [
    # Bak A: simpel, herkenbaar, altijd 1+ (mono-ion in lvl 1–3)
    _ion("H", "¹H", 1.007825, +1, "A"),
    _ion("He", "⁴He", 4.002603, +1, "A"),
    _ion("Li", "⁷Li", 7.016004, +1, "A"),
    _ion("C", "¹²C", 12.000000, +1, "A"),
    _ion("N", "¹⁴N", 14.003074, +1, "A"),
    _ion("F", "¹⁹F", 18.998403, +1, "A"),
    _ion("Ne", "²⁰Ne", 19.992440, +1, "A"),
    _ion("Na", "²³Na", 22.989770, +1, "A"),
    _ion("Mg", "²⁴Mg", 23.985042, +1, "A"),
    _ion("Al", "²⁷Al", 26.981538, +1, "A"),
]

BAK_B: list[Ion] = [
    # Bak B: 1+ met (bijna-)isobaren, mengsels in lvl 4–6 maken dit echt lastig
    _ion("Si", "²⁸Si", 27.976927, +1, "B"),
    _ion("P", "³¹P", 30.973762, +1, "B"),
    _ion("S", "³²S", 31.972071, +1, "B"),
    _ion("Cl", "³⁵Cl", 34.968853, +1, "B"),
    _ion("K", "³⁹K", 38.963707, +1, "B"),
    _ion("Ar", "⁴⁰Ar", 39.962383, +1, "B"),
    _ion("Ca", "⁴⁰Ca", 39.962591, +1, "B"),
]

BAK_C: list[Ion] = [
    # Referentie 1+ (handig om te vergelijken, voorkomt dat alles meteen "q-trucjes" voelt)
    _ion("Na", "²³Na", 22.989770, +1, "C"),
    _ion("K", "³⁹K", 38.963707, +1, "C"),
    _ion("Rb", "⁸⁵Rb", 84.911789, +1, "C"),
    _ion("Ne", "²⁰Ne", 19.992440, +1, "C"),
    _ion("Ne", "²²Ne", 21.991385, +1, "C"),
    # Meervoudig geladen: hier moeten leerlingen q gaan overwegen
    _ion("Mg", "²⁴Mg", 23.985042, +2, "C"),
    _ion("Al", "²⁷Al", 26.981538, +3, "C"),
    _ion("Ca", "⁴⁰Ca", 39.962591, +2, "C"),
    _ion("Fe", "⁵⁶Fe", 55.934942, +2, "C"),
    _ion("Ni", "⁵⁸Ni", 57.935348, +2, "C"),
    _ion("Zn", "⁶⁴Zn", 63.929147, +2, "C"),
    # Hoog geladen edelgassen (uit jouw bestaande set)
    _ion("Kr", "⁸⁴Kr", 83.911497, +4, "C"),
    _ion("Sr", "⁸⁸Sr", 87.905614, +4, "C"),
    _ion("Ba", "¹³⁸Ba", 137.905241, +6, "C"),
    _ion("Xe", "¹³²Xe", 131.904154, +6, "C"),
]


BAKKEN: dict[str, list[Ion]] = {
    "A": BAK_A,
    "B": BAK_B,
    "C": BAK_C,
}

ALLE_IONEN: list[Ion] = BAK_A + BAK_B + BAK_C


# ----------------------------
# Keuzehelpers (generator/levels)
# ----------------------------


def _haal_bak(bak: str) -> list[Ion]:
    """Geef de lijst ionen voor een bak terug, of geef een duidelijke fout."""
    if bak not in BAKKEN:
        raise ValueError(f"Onbekende bak: {bak}. Kies uit: {list(BAKKEN.keys())}")
    return BAKKEN[bak]


def kies_ion(bak: str, rng: random.Random | None = None) -> Ion:
    """Kies willekeurig 1 ion uit een bak."""
    r = rng or random
    ionen = _haal_bak(bak)
    return r.choice(ionen)


def kies_mengsel(bak: str, aantal: int, rng: random.Random | None = None) -> list[Ion]:
    """Kies een mengsel (uniek waar mogelijk) uit een bak."""
    if aantal <= 0:
        raise ValueError("aantal moet > 0 zijn")
    r = rng or random
    bron = _haal_bak(bak)
    if aantal >= len(bron):
        return list(bron)
    return r.sample(bron, k=aantal)


def maak_ion_pool_en_wegingen(
    instroomprofiel: str,
    bak: str,
    rng: random.Random | None = None,
    mengsel_aantal: int = 2,
    mengsel_weging: tuple[float, float] = (0.5, 0.5),
    ion_symbool: str | None = None,
) -> tuple[list[Ion], list[float]]:
    """
    Centrale plek voor instroomprofielen.
    Geeft (pool, wegingen) terug.

    Ondersteunt:
    - mono_symbool
    - mono_bak
    - eenvoudig_mengsel_bak (2 ionen; weging instelbaar)
    """
    r = rng or random
    profiel = instroomprofiel.strip().lower()

    if profiel == "mono_symbool":
        if not ion_symbool:
            raise ValueError("mono_symbool vereist ion_symbool")
        ion = kies_ion_op_symbool(ion_symbool, bak=bak)
        return [ion], [1.0]

    if profiel == "mono_bak":
        ion = kies_ion(bak=bak, rng=r)
        return [ion], [1.0]

    if profiel == "eenvoudig_mengsel_bak":
        ionen = kies_mengsel(bak=bak, aantal=mengsel_aantal, rng=r)

        if len(ionen) < 2:
            # val terug op mono (veiligheid)
            ion = kies_ion(bak=bak, rng=r)
            return [ion], [1.0]

        # Voor nu rustig: 2 ionen
        pool = [ionen[0], ionen[1]]

        w0, w1 = mengsel_weging
        if w0 < 0 or w1 < 0 or (w0 + w1) == 0:
            raise ValueError("mengsel_weging moet niet-negatief zijn en som > 0")

        return pool, [float(w0), float(w1)]

    raise ValueError(f"Onbekend instroomprofiel: {instroomprofiel}")


def kies_ion_op_symbool(symbool: str, bak: str = "A") -> Ion:
    """Kies een ion op basis van het symbool en optioneel de bak."""
    if bak not in BAKKEN:
        raise ValueError(f"Onbekende bak: {bak}. Kies uit {list(BAKKEN.keys())}")
    for ion in _haal_bak(bak):
        if ion.symbool == symbool:
            return ion
    raise ValueError(f"Ion met symbool {symbool} niet gevonden in bak {bak}.")


def ion_info(ion: Ion) -> str:
    """Handige tekstregel voor debug/logging."""
    teken = "+" if ion.lading_e > 0 else ""
    return f"{ion.symbool} ({ion.isotoop}) m={ion.massa_u:.6f} u, q={teken}{ion.lading_e}e, bak={ion.bak}"


def ion_code(ion: Ion) -> str:
    """Compacte code voor invoer/controle, bv. He2+, Ne+, Cl-, S2-."""
    q = ion.lading_e
    if q == 0:
        return f"{ion.symbool}0"

    teken = "+" if q > 0 else "-"
    grootte = abs(int(q))
    if grootte == 1:
        return f"{ion.symbool}{teken}"
    return f"{ion.symbool}{grootte}{teken}"
