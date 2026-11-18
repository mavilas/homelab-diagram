import json
import tempfile
import unittest
from pathlib import Path

from homelab_diagram import SpecError, load_spec, parse_spec
from tests.helpers import EXAMPLE, example_raw


class SpecTest(unittest.TestCase):
    def test_example_parses_into_typed_spec(self):
        spec = load_spec(EXAMPLE)
        self.assertEqual(spec.title, "Example homelab")
        self.assertEqual([n.id for n in spec.nodes], ["fw", "proxy", "pve", "nas"])
        self.assertEqual(spec.links[0].speed, "10G")

    def test_json_and_yaml_give_the_same_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "s.json")
            p.write_text(json.dumps(example_raw()))
            self.assertEqual(load_spec(p), load_spec(EXAMPLE))

    def assertRejected(self, raw, fragment):
        with self.assertRaises(SpecError) as cm:
            parse_spec(raw)
        self.assertIn(fragment, str(cm.exception))

    def test_unknown_keys_fail_closed(self):
        raw = example_raw()
        raw["nodes"][0]["ip_address"] = "10.0.0.1"
        self.assertRejected(raw, "nodes[0]: unknown key(s) ip_address")
        raw = example_raw()
        raw["layout"] = "auto"
        self.assertRejected(raw, "spec: unknown key(s) layout")

    def test_references_must_resolve(self):
        raw = example_raw()
        raw["nodes"][0]["group"] = "nope"
        self.assertRejected(raw, "nodes[0].group: unknown group 'nope'")
        raw = example_raw()
        raw["links"][0]["to"] = "ghost"
        self.assertRejected(raw, "links[0].to: unknown node or group 'ghost'")

    def test_duplicate_ids_and_self_links(self):
        raw = example_raw()
        raw["nodes"][1]["id"] = "fw"
        self.assertRejected(raw, "nodes: duplicate id 'fw'")
        raw = example_raw()
        raw["links"][0]["to"] = raw["links"][0]["from"]
        self.assertRejected(raw, "two different nodes")

    def test_colors_icons_and_text_are_validated(self):
        raw = example_raw()
        raw["groups"][0]["color"] = "red;stroke:url(x)"
        self.assertRejected(raw, "groups[0].color")
        raw = example_raw()
        raw["nodes"][0]["icon"] = "../../etc/passwd"
        self.assertRejected(raw, "nodes[0].icon")
        raw = example_raw()
        raw["title"] = "x" * 201
        self.assertRejected(raw, "spec.title")
        raw = example_raw()
        raw["nodes"][0]["label"] = "a\nb"
        self.assertRejected(raw, "nodes[0].label")

    def test_links_may_target_a_group_and_ids_are_unique_across_nodes_and_groups(self):
        raw = example_raw()
        raw["links"].append({"from": "fw", "to": "storage", "label": "to the whole group"})
        self.assertEqual(parse_spec(raw).links[-1].target, "storage")
        raw = example_raw()
        raw["nodes"][0]["id"] = "storage"
        raw["links"] = []
        self.assertRejected(raw, "id 'storage' is used by a group and a node")
        raw = example_raw()
        raw["links"][0]["to"] = "nowhere"
        self.assertRejected(raw, "unknown node or group 'nowhere'")

    def test_version_device_type_and_bounds(self):
        raw = example_raw()
        raw["version"] = 2
        self.assertRejected(raw, "spec.version")
        raw = example_raw()
        del raw["nodes"][0]["type"]
        self.assertRejected(raw, "nodes[0].type")
        raw = example_raw()
        raw["width"] = 100000
        self.assertRejected(raw, "spec.width")
        raw = example_raw()
        raw["links"][0]["width"] = 3
        self.assertRejected(raw, "give speed or width")
        raw = example_raw()
        raw["nodes"][1]["items"] = [{"label": "x"}]
        self.assertRejected(raw, "only kind 'device'")


if __name__ == "__main__":
    unittest.main()
