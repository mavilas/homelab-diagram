# Spec format (version 1)

A spec is a YAML or JSON document. Unknown keys, unknown ids and invalid values are errors that name the
path (for example `nodes[3].group: unknown group 'dmz'`). Text fields are single lines of at most 200
characters. Colors are `#rrggbb` or an accent name: `blue`, `purple`, `cyan`, `green`, `orange`, `red`,
`yellow`, `pink`, `grey`, `tan`. Link speeds are `10G`, `2.5G`, `1G`, `100M` (line width = link speed).

| Key | Required | Meaning |
|---|---|---|
| `version` | yes | `1` |
| `title` | yes | top-left title |
| `subtitle` | no | top-right text, for example a date |
| `footer` | no | small text under everything, for example the source of the facts |
| `theme` | no | `dark` (default) or `light` |
| `width` | no | canvas width in SVG units, 800 to 6000, default 2400 (PNG is 1.6 times larger) |
| `columns` | no | group slots per row, 1 to 8, default 2 |
| `groups` | no | list of groups (below) |
| `nodes` | yes | list of nodes (below), at least one |
| `links` | no | list of links (below) |
| `legend` | no | list of legend rows (below) |

**Group:** `id` (required), `label`, `note`, `tag` (pill top-right), `color`, `columns` (node columns inside
the group, default 1), `span` (group slots it takes, default 1). Groups fill rows in spec order.

**Node:** `id` and `label` (required), `kind` (`service` card, the default, or `device` folder card), `group`,
`icon`, `color` (default: the group color), `note`.
A `device` also needs `type` (shown on the tab after the label) and may have `model`, `address`, `os` and
`items` (up to 12 service rows with `label`, `note`, `icon`). Nodes without a group form a band at the top.

**Link:** `from`, `to` (node ids, required), `style` (`solid`, `dashed`, `dotted`), `color`, either `speed`
or `width` (0.5 to 20), `label`. Same-row nodes connect side to side; otherwise the cable turns in the gap
above the lower node's group. Keep linked nodes in adjacent rows for clean cables.

**Legend row:** `label` (required), `style`, `color`, `speed` or `width`.

Icons are file names (without extension) in the icon directories: `icons/` (the pinned dashboard-icons
plus the `glyph-*` set), any `--icons DIR`, and `HOMELAB_DIAGRAM_ICON_DIRS`. SVG and PNG files work.
