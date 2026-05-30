# Volkov Commander — reference sources (NOT ported code)

These are the original **Volkov Commander** sources by Vsevolod V. Volkov,
vendored here purely as a **reference specification** for Volkov Data's UI:
two-pane layout, F1–F10 function-key behavior, keybindings, dialogs, and the
status bar.

## Important: reference only

- The original is **x86 assembly** and is **not** ported to Python. We read it
  to understand *behavior*, not to translate it line by line.
- Per the project brief: **when porting any logic, retain the 2-clause BSD
  copyright notice** (`versions/*/LICENSE.TXT`, Copyright 1991–2000
  Vsevolod V. Volkov).

## Most relevant files (4.99.09 is the more complete tree)

- `VCKEYB.INC`   — keyboard interface / scan codes
- `VCPANELS.INC` — two-pane panel layout and drawing
- `VCFUNC.INC`   — F-key function dispatch
- `VCMENU.INC`   — menus
- `VCDIALOG.INC` — dialog boxes
- `VCSCREEN.INC` — screen / drawing primitives
- `VCVIEW.INC` / `VCEDIT.INC` — viewer / editor behavior

`archives/` keeps the original ZIPs for provenance. See `README.md` (upstream)
for authorship and historical context.
