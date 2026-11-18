"""Decode spec documents without silently replacing repeated mapping keys."""
import json

import yaml


class DocumentError(ValueError):
    """Invalid or ambiguous document structure."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str):
            raise DocumentError("mapping keys must be strings")
        if key in result:
            raise DocumentError("duplicate mapping key")
        result[key] = value
    return result


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        pairs = [(self.construct_object(key, deep=deep), self.construct_object(value, deep=deep))
                 for key, value in node.value]
        return unique_pairs(pairs)


def decode(text: str, extension: str):
    try:
        if extension == ".json":
            return json.loads(text, object_pairs_hook=unique_pairs)
        return yaml.load(text, Loader=UniqueLoader)
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        raise DocumentError("invalid document syntax") from error
