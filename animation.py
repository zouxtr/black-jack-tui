"""Card fly-from-deck-to-hand animation system."""

from cards import CARD_W, CARD_H, render_card, is_red_suit


class CardAnimation:
    """A single card flying from start to end position."""

    def __init__(self, card, start_row, start_col, end_row, end_col,
                 total_frames=8, hidden=False, hand_type=None, hand_index=None):
        self.card = card
        self.start_row = start_row
        self.start_col = start_col
        self.end_row = end_row
        self.end_col = end_col
        self.total_frames = total_frames
        self.frame = 0
        self.hidden = hidden
        self.hand_type = hand_type  # 'player' or 'dealer'
        self.hand_index = hand_index  # index in hand

    @property
    def current_row(self):
        if self.frame >= self.total_frames:
            return self.end_row
        return round(self.start_row + (self.end_row - self.start_row) * self.frame / self.total_frames)

    @property
    def current_col(self):
        if self.frame >= self.total_frames:
            return self.end_col
        return round(self.start_col + (self.end_col - self.start_col) * self.frame / self.total_frames)

    @property
    def done(self):
        return self.frame >= self.total_frames

    def advance(self):
        self.frame += 1

    def render(self):
        return render_card(self.card, hidden=self.hidden)


class AnimationManager:
    """Manages multiple concurrent card animations."""

    def __init__(self):
        self.animations = []

    def add(self, animation):
        self.animations.append(animation)

    def advance_all(self):
        for anim in self.animations:
            anim.advance()
        self.animations = [a for a in self.animations if not a.done]

    def is_running(self):
        return len(self.animations) > 0

    def animated_indices(self):
        """Set of (hand_type, hand_index) currently in transit."""
        return {
            (a.hand_type, a.hand_index)
            for a in self.animations
            if a.hand_type is not None
        }
