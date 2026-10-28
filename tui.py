"""Enhanced curses TUI for Blackjack with animated card dealing and ASCII cards.

Layout:
  * Deck sits on the LEFT side.
  * Dealer hand at top, player hand(s) below.
  * Money HUD across the top.
"""

import curses

from cards import render_card, CARD_W, CARD_H, is_red_suit
from animation import CardAnimation, AnimationManager
from game import BlackjackGame


class BlackjackUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.game = BlackjackGame.load()
        self.anim = AnimationManager()
        self.bet_buf = ""
        self.reset_confirm = False
        self.pending_dealer_hit = False
        self.pending_resolve = False
        self._init_curses()

    def _init_curses(self):
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)      # red suits (hearts/diamonds)
        curses.init_pair(2, curses.COLOR_WHITE, -1)     # black suits (spades/clubs)
        curses.init_pair(3, curses.COLOR_CYAN, -1)      # title / input
        curses.init_pair(4, curses.COLOR_GREEN, -1)     # win
        curses.init_pair(5, curses.COLOR_RED, -1)       # loss / bust
        curses.init_pair(6, curses.COLOR_YELLOW, -1)    # push
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)   # dealer label
        curses.init_pair(8, curses.COLOR_WHITE, -1)     # money / labels

    def run(self):
        self.stdscr.timeout(40)  # ~25 fps; getch returns -1 after 40ms if no input
        while True:
            # Advance animations one frame per loop iteration
            if self.anim.is_running():
                self.anim.advance_all()
                if not self.anim.is_running():
                    self._post_animation()

            self.draw()
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == -1:
                continue

            # Always allow quit
            if key in (ord("q"), ord("Q")):
                return

            # Ignore input while animating (except quit above)
            if self.anim.is_running():
                continue

            # Reset confirmation override
            if self.reset_confirm:
                if key in (ord("y"), ord("Y")):
                    self.game.reset()
                    self.reset_confirm = False
                    self.game.message = "Account reset to $1,000."
                elif key in (ord("n"), ord("N"), 27):  # ESC
                    self.reset_confirm = False
                    self.game.message = "Reset cancelled."
                continue

            if not self.handle_key(key):
                return

    # --------------------------------------------------------------- post-animation
    def _post_animation(self):
        """Called when all animations finish. Triggers next game step."""
        g = self.game
        if self.pending_dealer_hit:
            self.pending_dealer_hit = False
            self._dealer_hit_step()
        elif self.pending_resolve:
            self.pending_resolve = False
            g._resolve()

    # --------------------------------------------------------------- layout
    def _compute_layout(self):
        h, w = self.stdscr.getmaxyx()
        self.layout = {
            "w": w,
            "h": h,
            "deck_row": 11,          # left side, vertically centered
            "deck_col": 2,
            "dealer_row": 6,
            "dealer_col": 10,        # start right of the deck
            "player_row": 15,        # first player hand row
            "player_col": 10,        # start right of the deck
        }

    def _card_pos(self, hand_type, card_index, hand_index=0):
        """Target row,col where a card rests in a hand."""
        L = self.layout
        if hand_type == "dealer":
            row = L["dealer_row"]
            col = L["dealer_col"] + card_index * (CARD_W + 1)
        else:
            row = L["player_row"] + hand_index * (CARD_H + 2)
            col = L["player_col"] + card_index * (CARD_W + 1)
        return row, col

    # --------------------------------------------------------------- drawing
    def draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if w < 64 or h < 24:
            self._addstr_safe(h // 2, 2, "Terminal too small. Resize to at least 64x24.",
                              curses.A_BOLD)
            return

        self._compute_layout()

        self._draw_title(h, w)
        self._draw_money_hud(w)
        self._draw_deck(w)
        self._draw_dealer_hand()
        self._draw_player_hands()
        self._draw_message(w)
        self._draw_controls(w)
        self._draw_bet_input(w)

    def _addstr_safe(self, y, x, text, attr=0):
        try:
            hh, ww = self.stdscr.getmaxyx()
            if y < 0 or y >= hh or x < 0 or x >= ww:
                return
            self.stdscr.addnstr(y, x, text, max(0, ww - x - 1), attr)
        except curses.error:
            pass

    def _draw_title(self, h, w):
        title = "Black Jack | Fisher-Yates shuffled shoe | Real deck simulation"
        self._addstr_safe(h - 1, 2, title, curses.color_pair(3) | curses.A_DIM)

    def _draw_money_hud(self, w):
        g = self.game
        bankroll_attr = (
            curses.color_pair(4) if g.bankroll >= g.starting_bankroll else curses.color_pair(8)
        )
        bankroll_str = f"Bankroll: ${g.bankroll}"
        self._addstr_safe(3, 2, bankroll_str, bankroll_attr | curses.A_BOLD)

        bet_str = f"Bet: ${g.bet}"
        bet_x = 2 + len(bankroll_str) + 4
        self._addstr_safe(3, bet_x, bet_str, curses.color_pair(3) | curses.A_BOLD)

        shoe_str = f"Shoe: {g.deck.remaining} cards"
        shoe_x = bet_x + len(bet_str) + 4
        self._addstr_safe(3, shoe_x, shoe_str, curses.A_DIM)

        net_str = f"Net: ${g.net_profit:+d}"
        net_attr = curses.color_pair(4) if g.net_profit >= 0 else curses.color_pair(5)
        net_x = shoe_x + len(shoe_str) + 4
        self._addstr_safe(3, net_x, net_str, net_attr | curses.A_BOLD)

        sep_len = min(58, w - 4)
        self._addstr_safe(4, 2, "\u2500" * sep_len, curses.A_DIM)

    def _draw_deck(self, w):
        L = self.layout
        dr, dc = L["deck_row"], L["deck_col"]
        self._addstr_safe(dr - 1, dc, "DECK", curses.color_pair(7) | curses.A_BOLD)
        back_lines = render_card(None, hidden=True)
        for i, line in enumerate(back_lines):
            self._addstr_safe(dr + i, dc, line, curses.color_pair(2) | curses.A_DIM)

    def _is_animating(self, card):
        """True if a card object is currently being animated."""
        for a in self.anim.animations:
            if a.card is card:
                return True
        return False

    def _draw_dealer_hand(self):
        g = self.game
        hand = g.dealer
        row = self.layout["dealer_row"]
        col = self.layout["dealer_col"]

        self._addstr_safe(row - 1, col, "DEALER", curses.color_pair(7) | curses.A_BOLD)

        for i, card in enumerate(hand.cards):
            if self._is_animating(card):
                continue
            hidden = (not g.dealer_revealed and i == len(hand.cards) - 1)
            lines = render_card(card, hidden=hidden)
            r, c = self._card_pos("dealer", i)
            if hidden:
                attr = curses.A_DIM
            elif is_red_suit(card.suit):
                attr = curses.color_pair(1)
            else:
                attr = curses.color_pair(2)
            for li, line in enumerate(lines):
                self._addstr_safe(r + li, c, line, attr)

        for a in self.anim.animations:
            if a.hand_type != "dealer":
                continue
            lines = a.render()
            r, c = a.current_row, a.current_col
            if a.hidden:
                attr = curses.A_DIM
            elif is_red_suit(a.card.suit):
                attr = curses.color_pair(1)
            else:
                attr = curses.color_pair(2)
            for li, line in enumerate(lines):
                self._addstr_safe(r + li, c, line, attr)

        total_row = row + CARD_H + 1
        if g.dealer_revealed:
            tot = f"Total: {hand.total}"
            if hand.is_blackjack:
                tot += "  BLACKJACK!"
            elif hand.is_bust:
                tot += "  BUST"
            self._addstr_safe(total_row, col, tot, curses.A_BOLD)
        else:
            self._addstr_safe(total_row, col, "Total: ?", curses.A_DIM)

    def _draw_player_hands(self):
        g = self.game
        L = self.layout

        for hand_index, hand in enumerate(g.player_hands):
            row = L["player_row"] + hand_index * (CARD_H + 2)
            col = L["player_col"]

            if len(g.player_hands) > 1:
                label = "TOTAL:" if hand_index == 0 else f"PLAYER {hand_index + 1}"
            else:
                label = "TOTAL:"
            self._addstr_safe(row - 1, col, label, curses.color_pair(8) | curses.A_BOLD)

            for i, card in enumerate(hand.cards):
                if self._is_animating(card):
                    continue
                lines = render_card(card, hidden=False)
                r, c = self._card_pos("player", i, hand_index)
                if is_red_suit(card.suit):
                    attr = curses.color_pair(1)
                else:
                    attr = curses.color_pair(2)
                for li, line in enumerate(lines):
                    self._addstr_safe(r + li, c, line, attr)

            total_row = row + CARD_H + 1
            tot = f"Total: {hand.total}"
            if hand.is_blackjack:
                tot += "  BLACKJACK!"
            elif hand.is_bust:
                tot += "  BUST"
            self._addstr_safe(total_row, col, tot, curses.A_BOLD)

    def _draw_message(self, w):
        g = self.game
        # Place message below the last player hand total
        last_hand_row = self.layout["player_row"] + (len(g.player_hands) - 1) * (CARD_H + 2)
        y = last_hand_row + CARD_H + 3
        msg = g.message
        if not msg:
            if g.state == "BETTING":
                msg = "Place your bet to start."
            elif g.state == "PLAYER_TURN":
                msg = "Your turn."
            elif g.state == "DEALER_TURN":
                msg = "Dealer playing..."
            elif g.state == "GAME_OVER":
                msg = "Hand over."

        attr = curses.A_DIM
        if g.result in ("win", "blackjack"):
            attr = curses.color_pair(4) | curses.A_BOLD
        elif g.result in ("loss", "bust"):
            attr = curses.color_pair(5) | curses.A_BOLD
        elif g.result == "push":
            attr = curses.color_pair(6) | curses.A_BOLD
        elif g.result == "mixed":
            attr = curses.color_pair(3) | curses.A_BOLD
        self._addstr_safe(y, 2, msg[: w - 4], attr)

    def _draw_controls(self, w):
        g = self.game
        last_hand_row = self.layout["player_row"] + (len(g.player_hands) - 1) * (CARD_H + 2)
        y = last_hand_row + CARD_H + 5

        if self.reset_confirm:
            self._addstr_safe(
                y, 2,
                "RESET account to $1,000?  (Y)es  (N)o",
                curses.color_pair(5) | curses.A_BOLD,
            )
            return

        if g.state == "BETTING":
            self._addstr_safe(
                y, 2,
                "Type bet, then Enter.   [R] Reset account   [Q] Quit",
                curses.A_DIM,
            )
        elif g.state == "PLAYER_TURN":
            opts = ["[H] Hit", "[S] Stand"]
            hand = g.player_hands[g.active_hand_index]
            if len(hand.cards) == 2 and g.bet * 2 <= g.bankroll:
                opts.append("[D] Double")
            if g.can_split:
                opts.append("[Y] Split")
            opts.append("[R] Reset   [Q] Quit")
            self._addstr_safe(y, 2, "   ".join(opts), curses.A_BOLD)
        elif g.state == "GAME_OVER":
            self._addstr_safe(
                y, 2,
                "Any key: next hand   [R] Reset   [Q] Quit",
                curses.A_DIM,
            )

    def _draw_bet_input(self, w):
        if self.game.state != "BETTING" or self.reset_confirm:
            return
        last_hand_row = self.layout["player_row"] + (len(self.game.player_hands) - 1) * (CARD_H + 2)
        y = last_hand_row + CARD_H + 7
        prompt = f"Bet: ${self.bet_buf}"
        self._addstr_safe(y, 2, prompt, curses.color_pair(3) | curses.A_BOLD)
        cur_x = 2 + len(prompt)
        if cur_x < w - 1:
            self._addstr_safe(y, cur_x, " ", curses.A_REVERSE)

    # --------------------------------------------------------------- input
    def handle_key(self, key):
        g = self.game
        if g.state == "BETTING":
            return self._handle_betting(key)
        elif g.state == "PLAYER_TURN":
            return self._handle_player_turn(key)
        elif g.state == "GAME_OVER":
            g.next_hand()
            self.bet_buf = ""
            return True
        return True

    def _handle_betting(self, key):
        g = self.game
        if key in (curses.KEY_ENTER, 10, 13):
            if self.bet_buf.isdigit():
                if g.place_bet(int(self.bet_buf)):
                    self.bet_buf = ""
                    self._start_initial_deal_animations()
                else:
                    g.message = "Invalid bet."
            else:
                g.message = "Enter a number."
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.bet_buf = self.bet_buf[:-1]
            g.message = ""
        elif key in (ord("r"), ord("R")):
            self.reset_confirm = True
            g.message = ""
        elif 48 <= key <= 57:
            if len(self.bet_buf) < 6:
                self.bet_buf += chr(key)
                g.message = ""
        return True

    def _handle_player_turn(self, key):
        g = self.game
        if key in (ord("h"), ord("H")):
            g.player_hit()
            self._queue_hit_animation("player")
            if g.state == "DEALER_TURN":
                self._start_dealer_turn()
        elif key in (ord("s"), ord("S")):
            g.player_stand()
            self._start_dealer_turn()
        elif key in (ord("d"), ord("D")):
            g.player_double()
            self._queue_hit_animation("player")
            if g.state == "DEALER_TURN":
                self._start_dealer_turn()
        elif key in (ord("y"), ord("Y")):
            if g.can_split:
                g.split()
                self._start_split_animations()
        elif key in (ord("r"), ord("R")):
            self.reset_confirm = True
        return True

    # --------------------------------------------------------------- animations
    def _start_initial_deal_animations(self):
        """Fly the 4 initial cards from the deck to their hand slots."""
        g = self.game
        L = self.layout
        deck_r = L["deck_row"] + CARD_H // 2
        deck_c = L["deck_col"] + CARD_W // 2

        # Player card 0 -> player hand 0, card 0
        self.anim.add(CardAnimation(
            g.player_hands[0].cards[0], deck_r, deck_c,
            *self._card_pos("player", 0, 0), hidden=False,
            hand_type="player", hand_index=0,
        ))
        # Dealer card 0 (face up)
        self.anim.add(CardAnimation(
            g.dealer.cards[0], deck_r, deck_c,
            *self._card_pos("dealer", 0), hidden=False,
            hand_type="dealer", hand_index=0,
        ))
        # Player card 1 -> player hand 0, card 1
        self.anim.add(CardAnimation(
            g.player_hands[0].cards[1], deck_r, deck_c,
            *self._card_pos("player", 1, 0), hidden=False,
            hand_type="player", hand_index=0,
        ))
        # Dealer card 1 (face down during flight)
        self.anim.add(CardAnimation(
            g.dealer.cards[1], deck_r, deck_c,
            *self._card_pos("dealer", 1), hidden=True,
            hand_type="dealer", hand_index=0,
        ))

    def _start_split_animations(self):
        """Fly the newly dealt split cards to their hand positions."""
        g = self.game
        L = self.layout
        deck_r = L["deck_row"] + CARD_H // 2
        deck_c = L["deck_col"] + CARD_W // 2

        # Hand 0's new card (index 1) goes to hand 0 row
        self.anim.add(CardAnimation(
            g.player_hands[0].cards[1], deck_r, deck_c,
            *self._card_pos("player", 1, 0), hidden=False,
            hand_type="player", hand_index=0,
        ))
        # Hand 1's two cards go to hand 1 row
        for ci, card in enumerate(g.player_hands[1].cards):
            self.anim.add(CardAnimation(
                card, deck_r, deck_c,
                *self._card_pos("player", ci, 1), hidden=False,
                hand_type="player", hand_index=1,
            ))

    def _queue_hit_animation(self, hand_type):
        """Fly the most recently added card to its hand slot."""
        g = self.game
        L = self.layout
        deck_r = L["deck_row"] + CARD_H // 2
        deck_c = L["deck_col"] + CARD_W // 2

        if hand_type == "dealer":
            hand = g.dealer
            hand_index = 0
        else:
            hand = g.player_hands[g.active_hand_index]
            hand_index = g.active_hand_index

        card_index = len(hand.cards) - 1

        self.anim.add(CardAnimation(
            hand.cards[card_index], deck_r, deck_c,
            *self._card_pos(hand_type, card_index, hand_index), hidden=False,
            hand_type=hand_type, hand_index=hand_index,
        ))

    def _start_dealer_turn(self):
        g = self.game
        g.dealer_revealed = True
        self._dealer_hit_step()

    def _dealer_hit_step(self):
        g = self.game
        if g.state != "DEALER_TURN":
            return
        should_continue = g.dealer_hit_step()
        self._queue_hit_animation("dealer")
        if should_continue:
            self.pending_dealer_hit = True
        else:
            self.pending_resolve = True
