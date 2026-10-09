#!/bin/sh
# Installs the plugin for the current user
set -e
cd "$(dirname "$0")"
install -Dm 644 -t "${XDG_DATA_HOME:-$HOME/.local/share}/pluma/plugins" editorconfig.plugin editorconfig_.py
