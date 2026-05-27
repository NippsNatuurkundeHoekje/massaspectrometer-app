from copy import deepcopy
from app.config.configuratie import KLEUREN_PALET


def maak_ui_state() -> dict:
    ui_state = {
        "level": 1,
        "kleuren": list(KLEUREN_PALET),
        "ion_labels": ["Ion A", "Ion B", "Ion C", "Ion D", "Ion E"],
        "level_status": "idle",
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
            "meting": False,
        },
        "actieve_slider": None,
        "meters": {
            "E_selector_Vpm": 0.0,
            "v_selectie_ms": 0.0,
        },
        "histogram": {
            "y_hits_m": [],
            "bins": 50,
            "y_expected_m": None,
        },
        "selector_gekalibreerd": False,
        "show_ionenkaart": False,
        "ionenkaart_items": [],
        "ionenkaart_scroll": 0,
        "formulekaart_scroll": 0,
    }

    ui_state["ion_invoer"] = [""] * len(ui_state["kleuren"])
    ui_state["ion_feedback"] = [""] * len(ui_state["kleuren"])

    return deepcopy(ui_state)
