# Animated Blackjack TUI

A terminal Blackjack game with a **real, unrigged deck simulation**, animated card dealing,
and ASCII art cards. Built with Python 3 + `curses` (standard library — nothing to install).

## How it's unrigged

* The shoe (6 decks) is built once and Fisher-Yates shuffled at start.
* After shuffling, card order is **fixed**. Cards are dealt sequentially off the top of
  the shoe; nothing adapts to your hand or the dealer's hand.
* The dealer plays a **fixed house rule**: hit on 16 or below, stand on all 17s. The
  dealer never "magically" draws the card it needs.
* The shoe is reshuffled only when it runs down to the cut card (~25%).
* Animations are purely visual — they don't change which card is dealt next.

## Features

* **Animated card dealing** — cards fly from the deck to your hand and the dealer's hand.
* **ASCII art cards** — box-drawing card faces with colored suits (red hearts/diamonds,
  black spades/clubs) and face-down card backs.
* **Money HUD** — bankroll, current bet, and shoes remaining shown at the top.
* **Starting money** — begins at $1,000 (configurable); bankroll persists to `save.json`
  across sessions.
* **Reset account** — press `[R]` in betting mode to reset your bankroll to the starting
  amount (with confirmation).
* Standard rules: blackjack pays 3:2, dealer hits 16-/stands 17+, double down on first
  two cards only.

## Run

### Linux / macOS

```bash
cd /home/zouxtr/Documents/projekts/game_tui
python3 main.py
```

### One-line install (Linux) — run `black_jack_tui` from anywhere

```bash
curl -sSL https://raw.githubusercontent.com/zouxtr/black-jack-tui/main/install.sh | bash
```

This clones the repo to `~/.local/share/black-jack-tui` and creates a `black_jack_tui` command in `~/.local/bin`. After installing, just type:

```bash
black_jack_tui
```

If the command is not found, add `~/.local/bin` to your PATH:

```bash
export PATH="$PATH:$HOME/.local/bin"
```

Add that line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Windows

`curses` is **not** part of the Python standard library on Windows, so you need to install the `windows-curses` package first:

```powershell
# 1. Clone the repo
git clone https://github.com/zouxtr/black-jack-tui.git
cd black-jack-tui

# 2. Install the Windows curses package
pip install windows-curses

# 3. Run the game
python main.py
```

Alternatively, you can run it in [WSL](https://learn.microsoft.com/en-us/windows/wsl/) (Windows Subsystem for Linux), where it works out of the box with no extra install.

## Controls

| State | Key | Action |
|-------|-----|--------|
| Betting | `0`–`9` | Type your bet |
| Betting | `Enter` | Place bet & deal (cards animate) |
| Betting | `R` | Reset account (confirm with Y) |
| Betting | `Q` | Quit |
| Player turn | `H` | Hit (card animates to your hand) |
| Player turn | `S` | Stand (dealer plays) |
| Player turn | `D` | Double down (first 2 cards only) |
| Dealer turn | — | Dealer draws automatically with animation |
| Game over | any key | Next hand |
| Any | `Q` | Quit |

## Requirements

* Python 3.10+
* `curses` (included in Python standard library on Linux/macOS; install `windows-curses` on Windows)

No other `pip install` needed.
