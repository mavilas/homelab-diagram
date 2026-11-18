"""Declarative diagram spec (YAML or JSON) and its validation.

The spec is untrusted input: unknown keys, unknown references, bad colors,
bad icon names and out-of-range sizes are rejected with a message that names
the offending path. See docs/spec.md for the format.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .icons import NAME_RE as ICON_RE
from .theme import THEMES

SPEC_VERSION = 1
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_TEXT = 200
MAX_NODES = 300
MAX_LINKS = 600
WIDTH_RANGE = (800, 6000)
COLUMNS_RANGE = (1, 8)
LINK_STYLES = ("solid", "dashed", "dotted")
NODE_KINDS = ("device", "service")
MAX_ITEMS = 12


class SpecError(ValueError):
    """The spec is invalid; the message names the path, e.g. nodes[3].group."""


@dataclass(frozen=True)
class Item:
    label: str
    note: str | None = None
    icon: str | None = None


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    kind: str = "service"
    group: str | None = None
    type: str | None = None
    model: str | None = None
    address: str | None = None
    os: str | None = None
    note: str | None = None
    icon: str | None = None
    color: str | None = None
    items: tuple[Item, ...] = ()


@dataclass(frozen=True)
class Group:
    id: str
    label: str | None = None
    note: str | None = None
    tag: str | None = None
    color: str | None = None
    columns: int = 1
    span: int = 1


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    style: str = "solid"
    color: str | None = None
    speed: str | None = None
    width: float | None = None
    label: str | None = None


@dataclass(frozen=True)
class LegendEntry:
    label: str
    style: str = "solid"
    color: str | None = None
    speed: str | None = None
    width: float | None = None


@dataclass(frozen=True)
class Spec:
    title: str
    version: int = SPEC_VERSION
    subtitle: str | None = None
    footer: str | None = None
    theme: str = "dark"
    width: int = 2400
    columns: int = 2
    groups: tuple[Group, ...] = ()
    nodes: tuple[Node, ...] = ()
    links: tuple[Link, ...] = ()
    legend: tuple[LegendEntry, ...] = ()


# ---------------------------------------------------------------- field checks
def _keys(obj: Any, path: str, allowed: set[str], required: set[str]) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise SpecError(f"{path}: expected a mapping")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise SpecError(f"{path}: unknown key(s) {', '.join(map(str, unknown))}")
    missing = sorted(required - set(obj))
    if missing:
        raise SpecError(f"{path}: missing key(s) {', '.join(missing)}")
    return obj


def _text(v: Any, path: str, optional: bool = True) -> str | None:
    if v is None and optional:
        return None
    if not isinstance(v, str) or not v.strip():
        raise SpecError(f"{path}: expected a non-empty string")
    if len(v) > MAX_TEXT or any(ord(ch) < 32 for ch in v):
        raise SpecError(f"{path}: at most {MAX_TEXT} characters, no control characters")
    return v


def _int(v: Any, path: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise SpecError(f"{path}: expected an integer from {lo} to {hi}")
    return v


def _ident(v: Any, path: str) -> str:
    if not isinstance(v, str) or not ID_RE.match(v):
        raise SpecError(f"{path}: expected an id (letters, digits, '_', '.', '-'; at most 64)")
    return v


def _icon(v: Any, path: str) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str) or not ICON_RE.match(v):
        raise SpecError(f"{path}: expected an icon name (lowercase letters, digits, '.', '-', '_')")
    return v


def _color(v: Any, path: str, accents: Mapping[str, str]) -> str | None:
    if v is None:
        return None
    if isinstance(v, str) and (v in accents or HEX_RE.match(v)):
        return v
    raise SpecError(f"{path}: expected '#rrggbb' or one of {', '.join(sorted(accents))}")


def _choice(v: Any, path: str, options: tuple[str, ...] | Mapping, default: str) -> str:
    if v is None:
        return default
    if v not in options:
        raise SpecError(f"{path}: expected one of {', '.join(options)}")
    return v


def _stroke(raw: Mapping, path: str, speeds: Mapping[str, float]) -> tuple[str | None, float | None]:
    speed = raw.get("speed")
    if speed is not None and speed not in speeds:
        raise SpecError(f"{path}.speed: expected one of {', '.join(speeds)}")
    width = raw.get("width")
    if width is not None and (isinstance(width, bool) or not isinstance(width, (int, float)) or not 0.5 <= width <= 20):
        raise SpecError(f"{path}.width: expected a number from 0.5 to 20")
    if speed is not None and width is not None:
        raise SpecError(f"{path}: give speed or width, not both")
    return speed, (float(width) if width is not None else None)


def _list(v: Any, path: str, limit: int) -> list:
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > limit:
        raise SpecError(f"{path}: expected a list of at most {limit} entries")
    return v


# ---------------------------------------------------------------- parsing
def parse_spec(raw: Any) -> Spec:
    """Validate a decoded spec document and return the typed Spec."""
    top = _keys(raw, "spec", {"version", "title", "subtitle", "footer", "theme", "width", "columns",
                              "groups", "nodes", "links", "legend"}, {"version", "title", "nodes"})
    if top["version"] != SPEC_VERSION:
        raise SpecError(f"spec.version: only version {SPEC_VERSION} is supported")
    theme_name = _choice(top.get("theme"), "spec.theme", tuple(THEMES), "dark")
    theme = THEMES[theme_name]
    accents, speeds = theme.accents, theme.speed_width
    columns = _int(top.get("columns", 2), "spec.columns", *COLUMNS_RANGE)

    groups: list[Group] = []
    for i, g in enumerate(_list(top.get("groups"), "spec.groups", MAX_NODES)):
        p = f"groups[{i}]"
        g = _keys(g, p, {"id", "label", "note", "tag", "color", "columns", "span"}, {"id"})
        groups.append(Group(_ident(g["id"], f"{p}.id"), _text(g.get("label"), f"{p}.label"),
                            _text(g.get("note"), f"{p}.note"), _text(g.get("tag"), f"{p}.tag"),
                            _color(g.get("color"), f"{p}.color", accents),
                            _int(g.get("columns", 1), f"{p}.columns", *COLUMNS_RANGE),
                            _int(g.get("span", 1), f"{p}.span", 1, columns)))
    group_ids = _unique([g.id for g in groups], "groups")

    nodes: list[Node] = []
    raw_nodes = _list(top["nodes"], "spec.nodes", MAX_NODES)
    if not raw_nodes:
        raise SpecError("spec.nodes: at least one node is required")
    for i, n in enumerate(raw_nodes):
        p = f"nodes[{i}]"
        n = _keys(n, p, {"id", "label", "kind", "group", "type", "model", "address", "os", "note", "icon",
                         "color", "items"}, {"id", "label"})
        kind = _choice(n.get("kind"), f"{p}.kind", NODE_KINDS, "service")
        group = n.get("group")
        if group is not None and group not in group_ids:
            raise SpecError(f"{p}.group: unknown group {group!r}")
        items = []
        for j, it in enumerate(_list(n.get("items"), f"{p}.items", MAX_ITEMS)):
            q = f"{p}.items[{j}]"
            it = _keys(it, q, {"label", "note", "icon"}, {"label"})
            items.append(Item(_text(it["label"], f"{q}.label", False), _text(it.get("note"), f"{q}.note"),
                              _icon(it.get("icon"), f"{q}.icon")))
        if items and kind != "device":
            raise SpecError(f"{p}.items: only kind 'device' nodes can list items")
        if kind == "device" and not n.get("type"):
            raise SpecError(f"{p}.type: a device needs a type (shown on its folder tab)")
        nodes.append(Node(_ident(n["id"], f"{p}.id"), _text(n["label"], f"{p}.label", False), kind, group,
                          _text(n.get("type"), f"{p}.type"), _text(n.get("model"), f"{p}.model"),
                          _text(n.get("address"), f"{p}.address"), _text(n.get("os"), f"{p}.os"),
                          _text(n.get("note"), f"{p}.note"), _icon(n.get("icon"), f"{p}.icon"),
                          _color(n.get("color"), f"{p}.color", accents), tuple(items)))
    node_ids = _unique([n.id for n in nodes], "nodes")
    for nid in sorted(node_ids & group_ids):
        raise SpecError(f"nodes: id {nid!r} is used by a group and a node")
    endpoints = node_ids | group_ids

    links: list[Link] = []
    for i, ln in enumerate(_list(top.get("links"), "spec.links", MAX_LINKS)):
        p = f"links[{i}]"
        ln = _keys(ln, p, {"from", "to", "style", "color", "speed", "width", "label"}, {"from", "to"})
        for end in ("from", "to"):
            if ln[end] not in endpoints:
                raise SpecError(f"{p}.{end}: unknown node or group {ln[end]!r}")
        if ln["from"] == ln["to"]:
            raise SpecError(f"{p}: a link needs two different nodes")
        speed, width = _stroke(ln, p, speeds)
        links.append(Link(ln["from"], ln["to"], _choice(ln.get("style"), f"{p}.style", LINK_STYLES, "solid"),
                          _color(ln.get("color"), f"{p}.color", accents), speed, width,
                          _text(ln.get("label"), f"{p}.label")))

    legend: list[LegendEntry] = []
    for i, e in enumerate(_list(top.get("legend"), "spec.legend", 20)):
        p = f"legend[{i}]"
        e = _keys(e, p, {"label", "style", "color", "speed", "width"}, {"label"})
        speed, width = _stroke(e, p, speeds)
        legend.append(LegendEntry(_text(e["label"], f"{p}.label", False),
                                  _choice(e.get("style"), f"{p}.style", LINK_STYLES, "solid"),
                                  _color(e.get("color"), f"{p}.color", accents), speed, width))

    return Spec(title=_text(top["title"], "spec.title", False), subtitle=_text(top.get("subtitle"), "spec.subtitle"),
                footer=_text(top.get("footer"), "spec.footer"), theme=theme_name,
                width=_int(top.get("width", 2400), "spec.width", *WIDTH_RANGE), columns=columns,
                groups=tuple(groups), nodes=tuple(nodes), links=tuple(links), legend=tuple(legend))


def _unique(ids: list[str], path: str) -> set[str]:
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            raise SpecError(f"{path}: duplicate id {i!r}")
        seen.add(i)
    return seen


def load_spec(path: Path | str) -> Spec:
    """Read a .yaml/.yml/.json spec file (YAML is parsed with safe_load)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        raw = json.loads(text)
    elif p.suffix.lower() in (".yaml", ".yml"):
        raw = yaml.safe_load(text)
    else:
        raise SpecError(f"{p.name}: expected a .yaml, .yml or .json file")
    return parse_spec(raw)
