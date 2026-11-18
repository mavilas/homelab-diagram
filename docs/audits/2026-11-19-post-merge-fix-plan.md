# Post-merge audit fix plan

Goal: reject ambiguous or mistyped specs and stop external rendering tools with TERM-only bounded cleanup. Source base: 52303113610ad26f53b2ea352d06195b6474211f. No hosts or live services change.

1. Reproduce version bool/float acceptance, malformed reference TypeError, duplicate JSON/YAML keys, converter timeout cleanup, and failed converter version acceptance in tests before changing production code.
2. Keep schema validation in spec.py; share duplicate-key decoding in a small document adapter. Reject non-string reference values before set/dict membership.
3. Reuse the cluster TERM supervisor verbatim as a vendored internal module, documented by source digest; put all external tool execution behind one commands module. Preserve existing deadlines and renderer environment override.
4. Run focused regressions, full suite in the workflow-equivalent isolated Debian environment, build and source diff checks. Record exact revision, failures, skips, and environmental limitations.

Vendored supervisor source: homelab cluster/agent-mailbox/ci_shards/term_group.py, SHA256 52f491499dcf3c151cc61c29db86f86e2eb1b2b45d911eaac36f6453d215b448. Its own finite TERM grace and polling settings remain owned there. No import from another checkout at runtime. Existing original-render golden SVG bytes must stay unchanged.

Additional reproduced findings: failed conversion replaced an existing PNG with
partial bytes; the fix stages conversion and publishes per-file atomically.
Built wheels omitted the canonical icon lock and own glyphs; the build adapter
now generates bundled assets from those sources, and an isolated wheel import
check failed before the fix and passed afterward. Source and built resource
paths share resource_paths.py. The source inventory and service icons are not
published by this change.

Python subprocess timeout semantics were checked against the official Python
[subprocess documentation](https://docs.python.org/3/library/subprocess.html)
on November 19, 2026 JST. Its run(timeout=...) path kills the direct child;
the vendored group runner is used to retain TERM-only cleanup instead.
