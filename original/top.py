"""Top half of the original lab: header, edge chain, switch, device row, port forwards, legend, networks."""
from .common import *  # noqa: F401,F403  (the layout reads the shared inventory and helpers by name)

# ---------------------------------------------------------------- background + header
S.begin()   # background + dot grid: drawn at the end, once the canvas height is known

meta = INV["meta"]
title = meta["title"] if (UNREDACTED or not RED["domain"]) else meta["title_redacted"]
S.text(40, 86, title, 46, TEXT, 700, ls=-0.5)
S.text(W - 40, 74, meta["watermark"], 21, REDDIT, 700, "end")
S.text(W - 40, 100, meta["date"], 16, MUTED, 400, "end")

# ================================================================ TOP: edge chain
CX = 1200
cy0 = 172
fy, fh = 324, 104                          # Fritzbox (body; tab above)
ox, oy, ow, oh = 670, 468, 850, 430         # OPNsense (hardware list left, services right)
bx, by, bw, bh = 620, 990, 1000, 112       # switch
SB = by + bh
PX0, PITCH = bx + 320, 58
ALL_VLANS = ["10", "20", "30", "40", "99"]


N_RJ = sum(1 for p in INV["switch"]["ports"] if not p["name"].startswith("sfpp"))   # RJ45 ports come first


def port_x(i):
    """Center x of switch port i (0..N_RJ-1 RJ45, then SFP+)."""
    return PX0 + i * PITCH + 24 if i < N_RJ else PX0 + N_RJ * PITCH + 22 + (i - N_RJ) * 70 + 30


# Remote access: reaches home over the internet (dotted = logical, not a cable).
rw = INV["remote"]
rx_, ry_ = 700, 150
S.line([(rx_ + 300, ry_ + 42), (CX - 100, ry_ + 42)], C["vpn"], 1.8, dash="2 5", r=0)

# Internet cloud (circles: outline trick)
blobs = [(-95, 18, 42), (-45, -8, 56), (25, -18, 62), (90, 6, 48), (130, 26, 30), (-130, 30, 28)]
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r+2.5}" fill="#3a4a60"/>')
S.add(f'<rect x="{CX-150}" y="{cy0+12}" width="300" height="46" rx="23" fill="#3a4a60"/>')
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r}" fill="#1a2433"/>')
S.add(f'<rect x="{CX-147.5}" y="{cy0+14.5}" width="295" height="41" rx="20.5" fill="#1a2433"/>')
S.text(CX, cy0 + 14, "Internet", 26, TEXT, 600, "middle")
S.text(CX, cy0 + 40, "semi-static public IPv4", 13, MUTED, 400, "middle")

S.rect(rx_, ry_, 300, 84, rx=12, fill=PANEL, stroke=C["vpn"] + "aa", sw=1.6)
S.icon("wireguard", rx_ + 16, ry_ + 22, 38)
S.text(rx_ + 66, ry_ + 38, rw["name"], 18, TEXT, 600)
S.text(rx_ + 66, ry_ + 60, rw["note"], 13, MUTED, 400)

csx, csy = 1790, 146
for i, cs in enumerate(INV["internet"]["cloud_services"]):
    y = csy + i * 54
    S.rect(csx, y, 570, 44, rx=10, fill=PANEL2, stroke=BORDER)
    S.icon(cs["icon"], csx + 10, y + 9, 26)
    S.text(csx + 46, y + 20, cs["name"], 14, TEXT, 600)
    S.text(csx + 46, y + 36, cs["note"], 12, MUTED, 400)
S.line([(CX + 130, 168), (csx, 168)], FAINT, 1.6, dash="2 5", r=0)
S.line([(CX + 150, 222), (csx, 222)], FAINT, 1.6, dash="2 5", r=0)

# Fritzbox: owns the internet uplink, NATs as usual, OPNsense is its exposed host
fb = INV["fritzbox"]
ISPD = INV["internet"]["speed"]
S.label(CX - 10, (cy0 + 58 + fy - TAB) / 2 + 5, "↓ " + ISPD["down"], "#c3cdd9", 12, anchor="end", mono=True)
S.label(CX + 10, (cy0 + 58 + fy - TAB) / 2 + 5, "↑ " + ISPD["up"], "#c3cdd9", 12, anchor="start", mono=True)
FBX, FBW = CX - 302, 620                   # coax port sits right under the internet line (x = CX)
FB_PORTS = [] if fb.get("stub") else [("Cable", None)] + [(sp, None) for sp in fb["lan_ports"]]
if fb.get("stub"):                         # ISP-managed box (ONT, modem): small box, WAN goes straight down
    S.line([(CX, cy0 + 58), (CX, fy + fh)], C["wan"], SPEED_W["1G"])
    S.rect(CX - 170, fy + fh - 92, 340, 62, rx=12, fill=PANEL, stroke=C["wan"] + "aa", sw=1.6)
    S.text(CX, fy + fh - 66, f"{fb['name']} · {fb['type']}", 16, TEXT, 600, "middle")
    S.text(CX, fy + fh - 46, fb["model"], 12.5, MUTED, 400, "middle")
    WANX = CX
else:
    device_card(FBX, fy, FBW, fh, ["fritzbox"], fb, C["wan"])
    S.line([(CX, cy0 + 58), (CX, fy + 28)], "#6b7a90", 3)
COAX_X = FBX + 302
for i, (lbl, _) in enumerate(FB_PORTS):
    if i == 0:
        cx_ = COAX_X
        S.rect(cx_ - 22, fy + 28, 44, 36, rx=5, fill="#2a3443", stroke=TRUNK, sw=1.4)
        S.add(f'<circle cx="{cx_}" cy="{fy+46}" r="11" fill="#0b0f15" stroke="#5a6b82" stroke-width="2"/>'
              f'<circle cx="{cx_}" cy="{fy+46}" r="2.5" fill="{TRUNK}"/>')
        S.label(cx_, fy + 20, "Cable", MUTED, 11, mono=True, bg=PANEL)   # the internet line passes behind it
        S.text(cx_, fy + fh - 9, "internet", 10.5, MUTED, 500, "middle")
        continue
    cx_ = FBX + 366 + (i - 1) * 52
    used = (i - 1) == fb["opnsense_port"]
    jack(cx_ - 22, fy + 28, 44, 36, (C["wan"] + "55") if used else "#1b222c", C["wan"] if used else "#3a475a")
    S.text(cx_, fy + 21, lbl, 11, MUTED, 500, "middle", mono=True)
    if used:
        WANX = cx_
        ticks(cx_, fy + 69, untagged="wan")
        S.text(cx_, fy + fh - 9, "exposed host", 10.5, C["wan"], 600, "middle")

# OPNsense card (jacks: em0 on top where the WAN comes in, the dual NIC at the bottom above switch ports 1+2)
opn = INV["opnsense"]
device_card(ox, oy, ow, oh, ["opnsense"], opn, C["99"], stroke=TRUNK_BORDER)
S.text(ox + 20, oy + 96, "HARDWARE", 11.5, HWC, 700, ls=1.4)
S.text(916, oy + 96, "SERVICES", 11.5, HWC, 700, ls=1.4)
for i, hwi in enumerate(opn["hw"]):
    x, y = ox + 16, oy + 106 + i * 64
    S.rect(x, y, 200, 58, rx=11, fill="#151d29", stroke="#2e3a4c", sw=1.2)
    hw_bar(x, y, 58)
    S.icon(hwi["icon"], x + 12, y + 15, 28)
    S.text(x + 50, y + 17, hwi["label"], 10, "#c08a5c", 700, ls=1.3)
    S.text(x + 50, y + 35, hwi["value"], 15.5, TEXT, 700)
    S.text(x + 50, y + 50, hwi["sub"], 10.5, MUTED, 400)
sw_, sh_ = 190, 50
for i, sv in enumerate(opn["services"]):
    col, row = i % 3, i // 3
    x = 914 + col * (sw_ + 9)
    y = oy + 106 + row * (sh_ + 8)
    S.rect(x, y, sw_, sh_, rx=9, fill=CHIP, stroke=BORDER, sw=1)
    S.icon(sv["icon"], x + 9, y + 12, 26)
    S.text(x + 44, y + 22, sv["name"], 14, TEXT, 600)
    S.text(x + 44, y + 39, sv["note"], 11.5, MUTED, 400)

# WAN cable into the onboard port, uplink cables into the dual NIC (cables first, jacks on top)
S.line([(WANX, fy + fh), (WANX, oy + 30)], C["wan"], SPEED_W["1G"])
for i in (0, 1):
    S.trunk([(port_x(i), by), (port_x(i), oy + oh - 20)], sw=trunk_w("2.5G"))
jack(WANX - 24, oy + 14, 48, 36, C["wan"] + "55", C["wan"])
ticks(WANX, oy + 55, untagged="wan")
S.label(WANX + 6, (fy + fh + oy + 14) / 2 + 4, "1G", C["wan"], 11, anchor="start", mono=True)     # speed tag like the other links
S.text(WANX + 32, oy + 38, opn["wan_ip"], 14, C["wan"], 600, mono=True)
for i in (0, 1):
    jack(port_x(i) - 24, oy + oh - 46, 48, 36, "#2a3443", TRUNK)
    if i == 1:                            # OPNsense is .1 in every VLAN on this trunk
        S.text(port_x(i) + 32, oy + oh - 22, ".1", 14, TRUNK, 600, mono=True)
    ticks(port_x(i), oy + oh - 51, tagged=ALL_VLANS, up=True)
lx = (port_x(0) + port_x(1)) / 2
ly = (oy + oh + by) / 2
S.add(f'<ellipse cx="{lx}" cy="{ly}" rx="46" ry="12" fill="none" stroke="{TRUNK}" stroke-width="1.4" stroke-dasharray="3 3"/>')
S.label(lx + 54, ly + 4, "LACP · dual 2.5G", TRUNK, 11, anchor="start", mono=True)

# ================================================================ switch
swc = INV["switch"]
device_card(bx, by, bw, bh, ["mikrotik-l"], swc, C["99"], fill="#141b25", stroke=TRUNK_BORDER)

PORTS = {}
for i, p in enumerate(swc["ports"]):
    sfp = p["name"].startswith("sfpp")
    w = 60 if sfp else 48
    x = port_x(i) - w / 2
    y = by + 30
    unt = p.get("untagged")
    tagged = p.get("tagged", [])
    if p["to"] in ("free", "rescue"):
        fill, stroke = "#1b222c", (C[unt] if unt and not tagged else TRUNK)
    elif not unt and not tagged:                       # in use, VLANs unknown
        fill, stroke = UNKNOWN + "44", UNKNOWN
    elif unt and not tagged:
        fill, stroke = C[unt] + "55", C[unt]
    else:
        fill, stroke = "#2a3443", TRUNK
    jack(x, y, w, 36, fill, stroke, sfp)
    short = "SFP+" + p["name"][-1] if sfp else p["name"].replace("ether", "")
    S.text(port_x(i), y - 7, short, 11, MUTED, 500, "middle", mono=True)
    ticks(port_x(i), y + 41, unt, tagged)
    S.text(port_x(i), by + bh - 9, p.get("short", p["to"]), 10.5, FAINT if p["to"] in ("free", "rescue") else MUTED, 500, "middle")
    PORTS[p["name"]] = port_x(i)
assert port_x(len(swc["ports"]) - 1) + 40 <= bx + bw, \
    f"switch ports run past the card: widen bw (now {bw}) or reduce PITCH"

# ================================================================ device row
DY = 1234
dev = INV["devices"]
MAD = (40, 400, 86)
KVM = (460, 310, 86)
AP = (790, 310, 160)
ZB = (1120, 360, 86)


def device(key, box):
    x, w, h = box
    d = dev[key]
    col = C[d["vlan"]]
    device_card(x, DY, w, h, d["icons"], d, col, stroke=TRUNK_BORDER if d.get("trunk") else None)
    return x, w, h


device("madcat", MAD)

device("jetkvm", KVM)

x, w, h = device("ap", AP)
S.text(x + 18, DY + 96, "SSIDs", 11, FAINT, 600, ls=1.2)
for i, s in enumerate(INV["ssids"]):
    name = s["redacted"] if (RED["ssid_names"] and not UNREDACTED) else s["name"]
    col = C[s["vlan"]] if "vlan" in s else TRUNK     # PPSK SSIDs may list only `vlans`
    sy = DY + 106 + i * 17
    S.add(f'<circle cx="{x+24}" cy="{sy+5}" r="4" fill="{col}"/>')
    S.text(x + 36, sy + 9, name, 13, TEXT, 500)
    if s.get("vlans"):                    # PPSK: one SSID, several VLANs
        S.text(x + 150, sy + 9, "PPSK", 11, TRUNK, 700, mono=True)
        for j, k in enumerate(s["vlans"]):
            S.add(f'<circle cx="{x + 194 + j*13}" cy="{sy+5}" r="4.5" fill="{C[k]}"/>')
    else:
        S.text(x + 150, sy + 9, vlan_tag(s["vlan"]), 12, col, 500, mono=True)

device("slzb", ZB)

# links switch → devices; width = negotiated speed (read from the switch 2026-11-07)
MAD_10G = MAD[0] + tab_width(dev["madcat"]) + 34
MAD_25G = MAD_10G + 54
S.line([(PORTS["ether3"], SB), (PORTS["ether3"], SB + 46), (MAD_25G, SB + 46), (MAD_25G, DY)], C["10"], SPEED_W["2.5G"])
# cables enter the card bodies right of the folder tabs
KVM_IN = KVM[0] + tab_width(dev["jetkvm"]) + 34
AP_IN = AP[0] + tab_width(dev["ap"]) + 40
ZB_IN = ZB[0] + tab_width(dev["slzb"]) + 40
S.line([(PORTS["ether5"], SB), (PORTS["ether5"], SB + 66), (KVM_IN, SB + 66), (KVM_IN, DY)], C["10"], SPEED_W["100M"])
S.trunk([(PORTS["ether6"], SB), (PORTS["ether6"], SB + 86), (AP_IN, SB + 86), (AP_IN, DY)], sw=trunk_w("2.5G"))
S.line([(PORTS["ether7"], SB), (PORTS["ether7"], SB + 76), (ZB_IN, SB + 76), (ZB_IN, DY)], C["40"], SPEED_W["100M"])
p10 = [(PORTS["sfpp1"], SB + 5), (PORTS["sfpp1"], SB + 20), (MAD_10G, SB + 20), (MAD_10G, DY)]
S.line(p10, BG, SPEED_W["10G"] + 8, cap="butt")                      # knock-out: 10G crosses over the others
S.line([(PORTS["sfpp1"], SB)] + p10[1:], C["10"], SPEED_W["10G"])


def speed_tag(x, y, txt, color, anchor="start"):
    """Small speed label where a cable enters a device."""
    S.label(x, y, txt, color, 11, anchor=anchor, mono=True)


ST = DY - 9
speed_tag(MAD_10G + 8, ST, "10G", C["10"])
speed_tag(MAD_25G + 6, ST, "2.5G", C["10"])
speed_tag(KVM_IN + 5, ST, "100M", C["10"])
speed_tag(AP_IN + 8, ST, "2.5G", TRUNK)
speed_tag(ZB_IN + 5, ST, "100M", C["40"])

# ================================================================ open to the internet (info card, right column, no link)
ix_, iy_, iw_ = 1790, 262, 570
pf = INV["port_forwards"]
ih_ = 84 + len(pf) * 44
S.rect(ix_, iy_, iw_, ih_, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(ix_ + 20, iy_ + 34, "Open to the internet", 19, TEXT, 600)
S.text(ix_ + 20, iy_ + 56, "port forwards on OPNsense · blocklist + CrowdSec drop bad IPs first", 12.5, MUTED, 400)
for i, r in enumerate(pf):
    y = iy_ + 72 + i * 44
    S.rect(ix_ + 14, y, iw_ - 28, 38, rx=8, fill=CHIP, stroke=BORDER, sw=1)
    S.text(ix_ + 26, y + 24, r["port"], 13, TEXT, 600, mono=True)
    S.text(ix_ + 236, y + 17, r["to"], 13.5, TEXT, 600)
    S.text(ix_ + 236, y + 32, r["what"], 11.5, MUTED, 400)
    px = ix_ + iw_ - 24
    for pr in reversed(r["proto"].split("/")):
        px -= S.pill(px, y + 9, pr, PROTO[pr], 11, mono=True, anchor="end", pad=7, h=20) + 6

# ================================================================ legend (left column, under the Networks card)
LG_ROWS = ["trunk", "access", "wan", "kvm", "net", "speed", "public", "internal", "lan", "ticks", "share"]
lgx, lgy, lgw = 40, 660, 500
LR = 27
lgh = 52 + len(LG_ROWS) * LR + 8
S.rect(lgx, lgy, lgw, lgh, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(lgx + 20, lgy + 36, "Legend", 19, TEXT, 600)
SX, TX = lgx + 22, lgx + 162          # symbol column, text column
for i, k in enumerate(LG_ROWS):
    y = lgy + 66 + i * LR
    t = None
    if k == "trunk":
        S.trunk([(SX, y), (SX + 50, y)], sw=trunk_w("2.5G"), r=0); t = "802.1Q trunk (tagged VLANs)"
    elif k == "access":
        for jj, c in enumerate(["10", "20", "40", "99"]):
            S.line([(SX + jj * 13, y), (SX + jj * 13 + 9, y)], C[c], 3.6, r=0, cap="butt")
        t = "access port, colored by VLAN"
    elif k == "wan":
        S.line([(SX, y), (SX + 50, y)], C["wan"], 3, r=0); t = "WAN (Fritzbox network)"
    elif k == "kvm":
        S.line([(SX, y), (SX + 50, y)], MUTED, 2, dash="5 5", r=0, cap="butt"); t = "KVM console (HDMI + USB)"
    elif k == "net":
        S.line([(SX, y), (SX + 50, y)], MUTED, 1.8, dash="2 5", r=0); t = "over the internet (not a cable)"
    elif k == "speed":
        S.text(SX, y + 4.5, "line width = speed", 12.5, MUTED, 400)
        x0 = TX
        for lbl in ("10G", "2.5G", "1G", "100M"):
            S.line([(x0, y), (x0 + 26, y)], C["10"], SPEED_W[lbl], r=0, cap="butt")
            S.text(x0 + 32, y + 4.5, lbl, 12, TEXT, 500, mono=True)
            x0 += 32 + tw(lbl, 12, True) + 20
    elif k == "public":
        S.text(SX, y + 4.5, "app." + SHOWN_DOMAIN, 12, LINK, 500, mono=True); t = "public via Traefik"
    elif k == "internal":
        S.text(SX, y + 4.5, "name.internal", 12, C["10"], 400, mono=True, op=0.78); t = "local DNS, no Traefik"
    elif k == "lan":
        S.pill(SX, y - 9, "LAN", MUTED, 10, mono=True, pad=5); t = "only from LAN / VPN"
    elif k == "ticks":
        for jj, c in enumerate(["10", "20", "40"]):
            S.add(f'<rect x="{SX + jj*7}" y="{y-5 if jj == 0 else y-2}" width="5" height="{8 if jj == 0 else 5}" rx="1" fill="{C[c]}"/>')
        t = "port VLANs (tall = untagged)"
    elif k == "share":
        S.rect(SX, y - 8, 22, 15, rx=3, fill=C["10"] + "16", stroke=C["10"] + "cc", sw=1.2, dash="4 3")
        t = "TrueNAS share, bind-mounted"
    if t:
        S.text(TX, y + 4.5, t, 13, MUTED, 400)

# ================================================================ left column: VLAN table
vx, vy, vw = 40, 150, 500
vh = 70 + len(INV["vlans"]) * 60
S.rect(vx, vy, vw, vh, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(vx + 20, vy + 36, "Networks", 19, TEXT, 600)
for i, v in enumerate(INV["vlans"]):
    y = vy + 56 + i * 60
    S.rect(vx + 14, y, vw - 28, 52, rx=9, fill=CHIP, stroke=v["color"] + "55", sw=1)
    S.add(f'<rect x="{vx+14}" y="{y}" width="6" height="52" rx="3" fill="{v["color"]}"/>')
    S.text(vx + 32, y + 22, v["tag"], 13, v["color"], 600, mono=True)
    S.text(vx + 128, y + 22, v["name"], 15.5, TEXT, 600)
    S.text(vx + vw - 28, y + 22, v["subnet"], 13.5, TEXT, 500, "end", mono=True)
    S.text(vx + 32, y + 42, v["note"], 12, MUTED, 400)
