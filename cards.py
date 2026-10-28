"""ASCII art card rendering for Blackjack TUI."""

CARD_W = 8
CARD_H = 7

RED_SUITS = {"\u2665", "\u2666"}

# Box drawing characters
TL = "\u250c"
TR = "\u2510"
BL = "\u2514"
BR = "\u2518"
H = "\u2500"
V = "\u2502"

FULL_BLOCK = "\u2588"


def is_red_suit(suit):
    return suit in RED_SUITS


def render_card(card, hidden=False):
    """Render a playing card as ASCII art.

    Returns a list of CARD_H strings, each CARD_W chars wide.
    Cards show rank + suit in the top-left and bottom-right corners only.
    """
    lines = []

    if hidden or card is None:
        lines.append(TL + H * (CARD_W - 2) + TR)
        for _ in range(CARD_H - 2):
            lines.append(V + FULL_BLOCK * (CARD_W - 2) + V)
        lines.append(BL + H * (CARD_W - 2) + BR)
        return lines

    rank = card.rank
    suit = card.suit

    # Top border
    lines.append(TL + H * (CARD_W - 2) + TR)

    # Top-left: rank + suit
    tl = (rank + suit)[: CARD_W - 2]
    lines.append(V + tl + " " * (CARD_W - 2 - len(tl)) + V)

    # Middle: large center letter/number (rank)
    center = rank.center(CARD_W - 2)
    lines.append(V + center + V)

    # Empty rows below center
    for _ in range(CARD_H - 5):
        lines.append(V + " " * (CARD_W - 2) + V)

    # Bottom-right: suit + rank (right aligned)
    br = (suit + rank)[: CARD_W - 2]
    lines.append(V + " " * (CARD_W - 2 - len(br)) + br + V)

    # Bottom border
    lines.append(BL + H * (CARD_W - 2) + BR)

    return lines


def combine_cards(card_lines_lists, gap=1):
    """Combine multiple card line lists side by side.

    Each element is a list of CARD_H strings.
    Returns a list of CARD_H combined strings.
    """
    if not card_lines_lists:
        return []
    result = [""] * CARD_H
    gap_str = " " * gap
    for lines in card_lines_lists:
        for i in range(CARD_H):
            result[i] += lines[i] + gap_str
    return result
