# EditorConfig for Pluma

A plugin for [Pluma](https://github.com/mate-desktop/pluma), the MATE text
editor, that applies [EditorConfig](https://editorconfig.org) settings to the
files you edit.

This continues Filip Szymański's plugin from `github.com/fszymanski/pluma-plugins`,
which went offline in 2024 along with his GitHub account. The first commit here
is his final version (`3bcdb9b7`, 29 December 2023), recovered from the
[World of Code](https://worldofcode.org) archive. Everything after it is the
continuation.

## What it supports

It follows version 0.17.2 of the
[EditorConfig specification](https://spec.editorconfig.org):

| Key | In Pluma |
|---|---|
| `indent_style` | Spaces or tabs for indentation |
| `indent_size` | The indent width; `tab` makes it the tab width |
| `tab_width` | The width of a tab character |
| `end_of_line` | Line endings, applied when the file is opened and saved |
| `charset` | `latin1`, `utf-8`, `utf-16be` and `utf-16le`. Files are saved in it, and reopened in it if Pluma guessed another encoding when first opening them. Pluma can't write a byte order mark, so `utf-8-bom` is treated as `utf-8`; a file that starts with one keeps it |
| `trim_trailing_whitespace` | `true` trims trailing whitespace on save |
| `insert_final_newline` | `true` is what Pluma always does; `false` removes the final newline Pluma writes |
| `max_line_length` | Not in the specification, but widely used: sets the right margin, or hides it for `off` |

`unset` puts a setting back to Pluma's own preference, and so does saving a
file somewhere its EditorConfig no longer sets it. Unknown keys are ignored.
`spelling_language` isn't supported: Pluma gives plugins no way to set a
document's spell-checking language.

## Notes

- **Save Without Trailing Spaces:** Pluma's own plugin of that name trims every
  file on save, and other plugins can't stop it. Turn it off to let
  `trim_trailing_whitespace = false` take effect.
- **Encodings you choose:** a file you open in an encoding you pick yourself
  stays in that encoding while open, but is saved in its EditorConfig charset.
- **Comments after values:** since version 0.15.0 the specification says a `#`
  or `;` after a value is part of the value. The EditorConfig cores, including
  the Python one this plugin uses, still treat ` #` and ` ;` as starting a
  comment.

## Requirements

- Pluma with Python plugin support (libpeas 1.x and its python3 loader).
  Tested with Pluma 1.28.1.
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
