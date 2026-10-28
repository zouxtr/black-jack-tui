"""Blackjack game logic with bankroll persistence and reset.

House rules (fixed, never adapts to the player):
  * Dealer hits on 16 or below, stands on all 17s.
  * Blackjack pays 3:2.
  * Double down allowed only on the first two cards, then exactly one card.
  * Deck is Fisher-Yates shuffled; card order is fixed after shuffle (unrigged).
"""

import json
import os
from deck import Card, Deck


try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
SAVE_FILE = os.path.join(_HERE, "save.json")


class Hand:
    def __init__(self):
        self.cards = []

    def add(self, card):
        self.cards.append(card)

    def clear(self):
        self.cards = []

    @property
    def total(self):
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_bust(self):
        return self.total > 21

    @property
    def is_blackjack(self):
        return len(self.cards) == 2 and self.total == 21

    @property
    def is_soft(self):
        aces = sum(1 for c in self.cards if c.rank == "A")
        if not aces:
            return False
        non_ace = sum(c.value for c in self.cards if c.rank != "A")
        return non_ace + aces + 10 <= 21

    def __str__(self):
        return " ".join(str(c) for c in self.cards)


class BlackjackGame:
    BLACKJACK_PAYOUT_NUM = 3
    BLACKJACK_PAYOUT_DEN = 2

    def __init__(self, bankroll=1000):
        self.starting_bankroll = bankroll
        self.bankroll = bankroll
        self.net_profit = 0
        self.bet = 0
        self.deck = Deck(num_decks=6)
        self.player = Hand()
        self.dealer = Hand()
        self.state = "BETTING"  # BETTING | PLAYER_TURN | DEALER_TURN | GAME_OVER
        self.message = ""
        self.result = None  # 'win' | 'loss' | 'push' | 'blackjack' | 'bust'
        self.dealer_revealed = False
        self.doubled = False

    # ------------------------------------------------------------------ persistence
    def save(self):
        data = {
            "bankroll": self.bankroll,
            "net_profit": self.net_profit,
            "starting_bankroll": self.starting_bankroll,
        }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
        except OSError:
            pass

    @classmethod
    def load(cls):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
            game = cls(bankroll=data.get("bankroll", 1000))
            game.net_profit = data.get("net_profit", 0)
            return game
        except (OSError, json.JSONDecodeError, ValueError):
            return cls(bankroll=1000)

    # ------------------------------------------------------------------ reset
    def reset(self):
        """Reset bankroll to $1,000 and clear the win/loss counter."""
        self.starting_bankroll = 1000
        self.bankroll = 1000
        self.net_profit = 0
        self.bet = 0
        self.player.clear()
        self.dealer.clear()
        self.state = "BETTING"
        self.message = ""
        self.result = None
        self.dealer_revealed = False
        self.doubled = False
        self.deck = Deck(num_decks=6)
        self.save()

    # ------------------------------------------------------------------ betting
    def place_bet(self, amount):
        if amount <= 0 or amount > self.bankroll:
            return False
        self.bet = amount
        self.state = "PLAYER_TURN"
        self._deal_initial()
        self.save()
        return True

    def _deal_initial(self):
        self.player.clear()
        self.dealer.clear()
        self.dealer_revealed = False
        self.doubled = False
        self.result = None
        self.message = ""
        # Player, dealer, player, dealer.
        self.player.add(self.deck.draw())
        self.dealer.add(self.deck.draw())
        self.player.add(self.deck.draw())
        self.dealer.add(self.deck.draw())
        if self.player.is_blackjack or self.dealer.is_blackjack:
            self.dealer_revealed = True
            self._resolve()

    # ---------------------------------------------------------------- player actions
    def player_hit(self):
        if self.state != "PLAYER_TURN":
            return
        self.player.add(self.deck.draw())
        if self.player.is_blackjack or self.player.is_bust:
            self.dealer_revealed = True
            self._resolve()
        elif self.player.total == 21:
            self.player_stand()

    def player_stand(self):
        if self.state != "PLAYER_TURN":
            return
        self.state = "DEALER_TURN"
        self.dealer_revealed = True
        # Dealer plays via animated hit steps in the TUI loop.

    def player_double(self):
        if self.state != "PLAYER_TURN":
            return
        if len(self.player.cards) != 2:
            return  # only on first two cards
        if self.bet * 2 > self.bankroll:
            return
        self.bet *= 2
        self.doubled = True
        self.player.add(self.deck.draw())
        self.dealer_revealed = True
        if self.player.is_bust:
            self._resolve()
        else:
            self.state = "DEALER_TURN"
            # Dealer plays via animated hit steps in the TUI loop.

    # ---------------------------------------------------------------- dealer turn
    def dealer_hit_step(self):
        """Dealer takes exactly one hit. Returns True if dealer should continue."""
        self.dealer.add(self.deck.draw())
        return not (self.dealer.is_bust or self.dealer.total >= 17)

    def _dealer_play(self):
        while not self.dealer.is_bust and self.dealer.total < 17:
            self.dealer.add(self.deck.draw())
        self._resolve()

    # ----------------------------------------------------------------- settlement
    def _resolve(self):
        self.state = "GAME_OVER"
        p = self.player.total
        d = self.dealer.total
        pb = self.player.is_bust
        db = self.dealer.is_bust
        p_bj = self.player.is_blackjack
        d_bj = self.dealer.is_blackjack

        if p_bj and d_bj:
            self.result = "push"
            self.message = "Both have blackjack. Push."
        elif p_bj:
            self.result = "blackjack"
            self.message = "Blackjack! You win 3:2."
            self.bankroll += self.bet * self.BLACKJACK_PAYOUT_NUM // self.BLACKJACK_PAYOUT_DEN
            self.net_profit += self.bet * self.BLACKJACK_PAYOUT_NUM // self.BLACKJACK_PAYOUT_DEN
        elif d_bj:
            self.result = "loss"
            self.message = "Dealer has blackjack. You lose."
            self.bankroll -= self.bet
            self.net_profit -= self.bet
        elif pb:
            self.result = "bust"
            self.message = "You bust. Dealer wins."
            self.bankroll -= self.bet
            self.net_profit -= self.bet
        elif db:
            self.result = "win"
            self.message = "Dealer busts. You win!"
            self.bankroll += self.bet
            self.net_profit += self.bet
        elif p > d:
            self.result = "win"
            self.message = f"You win ({p} vs {d})!"
            self.bankroll += self.bet
            self.net_profit += self.bet
        elif d > p:
            self.result = "loss"
            self.message = f"Dealer wins ({d} vs {p})."
            self.bankroll -= self.bet
            self.net_profit -= self.bet
        else:
            self.result = "push"
            self.message = f"Push ({p} vs {d})."
        self.save()

    def next_hand(self):
        self.player.clear()
        self.dealer.clear()
        self.state = "BETTING"
        self.message = ""
        self.result = None
        self.dealer_revealed = False
        self.doubled = False
        self.bet = 0
        self.save()
