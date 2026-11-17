"""Deterministic layout of a Spec onto a Canvas.

Groups fill rows of `spec.columns` slots in spec order (a group may span
several slots); nodes fill a grid inside their group. Ungrouped nodes form a
borderless band above the groups. Links are orthogonal cables drawn under
the cards: same-row nodes connect side to side, otherwise the cable leaves
the upper node's bottom and turns in the gap just above the lower node. Put
linked nodes in adjacent rows to keep cables clear of other cards.
Text that would not fit its card raises LayoutError instead of overflowing.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .canvas import Canvas
from .components import TAB, card, device_card, zone
from .spec import Group, Link, Node, Spec
from .text import measure

MARGIN = 40
CONTENT_TOP = 130
GROUP_GAP = 24
NODE_GAP_X = 16
NODE_GAP_Y = 18
GROUP_PAD = 18
SERVICE_H = 64
SERVICE_ICON = 30
ITEM_PITCH = 64
ITEM_H = 56
DEFAULT_LINK_W = 2.4
DASH = {"solid": None, "dashed": "10 7", "dotted": "2 6"}
LEGEND_W = 520
ANCHOR_SPREAD = 14
CHANNEL_STEP = 7


class LayoutError(ValueError):
    """The spec is valid but does not fit; the message says what to change."""


@dataclass(frozen=True)
class Box:
    x: float
    y: float        # body top (below the folder tab for devices)
    w: float
    h: float
    top: float      # top of the slot, including the tab
    group: str = ""
    zone_top: float = 0.0   # top of the enclosing group (its border), for routing in the gap above it

    @property
    def bottom(self) -> float:
        return self.y + self.h


def group_header(g: Group) -> float:
    if g.label:
        return 70 if g.note else 54
    return 44 if (g.tag or g.note) else GROUP_PAD


def node_height(n: Node) -> float:
    """Body height; devices also need TAB above the body."""
    if n.kind == "service":
        return SERVICE_H
    return item_top(n) + len(n.items) * ITEM_PITCH + (8 if n.items else 0)


def item_top(n: Node) -> float:
    return 104 if n.note else (86 if n.os else 76)


def slot_height(n: Node) -> float:
    return node_height(n) + (TAB if n.kind == "device" else 0)


def _fit(text: str | None, size: float, weight: int, room: float, what: str, family: str) -> None:
    if text and measure(text, size, weight, family) > room:
        raise LayoutError(f"{what}: {text!r} does not fit in {room:.0f} px; shorten it, lower the "
                          "group columns, raise the group span or widen the canvas")


def _check_text(n: Node, w: float, family: str) -> None:
    if n.kind == "service":
        room = w - (18 + (SERVICE_ICON + 10 if n.icon else 0)) - 12
        _fit(n.label, 16, 600, room, f"node {n.id} label", family)
        _fit(n.note, 13, 400, room, f"node {n.id} note", family)
        return
    room = w - (14 + (58 if n.icon else 0) + 8) - 14
    for text, size, weight, what in ((n.model, 14, 600, "model"), (n.address, 12, 600, "address"),
                                     (n.os, 12, 400, "os"), (n.note, 12, 400, "note")):
        _fit(text, size, weight, room, f"node {n.id} {what}", family)
    item_room = w - 28 - (18 + 26 + 10) - 12
    for i, it in enumerate(n.items):
        _fit(it.label, 15, 600, item_room, f"node {n.id} items[{i}] label", family)
        _fit(it.note, 13, 400, item_room, f"node {n.id} items[{i}] note", family)


class Layout:
    """Positions for every group and node of one spec at one canvas width."""

    def __init__(self, spec: Spec, canvas: Canvas):
        self.spec, self.c = spec, canvas
        self.boxes: dict[str, Box] = {}
        self.zones: list[tuple[Group, float, float, float, float]] = []
        self.bottom = CONTENT_TOP

    def compute(self) -> "Layout":
        spec = self.spec
        members: dict[str | None, list[Node]] = defaultdict(list)
        for n in spec.nodes:
            members[n.group].append(n)
        inner = spec.width - 2 * MARGIN
        y = CONTENT_TOP
        if members[None]:
            loose = Group(id="", columns=min(4, len(members[None])), span=spec.columns)
            y = self._place_group(loose, members[None], MARGIN, y, inner, boxed=False) + GROUP_GAP
        slot_w = (inner - GROUP_GAP * (spec.columns - 1)) / spec.columns
        row: list[Group] = []
        for g in spec.groups:
            if sum(x.span for x in row) + g.span > spec.columns:
                y = self._place_row(row, members, y, slot_w) + GROUP_GAP
                row = []
            row.append(g)
        if row:
            y = self._place_row(row, members, y, slot_w) + GROUP_GAP
        self.bottom = y - GROUP_GAP
        return self

    def _place_row(self, row, members, y, slot_w) -> float:
        x, bottom = MARGIN, y
        for g in row:
            w = slot_w * g.span + GROUP_GAP * (g.span - 1)
            bottom = max(bottom, self._place_group(g, members[g.id], x, y, w, boxed=True))
            x += w + GROUP_GAP
        for i, (g, zx, zy, zw, _) in enumerate(self.zones):     # equal heights within a row
            if zy == y:
                self.zones[i] = (g, zx, zy, zw, bottom - y)
        return bottom

    def _place_group(self, g: Group, nodes: list[Node], x, y, w, boxed: bool) -> float:
        pad = GROUP_PAD if boxed else 0
        cols = g.columns
        nw = (w - 2 * pad - NODE_GAP_X * (cols - 1)) / cols
        cy = y + (group_header(g) if boxed else 0)
        for r in range(0, len(nodes), cols):
            chunk = nodes[r:r + cols]
            for k, n in enumerate(chunk):
                _check_text(n, nw, self.c.theme.sans)
                if n.kind == "device":
                    _fit(f"{n.label} · {n.type}", 20, 700, nw - 30, f"node {n.id} tab", self.c.theme.sans)
                nx = x + pad + k * (nw + NODE_GAP_X)
                body_y = cy + (TAB if n.kind == "device" else 0)
                self.boxes[n.id] = Box(nx, body_y, nw, node_height(n), cy, g.id, y)
            cy += max(slot_height(n) for n in chunk) + NODE_GAP_Y
        end = cy - (NODE_GAP_Y if nodes else 0) + pad
        if boxed:
            self.zones.append((g, x, y, w, end - y))
        return end


# ---------------------------------------------------------------- drawing
def _stroke_width(theme, speed, width) -> float:
    if speed:
        return theme.speed_width[speed]
    return width if width is not None else DEFAULT_LINK_W


def _route(a: Box, b: Box, sa: float, sb: float, slot: int):
    """Orthogonal points from a to b; sa/sb shift the anchors so parallel cables do not merge."""
    lo, hi = max(a.y, b.y), min(a.bottom, b.bottom)
    if hi - lo > 20:                                    # side by side in the same row
        left, right = (a, b) if a.x < b.x else (b, a)
        ym = (lo + hi) / 2 + (sa if left is a else sb)
        return [(left.x + left.w, ym), (right.x, ym)]
    up, down, su, sd = (a, b, sa, sb) if a.top < b.top else (b, a, sb, sa)
    ux, dx = up.x + up.w / 2 + su, down.x + down.w / 2 + sd
    if abs(ux - dx) < 1:
        return [(ux, up.bottom), (ux, down.y)]
    if up.group != down.group and down.zone_top > up.bottom:   # turn in the gap between the groups
        cy = down.zone_top - GROUP_GAP / 2 + (slot - 1) * CHANNEL_STEP - CHANNEL_STEP
        cy = min(max(cy, up.bottom + 4), down.zone_top - 4)
    else:                                                       # turn just above the node, inside its group
        cy = max(up.bottom + 8, down.top - 12 - (slot - 1) * CHANNEL_STEP)
    return [(ux, up.bottom), (ux, cy), (dx, cy), (dx, down.y)]


def _spread(links: tuple[Link, ...]) -> list[tuple[float, float]]:
    """Per link, the anchor offsets at its source and target."""
    count: dict[str, int] = defaultdict(int)
    for ln in links:
        count[ln.source] += 1
        count[ln.target] += 1
    seen: dict[str, int] = defaultdict(int)
    out = []
    for ln in links:
        offs = []
        for end in (ln.source, ln.target):
            k, n = seen[end], count[end]
            offs.append((k - (n - 1) / 2) * ANCHOR_SPREAD)
            seen[end] += 1
        out.append((offs[0], offs[1]))
    return out


def draw(spec: Spec, c: Canvas) -> str:
    """Draw spec on a fresh canvas and return the SVG document text."""
    t = c.theme
    lay = Layout(spec, c).compute()
    c.begin()
    c.text(MARGIN, 70, spec.title, 40, t.text, 700)
    if spec.subtitle:
        c.text(spec.width - MARGIN, 70, spec.subtitle, 16, t.muted, 400, "end")
    for g, x, y, w, h in lay.zones:
        zone(c, x, y, w, h, t.color(g.color) or t.border, g.label, g.tag, g.note)

    channels: dict[float, int] = defaultdict(int)
    labels = []
    for ln, (sa, sb) in zip(spec.links, _spread(spec.links)):
        a, b = lay.boxes[ln.source], lay.boxes[ln.target]
        lower = b if b.top > a.top else a
        key = lower.zone_top if a.group != b.group else lower.top
        channels[key] += 1
        pts = _route(a, b, sa, sb, channels[key])
        color = t.color(ln.color) or t.link
        c.line(pts, color, _stroke_width(t, ln.speed, ln.width), dash=DASH[ln.style], r=12)
        if ln.label:
            seg = max(zip(pts, pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
            labels.append(((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2 + 5, ln.label, color))

    nodes = {n.id: n for n in spec.nodes}
    groups = {g.id: g for g in spec.groups}
    for nid, box in lay.boxes.items():
        n = nodes[nid]
        color = t.color(n.color) or t.color(groups[n.group].color if n.group else None) or t.link
        if n.kind == "service":
            card(c, box.x, box.y, box.w, box.h, color, n.label, [n.icon] if n.icon else None, n.note,
                 isz=SERVICE_ICON, tsize=16)
            continue
        g = {"name": n.label, "type": n.type, "model": n.model, "ip": n.address, "os": n.os, "config": n.note}
        device_card(c, box.x, box.y, box.w, box.h, [n.icon] if n.icon else [], g, color)
        for i, it in enumerate(n.items):
            card(c, box.x + 14, box.y + item_top(n) + i * ITEM_PITCH, box.w - 28, ITEM_H, color, it.label,
                 [it.icon] if it.icon else None, it.note, isz=26, tsize=15)
    for x, y, s, color in labels:
        c.label(x, y, s, color, 12, mono=True)

    bottom = lay.bottom
    if spec.legend:
        top = bottom + GROUP_GAP
        h = 70 + len(spec.legend) * 36
        card(c, MARGIN, top, LEGEND_W, h, None, "Legend")
        for i, e in enumerate(spec.legend):
            yy = top + 76 + i * 36
            c.line([(MARGIN + 24, yy), (MARGIN + 124, yy)], t.color(e.color) or t.link,
                   _stroke_width(t, e.speed, e.width), dash=DASH[e.style])
            c.text(MARGIN + 144, yy + 5, e.label, 14, t.muted)
        bottom = top + h
    if spec.footer:
        bottom += 36
        c.text(MARGIN, bottom, spec.footer, 13, t.faint)
    return c.finish(int(bottom + MARGIN))


def needed_icons(spec: Spec) -> list[str]:
    names = [n.icon for n in spec.nodes if n.icon] + [it.icon for n in spec.nodes for it in n.items if it.icon]
    return sorted(set(names))


__all__ = ["Box", "Layout", "LayoutError", "draw", "needed_icons"]
