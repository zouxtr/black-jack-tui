"""Entry point for the animated Blackjack TUI game."""

import curses

from tui import BlackjackUI


def main():
    curses.wrapper(lambda stdscr: BlackjackUI(stdscr).run())


if __name__ == "__main__":
    main()
