# EditorConfig for Pluma

A plugin for [Pluma](https://github.com/mate-desktop/pluma), the MATE text
editor, that applies [EditorConfig](https://editorconfig.org) settings to the
files you edit.

This is Filip Szymański's plugin from `github.com/fszymanski/pluma-plugins`,
which went offline in 2024 along with his GitHub account: his final version
(`3bcdb9b7`, 29 December 2023), recovered from the
[World of Code](https://worldofcode.org) archive.

## What it supports

| Key | In Pluma |
|---|---|
| `indent_style` | Spaces or tabs for indentation |
| `indent_size` | The tab width |
| `tab_width` | The tab width |
| `end_of_line` | Line endings |
| `trim_trailing_whitespace` | `true` trims trailing whitespace on save. Pluma's own Save Without Trailing Spaces plugin, if it's on, trims every file anyway |
| `max_line_length` | Not in the EditorConfig specification, but widely used: sets the right margin, or hides it for `off` |

`charset` and `insert_final_newline` aren't supported.

## Requirements

- Pluma with Python plugin support (libpeas 1.x and its python3 loader).
- PyGObject.
- The EditorConfig Python core: `python-editorconfig` on Arch,
  `python3-editorconfig` on Debian, Ubuntu and Fedora, or `EditorConfig` from
  PyPI.
- Python 3.8 or later.

## Installing

Run `./install.sh` to install it for your user, into
`~/.local/share/pluma/plugins`. To install it for every user, copy
`editorconfig.plugin` and `editorconfig_.py` into Pluma's system plugin
directory instead:

- Arch: `/usr/lib/pluma/plugins`
- Debian and Ubuntu: `/usr/lib/x86_64-linux-gnu/pluma/plugins` on 64-bit x86
- Fedora: `/usr/lib64/pluma/plugins`
- Elsewhere: run `pkg-config --variable=pluginsdir pluma`, with Pluma's
  development files installed

Then turn it on under Edit › Preferences › Plugins.

## License

GPL-3.0-or-later. See `COPYING`.
