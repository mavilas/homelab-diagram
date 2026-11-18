# homelab-diagram

> **Fork note.** This is `mavilas/homelab-diagram`, a fork of
> [Goblinmine/homelab-diagram](https://github.com/Goblinmine/homelab-diagram) (MIT, "Copyright (c) 2026
> Goblinmine"). The fork adds an importable style library, a declarative spec renderer with a headless CLI,
> a librsvg preflight, pinned and hash-checked icons and tests. The original lab still renders byte for byte
> as upstream did.

The script behind the network diagram of my homelab that I posted on r/homelab. It turns a YAML file describing the lab into a big SVG/PNG diagram in the style of the diagrams you see on r/homelab.

![Example output](docs/example.png)

> [!IMPORTANT]
> **This is not a general tool.** The *content* comes from `inventory.yaml`, but the *layout* (where every box, port and cable goes) is hand-placed in `build.py` for exactly my network. If you want to use it for yours, expect to move coordinates around in the code. Think of it as a starting point, not a finished product.

> [!NOTE]
> **The code was written by AI.** I built this together with Claude (Anthropic) in Claude Code. I described what I wanted and gave feedback on every render, Claude wrote and changed the code. A few example prompts are at the end of this README.

## What it shows

- the path from the internet through the ISP router (with its real ports) and the firewall to the core switch
- every switch port with the VLANs on it (tall bar = untagged, short bars = tagged)
- cables whose **line width is the negotiated link speed** (10G / 2.5G / 1G / 100M), trunks drawn as a white cable with a dark core
- the devices with name, type, model, IP · hostname and OS
- the Proxmox host with its hardware, the VMs/CTs outside the DMZ, the TrueNAS pools (disks, vdevs, usage) and every DMZ container with its CT ID, IP and hostname
- containers that run several apps as one card with a row per app
- what's open to the internet, a legend, the networks table and a small "media pipeline" explainer

## How it works

- `inventory.yaml` holds everything the picture shows: VLANs, devices, switch ports, port forwards, hardware, containers, pools.
- `build.py` draws the diagram as SVG with hand-placed coordinates (`original/top.py`, `original/server.py`, on top of the `homelab_diagram` library), embeds the icons and converts it to PNG with `rsvg-convert`. Text widths for a few labels are measured with Pillow from the real font, so tabs and badges fit their text.
- **Redaction:** by default the real domain is replaced with `redacted.com` and SSIDs get generic names, so the PNG can be posted publicly. `python3 build.py --unredacted` renders a private version with the real values from `inventory.yaml`.

## Requirements

- Python 3.11+ with **PyYAML** and **Pillow** (Pillow is optional, but makes label widths exact). Both are declared in `pyproject.toml`, so [uv](https://docs.astral.sh/uv/) installs them for you — see below.
- **rsvg-convert from librsvg 2.60 or newer** for the PNG. Older librsvg (Debian bookworm ships 2.54)
  renders the cards but **silently drops every icon**. `build.py` and the CLI run a preflight that checks the
  version and renders a probe icon, and stop with an error instead of writing an incomplete picture.
  Debian trixie, current Arch and Homebrew ship 2.60 or newer.
- the fonts **Fira Sans** and **Fira Code** installed (found via fontconfig)

On Arch/CachyOS: `pacman -S python-yaml python-pillow librsvg ttf-fira-sans ttf-fira-code`
On Debian/Ubuntu: `apt install python3-yaml python3-pil librsvg2-bin fonts-firacode` plus Fira Sans
On macOS: `brew install librsvg`, then install the Fira fonts from [mozilla/Fira](https://github.com/mozilla/Fira) (e.g. `brew install --cask font-fira-code font-fira-sans`, if your Homebrew has them).

## Usage

With [uv](https://docs.astral.sh/uv/) (creates `.venv` and installs the pinned dependencies from `uv.lock`):

```bash
uv sync                         # once: create .venv, install PyYAML + Pillow
uv run fetch_icons.py           # downloads the service icons into icons/ (once)
uv run build.py                 # → out/homelab.svg + out/homelab.png (redacted)
uv run build.py --unredacted    # → out/homelab-unredacted.svg + .png
```

Or with a plain Python install of PyYAML:

```bash
python3 fetch_icons.py          # downloads the service icons into icons/ (once)
python3 build.py                # → out/homelab.svg + out/homelab.png (redacted)
python3 build.py --unredacted   # → out/homelab-unredacted.svg + .png
```

The service icons are **not** in this repo, `fetch_icons.py` downloads them from [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons) at the commit pinned in `icons.lock.json` and checks each file's sha256. Only my own small glyphs (`icons/glyph-*.svg`: CPU, RAM, SSD, …) are included.

## Spec renderer and library (fork)

Write a spec instead of moving coordinates around. The format is in [docs/spec.md](docs/spec.md); a full
example is [examples/small-lab.yaml](examples/small-lab.yaml).

```bash
python3 fetch_icons.py                                    # pinned icons, sha256-checked (network)
python3 -m homelab_diagram check --icon-dir icons         # librsvg >= 2.60, icons survive, fonts, icon lock
python3 -m homelab_diagram validate examples/small-lab.yaml
python3 -m homelab_diagram render examples/small-lab.yaml -o out/small-lab.png [--svg out/small-lab.svg]
```

Rendering is offline and deterministic: the same spec, icons, fonts and librsvg give the same bytes. It never
opens a network connection; extra icon directories come from `--icons DIR` or `HOMELAB_DIAGRAM_ICON_DIRS`.
Exit status is 0 on success, 1 when the spec, an icon, the layout or the renderer check fails, 2 on usage
errors. Text that does not fit its card is an error, not an overflow.

The drawing code is importable. The stable API is what `homelab_diagram/__init__.py` exports:

| Area | Names |
|---|---|
| Themes | `Theme`, `DARK`, `LIGHT`, `THEMES` |
| Primitives | `Canvas` (`rect`, `text`, `icon`, `line`, `trunk`, `arrow`, `pill`, `label`, `begin`, `finish`), `rounded` |
| Pieces | `card`, `device_card`, `folder`, `hw_bar`, `zone`, `addr`, `tab_width`, `TAB` |
| Icons | `IconStore`, `IconError` |
| Specs | `Spec`, `Group`, `Node`, `Item`, `Link`, `LegendEntry`, `parse_spec`, `load_spec`, `SpecError` |
| Layout and output | `draw`, `LayoutError`, `render`, `render_svg`, `preflight`, `PreflightError`, `MIN_LIBRSVG` |

```python
from homelab_diagram import Canvas, IconStore, DARK, card
c = Canvas(1200, DARK, IconStore(["icons"]))
c.begin()
card(c, 40, 40, 400, 64, DARK.color("blue"), "Postgres", ["postgresql"], "primary")
svg = c.finish(150)
```

### Icons are pinned

`icons.lock.json` records the dashboard-icons commit, the URL template and the sha256 of every icon file.
`fetch_icons.py` downloads only from that commit (never a branch) and rejects a file whose hash differs.
`python3 fetch_icons.py --verify` checks an icons directory offline.

### Tests

```bash
python3 fetch_icons.py && python3 -m unittest discover -s tests -t .
```

The suite needs the reference environment: Python 3.11+, PyYAML, Pillow, rsvg-convert 2.60+, Fira Sans
and Fira Code, and the fetched icons. Tests that need it fail instead of skipping. It covers spec validation,
the icon lock, the librsvg preflight (including a fake 2.54 and a fake converter that drops icons), a
spec-to-PNG smoke render, byte-for-byte determinism and the original build's SVG against upstream.
CI (`.github/workflows/test.yml`) runs it in Debian trixie.

## Making it your own

1. Change `inventory.yaml` to your network. Texts, IPs, ports, VLAN colors and the container groups come from there.
2. Look at the render. Things that don't fit are layout: the top part (cloud, ISP router, firewall, switch, device row) and the column split inside the server card are coordinates in `original/top.py` and `original/server.py` (search for `fy, fh`, `ox, oy`, `bx, by`, `DY`, `MAD = …`).
3. New icons: drop an SVG into `icons/` and use its file name in the inventory.

## Using it with Claude Code

The repo contains a [`CLAUDE.md`](CLAUDE.md) with everything an AI agent needs to adapt it to your lab: how the code is structured, which parts of the layout are hardcoded, the questions to ask about your network, the render-and-check loop, and the design rules this diagram follows.

Clone the repo, open it with [Claude Code](https://claude.com/claude-code) and say something like *"help me make this diagram for my homelab"*. It will interview you about your network (or read your docs if you have some), write a spec and iterate on the render with you. In this fork the agent instructions forbid running commands on your hosts; the agent works only from your answers and documents. Other agents can use the same file as context.

## How it was made

I had seen these diagrams on r/homelab for years and always wanted one for my own network. My setup was documented in an Obsidian vault (written by another Claude Code session, checked against the live systems), so the workflow was:

1. **Gathering the facts.** Claude Code read the documentation and filled the gaps with read-only checks on the live systems: link speeds from the switch, disk models and pool usage from TrueNAS, the router model from its info page, hostnames from DNS, the containers running in each CT.
2. **First draft.** Claude wrote `inventory.yaml` and `build.py`, rendered the PNG and looked at the image itself (plus zoomed-in crops) to catch overlaps before showing it to me.
3. **Iterating.** Then it was me giving feedback, Claude changing the code, re-rendering and checking again, about 60 rounds. Most of the design decisions (folder-shaped device cards, line width = speed, CT on top and IP below, no internal ports, …) came out of that back and forth.
4. **Publishing.** For this repo Claude made a cleaned-up copy (example domain, generic SSIDs), added the icon download script and checked that a fresh clone renders exactly the posted image.

Tools: Claude Code with Claude Opus 5.5, Python, librsvg, Pillow.

## Example prompts

About 60 prompts went into this. Three typical ones, to give an idea of how the back and forth looked:

**Getting started**
> Do you know the network diagrams people post on r/homelab? I'd like one for my own network. My setup is documented in my Obsidian vault, read it and check the live systems for anything that's missing.

**Design feedback**
> Use the line thickness to show the link speed and put a small speed label where each cable reaches a device. Also remove the interface names like em0 or igc0, nobody needs them on a diagram.

**Fixing the facts**
> That's not quite right yet: there are two shares. qBittorrent only downloads into the Torrents share, and when a download is done Sonarr/Radarr copy the file with the right name into the Media share. qBittorrent has no access to the Media share at all.

## Credits & license

- Code and the glyph icons in `icons/`: MIT, Copyright (c) 2026 Goblinmine, see [LICENSE](LICENSE). Fork changes are under the same license.
- Service icons: [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons), downloaded by `fetch_icons.py`, not part of this repo. The logos belong to their projects.
- Fonts: [Fira Sans / Fira Code](https://github.com/mozilla/Fira) (SIL Open Font License), not included.

### Spec and tool failure behavior

Spec version must be an integer. JSON and YAML mapping keys must be unique
strings; malformed reference types produce a validation error rather than a
Python traceback. Font and renderer subprocesses use the vendored TERM-only
process-group supervisor, whose source and digest are recorded in
[the audit fix plan](docs/audits/2026-11-19-post-merge-fix-plan.md).
A timed-out or failed converter cannot overwrite previous PNG or SVG outputs.
Successful outputs are replaced atomically per file after conversion; publishing
two files is not a filesystem transaction.

Built distributions include the lock and the repository's own glyphs, generated
from the canonical source files at build time. Third-party service icons still
require the pinned fetch step or an explicit icon directory.
