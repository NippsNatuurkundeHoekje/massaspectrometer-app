# *******************
# ** interactie.py **
# *******************
# ROL VAN DIT BESTAND: INTERACTIE-LAAG
# - Leest ruwe Pygame-events (muis) en vertaalt deze naar semantische acties (tuples).
# - Doet uitsluitend hit-testing op basis van UI-rechthoeken uit ui_state (aangeleverd door weergave.py).
# - Voert geen state-mutaties uit: acties zijn data zonder bijwerkingen.
#
# Invariant:
# - Geen simulatie-update, geen natuurkundige berekeningen.
# - Geen directe rendering.
# - Robot-object wordt alleen geraadpleegd voor ballon-hit-test (sluiten), niet voor inhoudelijke logica.

import pygame
from wereld import resolve_click_target


def verwerk_muis_events(
    events: list[pygame.event.Event], ui_state: dict, robot
) -> list[tuple]:
    """
    Parseert muis-events naar neutrale acties.
    Geen sim, geen fysica, geen robotteksten.
    Robot mag alleen voor ballon-hit-test (sluiten) worden geraadpleegd.
    """
    # Outputcontract:
    # Elke actie is een tuple (actie_type, ...) zonder bijwerkingen.
    # Bijwerkingen (state-mutaties, simulatie, UI-toggles) gebeuren uitsluitend in hoofd.py.

    acties: list[tuple] = []

    knop_rechthoeken = ui_state.get("knop_rechthoeken", {})
    slider_rechthoeken = ui_state.get("slider_rechthoeken", {})
    # Layout-rects:
    # Rechthoeken worden in weergave.py bepaald en teruggeschreven naar ui_state.
    # Interactie gebruikt deze rects als bron van waarheid voor hit-testing.
    vergrendeld = ui_state.get("locked", {})
    knoppen = ui_state.get("buttons", {})

    target_vakjes = ui_state.get("target_kleur_vakjes", [])
    invoer_vakjes = ui_state.get("ion_invoer_vakjes", [])

    for ev in events:
        # -------------------------
        # Linkermuisknop NEER (klik)
        # -------------------------
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            muis_x, muis_y = ev.pos

            # ballon: klik = sluiten
            ballon_rect = robot.ballon_rechthoek()
            if ballon_rect and ballon_rect.collidepoint((muis_x, muis_y)):
                acties.append(("ballon_sluit",))
                continue

            # 1) target-kleur vakjes
            if not vergrendeld.get("target", False):
                for i, rr in enumerate(target_vakjes):
                    if rr and rr.collidepoint((muis_x, muis_y)):
                        # Target-keuze koppelt de geselecteerde kleur/ion aan het bijbehorende invoerveld.
                        acties.append(("set_target", i))
                        acties.append(("focus_invoer", i))
                        break

            # 2) invoervakjes: focus
            for i, rr in enumerate(invoer_vakjes):
                if rr and rr.collidepoint((muis_x, muis_y)):
                    acties.append(("focus_invoer", i))
                    break

            # 3) knoppen
            # Lokale helper voor consistente kliklogica (hit-test + vergrendeling) binnen dit eventpad.
            def _knop_clicked(key: str) -> bool:
                r = knop_rechthoeken.get(key)
                return bool(
                    r
                    and r.collidepoint((muis_x, muis_y))
                    and not vergrendeld.get(key, False)
                )

            for key in (
                "submit",
                "start_level",
                "meting",
                "pause",
                "reset_det",
                "reset_sim",
            ):
                if _knop_clicked(key):
                    acties.append(("knop", key))
                    break
            else:
                # 4) sliders: start slepen
                for sleutel, srect in slider_rechthoeken.items():
                    if (
                        srect
                        and srect.collidepoint((muis_x, muis_y))
                        and not vergrendeld.get(sleutel, False)
                    ):
                        acties.append(("slider_start", sleutel, muis_x))
                        break
                else:
                    # 5) world click info
                    key = resolve_click_target((muis_x, muis_y))
                    if key:
                        acties.append(("world_info", key))
            continue

        # -------------------------
        # RechterMuisKnop NEER (toggle ionenkaart)
        # -------------------------
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            key = resolve_click_target(ev.pos)
            if key == "analyse.kamer":
                acties.append(("toggle_ionenkaart",))
            continue

        # -------------------------
        # Muisbeweging (slider slepen)
        # -------------------------
        if ev.type == pygame.MOUSEMOTION:
            if (
                ui_state.get("actieve_slider") is not None
                and ev.buttons
                and ev.buttons[0] == 1
            ):
                sleutel = ui_state["actieve_slider"]
                # Modifier-toetsen (mods) worden meegegeven zodat hoofd.py de resolutie van slider-aanpassing kan bepalen.
                mods = pygame.key.get_mods()
                muis_x, _ = ev.pos
                acties.append(("slider_drag", sleutel, muis_x, mods))
            continue

        # -------------------------
        # Linkermuisknop OP (stop slider)
        # -------------------------
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if ui_state.get("actieve_slider") is not None:
                acties.append(("slider_end",))
            continue

        # -------------------------
        # WIEL (ionenkaart scroll of slider wheel)
        # -------------------------
        if ev.type == pygame.MOUSEWHEEL:

            # Formulekaart scroll (muiswiel boven formulekaart)
            muis_x, muis_y = pygame.mouse.get_pos()
            formulekaart_rect = (
                ui_state.get("layout", {}).get("overlays", {}).get("formulekaart")
            )
            if formulekaart_rect and formulekaart_rect.collidepoint((muis_x, muis_y)):
                # Prioriteit: scroll boven formulekaart wordt niet doorgegeven aan sliders (voorkomt dubbelgedrag).
                acties.append(("formulekaart_scroll", int(ev.y)))
                continue

            # ionenkaart scroll (alleen als open + muis boven analysekamer)
            if ui_state.get("show_ionenkaart", False):
                key = resolve_click_target(pygame.mouse.get_pos())
                if key == "analyse.kamer":
                    acties.append(("ionenkaart_scroll", int(ev.y)))
                    continue

            # hover slider => wheel adjust
            muis_x, muis_y = pygame.mouse.get_pos()
            for sleutel, srect in slider_rechthoeken.items():
                if (
                    srect
                    and srect.collidepoint((muis_x, muis_y))
                    and not vergrendeld.get(sleutel, False)
                ):
                    # Ook bij wheel-adjust wordt mods meegegeven voor consistente resolutie.
                    mods = pygame.key.get_mods()
                    acties.append(("slider_wheel", sleutel, int(ev.y), mods))
                    break

    return acties
