#!/usr/bin/env bash
# Install Blackjack TUI on Linux so you can run `black_jack_tui` from anywhere.
set -euo pipefail

REPO_URL="https://github.com/zouxtr/black-jack-tui.git"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/black-jack-tui"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
BIN_NAME="black_jack_tui"

echo "==> Installing Blackjack TUI to $INSTALL_DIR"

# Clone the repo (shallow)
if [ -d "$INSTALL_DIR" ]; then
    echo "==> Existing installation found, updating..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

# Make sure the bin directory exists
mkdir -p "$BIN_DIR"

# Create the launcher script
cat > "$BIN_DIR/$BIN_NAME" <<LAUNCHER
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
LAUNCHER

chmod +x "$BIN_DIR/$BIN_NAME"

echo "==> Installed!"
echo ""
echo "You can now run the game from anywhere by typing:"
echo "    black_jack_tui"
echo ""
echo "If the command is not found, make sure $BIN_DIR is in your PATH:"
echo "    export PATH=\"\$PATH:$BIN_DIR\""
echo "Add that line to your ~/.bashrc or ~/.zshrc to make it permanent."
echo ""
