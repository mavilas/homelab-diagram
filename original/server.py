"""Bottom half of the original lab: the Proxmox host, DMZ, pools and media pipeline; then the files."""
import subprocess

from .top import *  # noqa: F401,F403  (positions and helpers from the top half)


# ================================================================ terra
T = INV["terra"]
tx0, ty0, tw0 = 40, 1468, W - 80
GY = 92           # body starts below the header
ZH = 712          # body height: hardware list | other-VLAN guests | DMZ zone
th0 = GY + ZH + 22
device_card(tx0, ty0, tw0, th0, ["proxmox"], T, C["10"], fill="#0f151e", stroke=TRUNK_BORDER, sw=2)

# ---- column 1: hardware as a vertical list
hwx, HWW = tx0 + 20, 250
hy0 = ty0 + GY
S.text(hwx + 2, hy0 + 12, "HARDWARE", 11.5, HWC, 700, ls=1.4)
TH_, TG_ = 58, 6
for i, hwi in enumerate(T["hw"]):
    x, y = hwx, hy0 + 22 + i * (TH_ + TG_)
    S.rect(x, y, HWW, TH_, rx=11, fill="#151d29", stroke="#2e3a4c", sw=1.2)
    hw_bar(x, y, TH_)
    S.icon(hwi["icon"], x + 12, y + 15, 28)
    S.text(x + 50, y + 17, hwi["label"], 10, "#c08a5c", 700, ls=1.3)
    vs = min(15.5, 15.5 * (HWW - 62) / measure(hwi["value"], 15.5, 700))   # shrink long part names to fit
    S.text(x + 50, y + 35, hwi["value"], round(vs, 2), TEXT, 700)
    ss = min(10.5, 10.5 * (HWW - 60) / max(tw(hwi["sub"], 10.5), 1))       # same for the sub line
    S.text(x + 50, y + 50, hwi["sub"], round(ss, 2), MUTED, 400)
assert hy0 + 22 + len(T["hw"]) * (TH_ + TG_) <= hy0 + ZH + 6, "hardware list too tall"

S.trunk([(PORTS["sfpp2"], SB), (PORTS["sfpp2"], ty0)], sw=trunk_w("10G"))
speed_tag(PORTS["sfpp2"] + 10, ty0 - 9, "10G", TRUNK)

kx = KVM[0] + KVM[1] / 2
S.line([(kx, DY + KVM[2]), (kx, ty0)], MUTED, 2, dash="5 5", cap="butt")
S.label(kx + 10, (DY + KVM[2] + ty0) / 2 + 5, "HDMI + USB console", MUTED, 12, anchor="start")

# ---- other-VLAN guests (left column inside terra)
og = T["other_guests"]
gx, gy, gw = hwx + HWW + 20, ty0 + GY, 480


def guest_card(g, x, y, w, h):
    col = C[g["vlan"]]
    S.rect(x, y, w, h, rx=12, fill=PANEL, stroke=col + "99", sw=1.5)
    S.icon(g["icons"][0], x + 16, y + 14, 34)
    if g.get("badge"):
        S.add(f'<circle cx="{x+45}" cy="{y+44}" r="11" fill="{PANEL}"/>')
        S.icon(g["badge"], x + 35, y + 34, 20)
    S.text(x + 60, y + 32, g["name"], 17, TEXT, 600)
    S.pill(x + w - 14, y + 16, vlan_tag(g["vlan"]), col, 10.5, mono=True, h=19, pad=6, anchor="end")
    addr(x + 60, y + 51, g["ip"], g, col)
    S.text(x + 60, y + 69, g["note"], 12.5, MUTED, 400)


def disk(kind, x, y):
    if kind == "hdd":
        S.rect(x, y, 30, 40, rx=4, fill=DISK, stroke=DISK_EDGE, sw=1.2)
        S.add(f'<circle cx="{x+15}" cy="{y+16}" r="9" fill="none" stroke="{C["10"]}" stroke-width="1.6"/>'
              f'<circle cx="{x+15}" cy="{y+16}" r="2" fill="{C["10"]}"/>')
        S.rect(x + 8, y + 31, 14, 3, rx=1, fill=DISK_EDGE, stroke="none", sw=0)
        return 30
    if kind == "ssd":
        S.rect(x, y + 6, 44, 28, rx=3, fill=DISK, stroke=DISK_EDGE, sw=1.2)
        S.rect(x + 6, y + 12, 20, 16, rx=2, fill=C["10"] + "55", stroke="none", sw=0)
        S.rect(x + 30, y + 12, 8, 16, rx=1, fill=DISK_EDGE, stroke="none", sw=0)
        return 44
    S.rect(x, y + 10, 96, 20, rx=2, fill=DISK, stroke=DISK_EDGE, sw=1.2)        # nvme
    for k in range(3):
        S.rect(x + 8 + k * 22, y + 14, 16, 12, rx=1, fill=C["10"] + "55", stroke="none", sw=0)
    S.rect(x + 88, y + 15, 4, 10, rx=1, fill=BG, stroke="none", sw=0)
    return 96


def pool_box(p, x, y, w, h):
    y0 = y
    S.rect(x, y, w, h, rx=10, fill=CHIP, stroke=BORDER, sw=1)
    S.text(x + 14, y + 24, p["name"], 15.5, TEXT, 700)
    S.text(x + 14 + tw(p["name"], 15.5) + 12, y + 24, p["layout"], 12.5, MUTED, 400)
    S.text(x + w - 14, y + 24, p["used"], 12, MUTED, 400, "end")
    bw_ = w - 28
    S.rect(x + 14, y + 34, bw_, 8, rx=4, fill="#253042", stroke="none", sw=0)
    barc = "#f0883e" if p["pct"] >= p.get("warn", 85) else C["10"]     # nearly full → orange
    S.rect(x + 14, y + 34, max(bw_ * p["pct"] / 100, 8), 8, rx=4, fill=barc, stroke="none", sw=0)
    gx0 = x + 14
    for grp in p["groups"]:
        disks = grp["count"] * ({"hdd": 30, "ssd": 44}.get(grp["kind"], 96) + 7)
        texts = max(measure(grp["label"], 12.5, 600), measure(grp["sub"], 11.5, 400),
                    measure(grp.get("sub2", ""), 11.5, 400))                      # real font widths
        if grp["kind"] == "nvme":                        # labels sit right of the stick
            disks, texts = disks, disks + 8 + texts
        # disks must stay inside the padding; labels may run into it, up to the box edge
        if gx0 > x + 14 and (gx0 + disks > x + w - 14 or gx0 + texts > x + w - 4):   # next row
            gx0, y = x + 14, y + 110
            assert y + 156 <= y0 + h, f"pool {p['name']}: disk groups wrap to a 2nd row, give the pool box {y + 156 - y0} px"
        dx = gx0
        for _ in range(grp["count"]):
            dx += disk(grp["kind"], dx, y + 54) + 7
        gw_ = dx - 7 - gx0
        if grp["kind"] == "nvme":          # label to the right of the stick
            S.text(dx + 8, y + 64, grp["label"], 12.5, TEXT, 500)
            S.text(dx + 8, y + 80, grp["sub"], 11.5, MUTED, 400)
            if grp.get("sub2"):
                S.text(dx + 8, y + 95, grp["sub2"], 11.5, MUTED, 400)
        else:
            S.line([(gx0, y + 102), (gx0, y + 106), (gx0 + gw_, y + 106), (gx0 + gw_, y + 102)], DISK_EDGE, 1.2, r=0, cap="butt")
            S.text(gx0, y + 122, grp["label"], 12.5, TEXT, 500)
            S.text(gx0, y + 137, grp["sub"], 11.5, MUTED, 400)
            if grp.get("sub2"):
                S.text(gx0, y + 152, grp["sub2"], 11.5, MUTED, 400)
            gw_ = max(gw_, tw(grp["label"], 12.5), tw(grp["sub"], 11.5), tw(grp.get("sub2", ""), 11.5))
        gx0 += gw_ + 30


tn = og["truenas"]
guest_card(tn, gx, gy, gw, 382)
pool_box(tn["pools"][0], gx + 14, gy + 84, gw - 28, 158)
pool_box(tn["pools"][1], gx + 14, gy + 250, gw - 28, 102)
S.text(gx + 18, gy + 370, tn["footer"], 12, MUTED, 400)

ha = og["haos"]
hy = gy + 396
guest_card(ha, gx, hy, gw, 120)
ax = gx + 18
for ic in ha["addons"]:
    S.icon(ic, ax, hy + 80, 26)
    ax += 34
S.text(ax + 8, hy + 98, ha["addons_text"], 12, MUTED, 400)

guest_card(og["unifi"], gx, hy + 134, gw, 84)
guest_card(og["bliss"], gx, hy + 232, gw, 84)

# ---- DMZ zone
zx = gx + gw + 20
zy = gy
zw = tx0 + tw0 - 20 - zx
S.rect(zx, zy, zw, ZH, rx=14, fill=C["20"] + "0d", stroke=C["20"] + "88", sw=1.5)
S.pill(zx + zw - 14, zy + 16, vlan_tag("20"), C["20"], 10.5, mono=True, h=19, pad=6, anchor="end")   # same as the VM/CT card pills
S.text(zx + 18, zy + 31, "one unprivileged LXC per service · web apps behind Traefik (CT 149)",
       12.5, MUTED, 400)

groups = {g["name"]: g for g in T["dmz_groups"]}
cgap = 14
NCOL = 4
cw = (zw - 32 - cgap * (NCOL - 1)) / NCOL
CH, CG = 64, 7
GT = "#c08a5c"


def col_x(i):
    return zx + 16 + i * (cw + cgap)


def docker_badge(x, y):
    """Small Docker whale on a corner = this CT runs its apps as Docker containers."""
    S.add(f'<circle cx="{x}" cy="{y}" r="12" fill="{PANEL}" stroke="#2f6fb0" stroke-width="1.2"/>')
    S.icon("docker", x - 8.5, y - 8.5, 17)


ZONE_VLAN = "20"


def chip_ids(g, x, y, w, h):
    """Right-hand column of a chip: '<kind> <id>', IP (or .id), optional node; VLAN bar if not in the zone VLAN.
    Optional guest fields: kind (default CT), node (cluster member it runs on), vlan."""
    node = f" · {g['node']}" if g.get("node") else ""          # on the id line, clear of the hostname
    S.text(x + w - 12, y + 21, f"{g.get('kind', 'CT')} {g['id']}{node}", 12, FAINT, 500, "end", mono=True)
    S.text(x + w - 12, y + 37, g.get("ip", f".{g['id']}"), 11, FAINT, 500, "end", mono=True)
    if g.get("vlan", ZONE_VLAN) != ZONE_VLAN:
        S.add(f'<rect x="{x}" y="{y+8}" width="4" height="{h-16}" rx="2" fill="{C[g["vlan"]]}"/>')


def chip_apps(g, x, y, w):
    """One CT running several apps: header like a normal chip, then one row per app (icon, name, hostname)."""
    h = 46 + len(g["apps"]) * 21 + 8
    S.rect(x, y, w, h, rx=9, fill=CHIP, stroke=BORDER, sw=1)
    S.text(x + 14, y + 22, g["name"], 14.5, TEXT, 600)
    S.text(x + 14, y + 38, g.get("note", ""), 11.5, MUTED, 400)
    chip_ids(g, x, y, w, h)
    for k, a in enumerate(g["apps"]):
        ry = y + 50 + k * 21
        S.icon(a["icon"], x + 14, ry, 17)
        S.text(x + 38, ry + 13, a["name"], 12.5, TEXT, 600)
        if a.get("host"):
            S.text(x + 140, ry + 13, fqdn(a["host"]), 11, LINK, 500, mono=True)
        else:
            S.text(x + 140, ry + 13, a.get("note", ""), 11.5, MUTED, 400)
    if g.get("docker"):
        docker_badge(x + 2, y + 2)
    return h


def chip(g, x, y, w):
    if g.get("apps"):
        return chip_apps(g, x, y, w)
    S.rect(x, y, w, CH, rx=9, fill=CHIP, stroke=BORDER, sw=1)
    icons = g["icons"]
    if len(icons) == 4:                      # 2×2 grid
        for k, ic in enumerate(icons):
            S.icon(ic, x + 12 + (k % 2) * 23, y + 13 + (k // 2) * 21, 19)
        nx = x + 12 + 46 + 10
    else:
        isz = 32 if len(icons) == 1 else 26
        ix = x + 10
        for ic in icons:
            S.icon(ic, ix, y + (CH - isz) / 2, isz)
            ix += isz + 4
        nx = ix + 6
    S.text(nx, y + 21, g["name"], 14.5, TEXT, 600)
    S.text(nx, y + 37, g.get("note", ""), 11.5, MUTED, 400)
    name, ncol = hostname(g)
    if name:
        S.text(nx, y + 54, name, 11.5, ncol or MUTED, 500, mono=True)
        if g.get("exposure") == "local":
            S.pill(nx + tw(name, 11.5, True) + 8, y + 44, "LAN", MUTED, 9.5, mono=True, pad=4, h=14)
    chip_ids(g, x, y, w, CH)
    if g.get("docker"):
        docker_badge(x + 2, y + 2)
    return CH


def column(i, names):
    x, y = col_x(i), zy + 56
    for gname in names:
        S.text(x + 2, y + 12, gname.upper(), 11.5, GT, 700, ls=1.4)
        y += 22
        for g in groups[gname]["guests"]:
            y += chip(g, x, y, cw) + CG
        y += 14
    assert y <= zy + ZH + 6, f"DMZ column {i} too tall"


column(0, ["Edge & security", "Monitoring"])
column(1, ["Media & photos"])
column(2, ["Productivity", "Gaming"])
column(3, ["Dev", "Chat"])

# ================================================================ media pipeline (explainer panel, right column above terra)
mp = T["media_pipeline"]
N = mp["nodes"]
PX, PY, PW = 1790, iy_ + ih_ + 20, 570
CARD_BG = PANEL
G_ = 42
NW = (PW - 28 - 2 * G_) / 3
NH = 68
STACK_H = 3 * 46 + 2 * 6
RA = PY + 98                       # top of the *arr stack (room for title + its label)
RS = RA + (STACK_H - NH) / 2       # Seerr / Prowlarr (centered on the stack)
RB = RA + STACK_H + 52             # Jellyfin / qBittorrent
RC = RB + NH + 40                  # the two TrueNAS shares
SH_ = 64
SW_ = (PW - 28 - G_) / 2
PH = RC + SH_ + 16 - PY
S.rect(PX, PY, PW, PH, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(PX + 20, PY + 32, "Media pipeline", 17, TEXT, 600)
S.text(PX + 20, PY + 52, "how a request ends up in Jellyfin", 12.5, MUTED, 400)
assert PY + PH <= ty0 - TAB - 16, f"pipeline panel overlaps terra: {PY + PH} > {ty0 - TAB - 16}"


def node_x(c):
    return PX + 14 + c * (NW + G_)


def node(n, c, y):
    x = node_x(c)
    S.rect(x, y, NW, NH, rx=9, fill=CHIP, stroke=BORDER, sw=1)
    S.icon(n["icon"], x + 8, y + 9, 22)
    S.text(x + 35, y + 26, n["name"], 12.5, TEXT, 600)
    S.text(x + NW - 10, y + 26, f"CT {n['ct']}", 10.5, FAINT, 500, "end", mono=True)
    S.text(x + NW - 10, y + 46, n["ip"], 10.5, FAINT, 500, "end", mono=True)
    S.text(x + 10, y + 46, n["sub"], 11, MUTED, 400)
    S.text(x + 10, y + 62, fqdn(n["host"]), 10, LINK, 500, mono=True)


def arr_node(a, x, y):
    S.rect(x, y, NW, 46, rx=8, fill=CHIP, stroke=BORDER, sw=1)
    S.icon(a["icon"], x + 10, y + 7, 20)
    S.text(x + 36, y + 22, a["name"], 13.5, TEXT, 600)
    S.text(x + NW - 10, y + 22, a["ip"], 12, FAINT, 500, "end", mono=True)
    S.text(x + 10, y + 38, fqdn(a["host"]), 10, LINK, 500, mono=True)


def share(sh, x, y):
    """A TrueNAS SMB share, mounted on terra and bind-mounted into the containers."""
    S.rect(x, y, SW_, SH_, rx=9, fill=C["10"] + "16", stroke=C["10"] + "cc", sw=1.3, dash="5 4")
    S.icon("truenas", x + 10, y + 10, 22)
    S.text(x + 40, y + 26, sh["name"], 13.5, TEXT, 600)
    S.text(x + SW_ - 10, y + 26, "TrueNAS SMB", 10.5, C["10"], 600, "end", mono=True)
    S.text(x + 10, y + 44, sh["pool"], 11, MUTED, 400)
    S.text(x + 10, y + 58, "bind mount: SMB ↔ terra ↔ CT", 10, C["10"], 500, mono=True)


node(N["seerr"], 0, RS)
node(N["prowlarr"], 2, RS)
S.rect(node_x(1) - 6, RA - 6, NW + 12, STACK_H + 12, rx=12, fill="none", stroke="#3a475a", sw=1.2, dash="3 3")
lx0 = node_x(1) + 2                                   # group label: Docker whale + "CT 154"
S.rect(lx0, RA - 17, 58, 22, rx=5, fill=CARD_BG, stroke=CARD_BG, sw=0)
S.text(lx0 + 6, RA - 1, "CT 154", 11.5, "#c3cdd9", 600, mono=True)
for k, a in enumerate(mp["arrs"]):
    arr_node(a, node_x(1), RA + k * 52)
node(N["jellyfin"], 0, RB)
node(N["qbit"], 2, RB)
mx, tx_ = PX + 14, PX + 14 + SW_ + G_
share(mp["shares"]["media"], mx, RC)
share(mp["shares"]["torrents"], tx_, RC)

midS = RS + NH / 2
S.arrow([(node_x(0) + NW + 4, midS), (node_x(1) - 10, midS)])
S.label(node_x(0) + NW + G_ / 2 - 3, midS - 8, "request", MUTED, 11, bg=CARD_BG)
S.arrow([(node_x(2) - 4, midS), (node_x(1) + NW + 10, midS)])
S.label(node_x(1) + NW + G_ / 2 + 3, midS - 8, "indexers", MUTED, 11, bg=CARD_BG)
qx = node_x(2) + NW / 2
yr = RA + 2 * 52 + 23                       # Radarr row
S.arrow([(node_x(1) + NW + 8, yr), (qx, yr), (qx, RB - 5)])
S.label((node_x(1) + NW + qx) / 2 + 4, yr - 8, "torrent", MUTED, 11, bg=CARD_BG)
# the *arr apps pick finished files up from Torrents and copy them (renamed, sorted) into Media
ax1, ax2 = node_x(1) + 24, node_x(1) + NW - 24
S.arrow([(ax1, RA + STACK_H + 7), (ax1, RC - 5)])
S.text(ax1 + 8, RB + 30, "copy +", 11, MUTED, 500)
S.text(ax1 + 8, RB + 44, "rename", 11, MUTED, 500)
S.arrow([(ax2, RC - 2), (ax2, RA + STACK_H + 10)])
S.text(ax2 + 8, RB + 30, "pick up", 11, MUTED, 500)
S.text(ax2 + 8, RB + 44, "when done", 11, MUTED, 500)
jx = node_x(0) + NW / 2
S.arrow([(jx, RB - 2), (jx, RS + NH + 5)], dash="4 4")
S.text(jx + 10, (RS + NH + RB) / 2 + 4, "available", 11, MUTED, 500)
S.arrow([(qx, RB + NH + 2), (qx, RC - 5)])
S.text(qx + 10, (RB + NH + RC) / 2 + 4, "download", 11, MUTED, 500)
S.arrow([(jx, RC - 2), (jx, RB + NH + 5)])
S.text(jx + 10, (RB + NH + RC) / 2 + 4, "library", 11, MUTED, 500)
# ---------------------------------------------------------------- canvas height
# the canvas grows with the content: lowest panel + margin
H = int(ty0 + th0 + 32)


def write():
    OUT.mkdir(exist_ok=True)
    name = "homelab-unredacted" if UNREDACTED else "homelab"
    svg_path = OUT / f"{name}.svg"
    svg_path.write_text(S.finish(H))
    png_path = OUT / f"{name}.png"
    subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
    print(svg_path, png_path)
