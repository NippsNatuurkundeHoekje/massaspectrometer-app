# fonts.py
import pygame

_FONT_PAD = None
_FONTS = {}


def _vind_unicode_font():
    global _FONT_PAD
    if _FONT_PAD is None:
        _FONT_PAD = pygame.font.match_font("dejavusans")
    return _FONT_PAD


def get_font(size: int) -> pygame.font.Font:
    """
    Geef een Unicode-safe font van gegeven grootte.
    Wordt gecachet per grootte.
    """
    if size not in _FONTS:
        pad = _vind_unicode_font()
        try:
            if pad:
                _FONTS[size] = pygame.font.Font(pad, size)
            else:
                _FONTS[size] = pygame.font.Font(None, size)
        except Exception:
            _FONTS[size] = pygame.font.Font(None, size)
    return _FONTS[size]
