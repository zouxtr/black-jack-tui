"""Blackjack game logic with bankroll persistence, reset, and split pairs.

House rules (fixed, never adapts to the player):
  * Dealer hits on 16 or below, stands on all 17s.
  * Blackjack pays 3:2.
  * Double down allowed only on the first two cards, then exactly one card.
  * Split allowed on any pair (same value cards), one split per hand, no re-split.
  * After splitting Aces, each hand receives exactly one more card.
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

    @property
    def is_pair(self):
        """True if the hand has exactly two cards of the same value."""
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

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
        self.split_bet = 0  # additional bet placed when splitting
        self.deck = Deck(num_decks=6)
        self.player_hands = [Hand()]  # list of player hands (split creates more)
        self.active_hand_index = 0
        self.dealer = Hand()
        self.state = "BETTING"  # BETTING | PLAYER_TURN | DEALER_TURN | GAME_OVER
        self.message = ""
        self.result = None  # 'win' | 'loss' | 'push' | 'blackjack' | 'bust' | 'mixed'
        self.dealer_revealed = False
        self.doubled = False
        self.split_done = False  # whether a split has occurred this round

    # ------------------------------------------------------------------ compatibility
    @property
    def player(self):
        """Return the currently active player hand (for backwards compatibility)."""
        return self.player_hands[self.active_hand_index]

    @player.setter
    def player(self, value):
        self.player_hands[self.active_hand_index] = value

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
        self.split_bet = 0
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        self.dealer.clear()
        self.state = "BETTING"
        self.message = ""
        self.result = None
        self.dealer_revealed = False
        self.doubled = False
        self.split_done = False
        self.deck = Deck(num_decks=6)
        self.save()

    # ------------------------------------------------------------------ betting
    def place_bet(self, amount):
        if amount <= 0 or amount > self.bankroll:
            return False
        self.bet = amount
        self.split_bet = 0
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        self.state = "PLAYER_TURN"
        self._deal_initial()
        self.save()
        return True

    def _deal_initial(self):
        self.dealer.clear()
        self.dealer_revealed = False
        self.doubled = False
        self.split_done = False
        self.result = None
        self.message = ""
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        # Player, dealer, player, dealer.
        self.player_hands[0].add(self.deck.draw())
        self.dealer.add(self.deck.draw())
        self.player_hands[0].add(self.deck.draw())
        self.dealer.add(self.deck.draw())
        if self.player_hands[0].is_blackjack or self.dealer.is_blackjack:
            self.dealer_revealed = True
            self._resolve()

    # ---------------------------------------------------------------- split
    @property
    def can_split(self):
        """True if the active hand can be split (pair, first two cards, enough bankroll)."""
        if self.split_done:
            return False  # no re-splitting
        if self.state != "PLAYER_TURN":
            return False
        hand = self.player_hands[self.active_hand_index]
        if len(self.player_hands) > 1:
            return False  # already split this round
        if len(hand.cards) != 2:
            return False
        if not hand.is_pair:
            return False
        # Need enough bankroll to match the bet on the second hand
        if self.bet * 2 > self.bankroll + self.bet:  # bet already deducted? no, bet is separate
            return False
        return self.bankroll >= self.bet

    def split(self):
        """Split the active hand into two hands, placing a matching bet."""
        if not self.can_split:
            return False

        hand = self.player_hands[0]
        c1, c2 = hand.cards[0], hand.cards[1]

        # Build two new hands
        hand1 = Hand()
        hand1.add(c1)
        hand2 = Hand()
        hand2.add(c2)

        # Deal one card to each hand
        hand1.add(self.deck.draw())
        hand2.add(self.deck.draw())

        self.player_hands = [hand1, hand2]
        self.active_hand_index = 0
        self.split_bet = self.bet  # matching bet for second hand
        self.bankroll -= self.bet  # charge for the additional bet
        self.split_done = True
        self.save()

        # If either hand is blackjack after split, resolve immediately
        self._check_hand_done()
        return True

    def _check_hand_done(self):
        """If current hand is done (bust or 21), move to next hand or dealer."""
        hand = self.player_hands[self.active_hand_index]
        if hand.is_bust or hand.total == 21:
            self._next_hand_or_dealer()

    def _next_hand_or_dealer(self):
        """Advance to the next player hand, or to the dealer turn."""
        if self.active_hand_index < len(self.player_hands) - 1:
            self.active_hand_index += 1
        else:
            self.state = "DEALER_TURN"
            self.dealer_revealed = True

    # ---------------------------------------------------------------- player actions
    def player_hit(self):
        if self.state != "PLAYER_TURN":
            return
        hand = self.player_hands[self.active_hand_index]
        # After splitting Aces, each hand gets exactly one card (already dealt)
        if self.split_done and hand.cards[0].rank == "A" and len(hand.cards) >= 2:
            return
        hand.add(self.deck.draw())
        self._check_hand_done()

    def player_stand(self):
        if self.state != "PLAYER_TURN":
            return
        self._next_hand_or_dealer()

    def player_double(self):
        if self.state != "PLAYER_TURN":
            return
        hand = self.player_hands[self.active_hand_index]
        if len(hand.cards) != 2:
            return  # only on first two cards of the hand
        total_bet = self.bet + (self.split_bet if self.active_hand_index == 1 else 0)
        if total_bet * 2 > self.bankroll:
            return
        # Double the bet for this hand only
        if self.active_hand_index == 0:
            self.bet *= 2
        else:
            self.split_bet *= 2
        self.bankroll -= total_bet  # charge the additional amount
        self.doubled = True
        hand.add(self.deck.draw())
        self.dealer_revealed = True
        self._check_hand_done()

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
        """Resolve all player hands against the dealer."""
        self.state = "GAME_OVER"
        d = self.dealer.total
        db = self.dealer.is_bust
        d_bj = self.dealer.is_blackjack
        is_split = len(self.player_hands) > 1

        total_profit = 0
        results = []
        msg_parts = []

        for i, hand in enumerate(self.player_hands):
            hand_bet = self.bet if i == 0 else self.split_bet
            p = hand.total
            pb = hand.is_bust
            p_bj = hand.is_blackjack

            if p_bj and d_bj:
                results.append("push")
                msg_parts.append("Hand 1: PUSH!" if is_split else "PUSH!")
            elif p_bj and not d_bj:
                # Blackjack after split pays 1:1 (standard casino rule)
                win_amount = hand_bet
                total_profit += win_amount
                self.bankroll += win_amount
                results.append("win")
                msg_parts.append("BLACKJACK!" if not is_split else f"Hand {i+1}: BLACKJACK!")
            elif d_bj:
                total_profit -= hand_bet
                self.bankroll -= hand_bet
                results.append("loss")
                msg_parts.append("DEALER HAS BLACKJACK! YOU LOSE." if not is_split else f"Hand {i+1}: LOSE!")
            elif pb:
                total_profit -= hand_bet
                self.bankroll -= hand_bet
                results.append("bust")
                msg_parts.append("YOU BUST! DEALER WINS." if not is_split else f"Hand {i+1}: BUST!")
            elif db:
                total_profit += hand_bet
                self.bankroll += hand_bet
                results.append("win")
                msg_parts.append("DEALER BUSTS! YOU WIN!" if not is_split else f"Hand {i+1}: WIN!")
            elif p > d:
                total_profit += hand_bet
                self.bankroll += hand_bet
                results.append("win")
                msg_parts.append("YOU WIN!" if not is_split else f"Hand {i+1}: WIN!")
            elif d > p:
                total_profit -= hand_bet
                self.bankroll -= hand_bet
                results.append("loss")
                msg_parts.append("DEALER WINS!" if not is_split else f"Hand {i+1}: LOSE!")
            else:
                results.append("push")
                msg_parts.append("PUSH!" if not is_split else f"Hand {i+1}: PUSH!")

        self.net_profit += total_profit

        # Determine overall result
        if not is_split:
            # Single hand: use the specific message part directly
            self.message = msg_parts[0]
            if results[0] in ("win", "blackjack"):
                self.result = "win"
            elif results[0] in ("loss", "bust"):
                self.result = "loss"
            else:
                self.result = "push"
        elif all(r == "push" for r in results):
            self.result = "push"
            self.message = "PUSH!"
        elif all(r in ("win", "blackjack") for r in results):
            self.result = "win"
            self.message = " | ".join(msg_parts)
        elif all(r in ("loss", "bust") for r in results):
            self.result = "loss"
            self.message = "YOU LOSE!"
        else:
            self.result = "mixed"
            self.message = " | ".join(msg_parts)

        self.save()

    def next_hand(self):
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        self.dealer.clear()
        self.state = "BETTING"
        self.message = ""
        self.result = None
        self.dealer_revealed = False
        self.doubled = False
        self.split_bet = 0
        self.split_done = False
        self.bet = 0
        self.save()
