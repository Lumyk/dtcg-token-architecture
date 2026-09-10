"""Validate this repository's token contracts, not the entire DTCG format.

No network or third-party dependencies. Human review still owns role intent,
description accuracy, recipe semantics, and rendered accessibility.
"""

import itertools
import json
import math
import re
import sys
from pathlib import Path

ALLOWED_TYPES = {
    "color",
    "dimension",
    "fontFamily",
    "fontWeight",
    "duration",
    "cubicBezier",
    "number",
    "strokeStyle",
    "border",
    "transition",
    "shadow",
    "gradient",
    "typography",
}
FORBIDDEN_NAME_CHARS = set("{}.")
THEME_ROOTS = {"color", "elevation"}
STATE_WORDS = {"hover", "pressed", "selected", "disabled"}
COMPONENT_SCHEMA_VERSION = 1


class ValidationError(Exception):
    pass


def _reject_duplicate_keys(pairs):
    """json.loads keeps the last duplicate silently; for a token file "the second
    declaration was ignored" is never what the author meant, so it fails here."""
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
    return dict(pairs)


def load_documents(root: Path) -> dict:
    documents = {}
    for path in sorted(root.rglob("*.json")):
        name = path.relative_to(root).as_posix()
        try:
            documents[name] = json.loads(
                path.read_text(),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError) as error:
            raise ValidationError(f"{name}: invalid JSON — {error}") from error
    if "default.resolver.json" not in documents:
        raise ValidationError("default.resolver.json missing")
    return documents


def _reject_constant(value):
    raise ValueError(f"non-finite JSON number {value}")


def walk_tokens(tree: dict, path=()):
    for key, child in tree.items():
        if key.startswith("$"):
            continue
        if isinstance(child, dict) and "$value" in child:
            yield path + (key,), child
        elif isinstance(child, dict):
            yield from walk_tokens(child, path + (key,))


def resolver_file_names(resolver: dict) -> tuple:
    set_names, theme_names = [], []
    for entry in resolver["sets"].values():
        set_names += [source["$ref"] for source in entry["sources"]]
    for context in resolver["modifiers"]["theme"]["contexts"].values():
        theme_names += [source["$ref"] for source in context]
    return set_names, theme_names


def _modifier_file_names(resolver: dict) -> list:
    names = []
    for modifier in resolver["modifiers"].values():
        for context in modifier["contexts"].values():
            names += [source["$ref"] for source in context]
    return names


def check_sources_exist(documents: dict, resolver: dict) -> None:
    set_names, _ = resolver_file_names(resolver)
    for name in set_names + _modifier_file_names(resolver):
        if name not in documents:
            raise ValidationError(f"resolver references missing file {name}")


def check_token_shapes(documents: dict) -> None:
    for name, tree in documents.items():
        if name.endswith(".resolver.json"):
            continue
        _check_group(tree, name, (), name.startswith("component/"))


def _is_current_component_schema(tree: dict) -> bool:
    if not isinstance(tree, dict) or not isinstance(tree.get("component", {}), dict):
        return False
    for component in tree.get("component", {}).values():
        if not isinstance(component, dict):
            continue
        extensions = component.get("$extensions", {})
        if (
            extensions.get("com.designsystem", {}).get("schemaVersion")
            == COMPONENT_SCHEMA_VERSION
        ):
            return True
    return False


def _check_group(
    node: dict, file_name: str, path: tuple, component_file: bool = False
) -> None:
    require(isinstance(node, dict), f"{file_name}: group must be an object")
    if "$description" in node:
        require(
            isinstance(node["$description"], str),
            f"{file_name}: {'.'.join(path)} description must be text",
        )
    if "$extensions" in node:
        require(
            isinstance(node["$extensions"], dict)
            and all(isinstance(value, dict) for value in node["$extensions"].values()),
            f"{file_name}: {'.'.join(path)} extensions must contain namespace objects",
        )
    for key, child in node.items():
        if key.startswith("$"):
            continue
        if FORBIDDEN_NAME_CHARS & set(key):
            raise ValidationError(
                f"{file_name}: illegal name {key!r} at {'.'.join(path)}"
            )
        if not isinstance(child, dict):
            raise ValidationError(
                f"{file_name}: non-object node {key!r} at {'.'.join(path)}"
            )
        if "$value" in child or "$type" in child:
            if "$value" not in child:
                raise ValidationError(
                    f"{file_name}: {'.'.join(path + (key,))} missing $value"
                )
            if child.get("$type") not in ALLOWED_TYPES:
                raise ValidationError(
                    f"{file_name}: {'.'.join(path + (key,))} has bad type "
                    f"{child.get('$type')!r}"
                )
            require(
                all(k.startswith("$") for k in child),
                f"{file_name}: {'.'.join(path + (key,))} mixes token and group",
            )
            if child.get("$type") == "shadow":
                _check_shadow_token(child, file_name, path + (key,))
            _check_group(child, file_name, path + (key,), component_file)
        else:
            _check_group(child, file_name, path + (key,), component_file)
    if component_file and file_name.startswith("component/"):
        _check_shadow_groups(node, file_name, path)
        _check_envelope_location(node, file_name, path)


def _check_envelope_location(node: dict, file_name: str, path: tuple) -> None:
    """§7: com.designsystem envelope only at component root or variant scope."""
    if "$extensions" not in node:
        return
    if "com.designsystem" not in node.get("$extensions", {}):
        return
    is_component_root = len(path) == 2 and path[0] == "component"
    is_variant_scope = (
        len(path) == 4 and path[0] == "component" and path[2] == "variant"
    )
    if not (is_component_root or is_variant_scope):
        raise ValidationError(
            f"{file_name}: com.designsystem envelope at illegal level {'.'.join(path)}"
        )
    _check_materials(node, file_name, path)


def _part_paths_with_background(scope: dict) -> set:
    """All parts.… paths that own a background leaf anywhere in the scope
    (base parts, size/layout members, state/selection snapshots)."""
    found = set()

    def scan_parts(parts, prefix):
        for part, body in parts.items():
            if part.startswith("$"):
                continue
            here = f"{prefix}.{part}" if prefix else f"parts.{part}"
            if isinstance(body, dict):
                if isinstance(body.get("background"), dict):
                    found.add(here)
                if isinstance(body.get("parts"), dict):
                    scan_parts(body["parts"], f"{here}.parts")

    def scan(node):
        if not isinstance(node, dict):
            return
        if isinstance(node.get("parts"), dict):
            scan_parts(node["parts"], "")
        for key, child in node.items():
            if key in ("size", "layout", "state", "selection") and isinstance(
                child, dict
            ):
                for member in child.values():
                    scan(member)

    scan(scope)
    return found


def _declared_part_paths(scope: dict) -> set:
    declared = set()

    def scan_parts(parts, prefix):
        for part, body in parts.items():
            if part.startswith("$"):
                continue
            here = f"{prefix}.{part}" if prefix else f"parts.{part}"
            declared.add(here)
            if isinstance(body, dict) and isinstance(body.get("parts"), dict):
                scan_parts(body["parts"], f"{here}.parts")

    def scan(node):
        if not isinstance(node, dict):
            return
        if isinstance(node.get("parts"), dict):
            scan_parts(node["parts"], "")
        for key, child in node.items():
            if key in ("size", "layout", "state", "selection") and isinstance(
                child, dict
            ):
                for member in child.values():
                    scan(member)

    scan(scope)
    return declared


def _check_materials(scope: dict, file_name: str, path: tuple) -> None:
    envelope = scope["$extensions"]["com.designsystem"]
    if "material" in envelope:
        raise ValidationError(
            f"{file_name}: legacy singular material at {'.'.join(path)} — "
            "use the materials map (§7)"
        )
    if "solidBackground" in envelope:
        raise ValidationError(
            f"{file_name}: solidBackground forbidden at {'.'.join(path)}"
        )
    materials = envelope.get("materials")
    if materials is None:
        return
    if not isinstance(materials, dict) or not materials:
        raise ValidationError(
            f"{file_name}: materials at {'.'.join(path)} must be a non-empty map"
        )
    slots = set(envelope.get("slots", []))
    declared = _declared_part_paths(scope)
    painted = _part_paths_with_background(scope)
    for target, descriptor in materials.items():
        if (
            not isinstance(descriptor, dict)
            or not isinstance(descriptor.get("kind"), str)
            or not descriptor["kind"]
        ):
            raise ValidationError(
                f"{file_name}: materials[{target!r}] needs an object "
                "descriptor with a non-empty kind"
            )
        if descriptor["kind"] == "solid":
            raise ValidationError(
                f'{file_name}: materials[{target!r}] kind "solid" is '
                "forbidden — absence is the solid baseline"
            )
        if target in slots:
            raise ValidationError(
                f"{file_name}: materials[{target!r}] targets a slot part"
            )
        if target not in declared:
            raise ValidationError(
                f"{file_name}: materials[{target!r}] does not resolve to a "
                f"declared part at {'.'.join(path)}"
            )
        if target not in painted:
            raise ValidationError(
                f"{file_name}: materials[{target!r}] targets a part with no "
                "background leaf"
            )


SHADOW_REQUIRED_FIELDS = {"offsetX", "offsetY", "blur", "spread", "color"}
SHADOW_OPTIONAL_FIELDS = {"inset"}


def _check_shadow_token(child: dict, file_name: str, path: tuple) -> None:
    value = child["$value"]
    if isinstance(value, str):
        return
    if isinstance(value, list):
        if not value:
            raise ValidationError(
                f"{file_name}: {'.'.join(path)} shadow layer list is empty"
            )
        for layer in value:
            _check_shadow_layer(layer, file_name, path)
        return
    _check_shadow_layer(value, file_name, path)


def _check_shadow_layer(value, file_name: str, path: tuple) -> None:
    if not isinstance(value, dict):
        raise ValidationError(
            f"{file_name}: {'.'.join(path)} shadow layer must be an object"
        )
    fields = set(value)
    missing = SHADOW_REQUIRED_FIELDS - fields
    extra = fields - SHADOW_REQUIRED_FIELDS - SHADOW_OPTIONAL_FIELDS
    if missing or extra:
        raise ValidationError(
            f"{file_name}: {'.'.join(path)} malformed shadow layer — "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    if "inset" in value and not isinstance(value["inset"], bool):
        raise ValidationError(
            f"{file_name}: {'.'.join(path)} shadow inset must be a boolean"
        )


def _check_shadow_groups(node: dict, file_name: str, path: tuple) -> None:
    """Component tier: `shadow` is always the fixed {outer, inner} pair."""
    shadow = node.get("shadow")
    if not isinstance(shadow, dict):
        return
    if "$value" in shadow or "$type" in shadow:
        raise ValidationError(
            f"{file_name}: {'.'.join(path + ('shadow',))} is a bare leaf — "
            "component shadow must be the {outer, inner} group"
        )
    slots = {key for key in shadow if not key.startswith("$")}
    if slots != {"outer", "inner"}:
        raise ValidationError(
            f"{file_name}: {'.'.join(path + ('shadow',))} must declare "
            f"exactly outer and inner, got {sorted(slots)}"
        )
    for slot in ("outer", "inner"):
        if "$value" not in shadow[slot]:
            raise ValidationError(
                f"{file_name}: {'.'.join(path + ('shadow', slot))} "
                "must be a shadow token"
            )


def check_theme_roots(documents: dict, resolver: dict) -> None:
    _, theme_names = resolver_file_names(resolver)
    for name in theme_names:
        roots = {key for key in documents[name] if not key.startswith("$")}
        if not roots <= THEME_ROOTS:
            extra = sorted(roots - THEME_ROOTS)
            raise ValidationError(f"{name}: foreign root namespaces {extra}")


def check_theme_parity(documents: dict, resolver: dict) -> None:
    contexts = resolver["modifiers"]["theme"]["contexts"]
    path_sets = {
        context: {
            ".".join(path): node["$type"]
            for source in sources
            for path, node in walk_tokens(documents[source["$ref"]])
        }
        for context, sources in contexts.items()
    }
    reference_name, reference = next(iter(sorted(path_sets.items())))
    for name, paths in sorted(path_sets.items()):
        if paths != reference:
            missing = sorted(set(reference) - set(paths))[:5]
            extra = sorted(set(paths) - set(reference))[:5]
            raise ValidationError(
                f"theme path/type parity broken between {reference_name} and {name}: "
                f"missing={missing} extra={extra}"
            )


def _is_alias(value) -> bool:
    return isinstance(value, str) and value.startswith("{") and value.endswith("}")


def flat_context(
    documents: dict, resolver: dict, context: str, appearance: str = None
) -> dict:
    choices = {key: value["default"] for key, value in resolver["modifiers"].items()}
    choices["theme"] = context
    if appearance is not None:
        choices["appearance"] = appearance
    return compose_context(documents, resolver, choices)


def compose_context(documents: dict, resolver: dict, choices: dict) -> dict:
    flat = {}
    for entry in resolver["resolutionOrder"]:
        kind, key = entry["$ref"].split("/")[1:]
        group = resolver[kind][key]
        sources = (
            group["sources"] if kind == "sets" else group["contexts"][choices[key]]
        )
        for source in sources:
            for path, node in walk_tokens(documents[source["$ref"]]):
                flat[".".join(path)] = node
    return flat


def check_state_bindings(documents: dict, resolver: dict) -> None:
    """State membership derives from the name grammar: a leaf whose final
    segment is a state word is a state leaf of its family, and the family
    base is the sibling ``default`` — or ``primary`` where the family ladder
    is ordinal. Hover leaves are always slots: their authored value must
    alias the family base."""
    _, theme_names = resolver_file_names(resolver)
    for name in theme_names:
        paths = {".".join(path) for path, _ in walk_tokens(documents[name])}
        for path, node in walk_tokens(documents[name]):
            if path[-1] not in STATE_WORDS:
                continue
            dotted = ".".join(path)
            base = next(
                (
                    candidate
                    for anchor in ("default", "primary")
                    if (candidate := ".".join(path[:-1] + (anchor,))) in paths
                ),
                None,
            )
            if base is None:
                raise ValidationError(
                    f"{name}: state leaf {dotted} has no family base "
                    f"(no sibling default or primary)"
                )
            if path[-1] == "hover" and node["$value"] != "{" + base + "}":
                raise ValidationError(
                    f"{name}: hover slot {dotted} must alias its family base "
                    f"{base}, found {node['$value']!r}"
                )


def check_sanctioned_aliases(documents: dict, resolver: dict) -> None:
    """Same-tier aliases inside semantic and theme files are forbidden except
    the contract's sanctioned list (§3): hover slots (pinned to the family
    base by check_state_bindings), the selected-state bridges to
    interactive.bold, recipe-internal elevation surfaces, and the addressed
    rhythm alias spacing.screen -> spacing.content. Extending this list is an
    architecture decision: amend the contract first, then this gate."""
    set_names, theme_names = resolver_file_names(resolver)
    semantic_names = [name for name in set_names if name.startswith("semantic/")]
    for name in semantic_names + theme_names:
        for path, node in walk_tokens(documents[name]):
            value = node["$value"]
            if not _is_alias(value) or value.startswith("{primitive."):
                continue
            dotted = ".".join(path)
            target = value[1:-1]
            if path[-1] == "hover":
                continue
            if dotted in (
                "color.fill.control.selected",
                "color.border.selected",
            ) and target.startswith("color.interactive.bold"):
                continue
            if (
                path[0] == "elevation"
                and path[-1] == "surface"
                and target.startswith("color.surface.")
            ):
                continue
            if dotted == "spacing.screen" and target == "spacing.content":
                continue
            raise ValidationError(
                f"{name}: unsanctioned same-tier alias {dotted} -> {target}"
            )


def check_appearance_deltas(documents: dict, resolver: dict) -> None:
    """§9 second appearance recipe: every delta leaf must override an existing
    component path with the same $type, a value that differs from the base,
    and — for colors — an alias (so theme × appearance composes)."""
    appearance = resolver["modifiers"].get("appearance")
    if appearance is None:
        return
    if appearance["contexts"].get(appearance["default"]):
        raise ValidationError(
            "appearance default context must be empty — the canonical "
            "recipe lives in the component set"
        )
    base = {}
    base_tree = {"component": {}}
    for source in resolver["sets"]["component"]["sources"]:
        base_tree["component"].update(documents[source["$ref"]]["component"])
        for path, node in walk_tokens(documents[source["$ref"]]):
            base[".".join(path)] = node
    for context, sources in appearance["contexts"].items():
        for source in sources:
            name = source["$ref"]
            check_delta(name, documents[name], base_tree)
            for path, node in walk_tokens(documents[name]):
                dotted = ".".join(path)
                if dotted not in base:
                    raise ValidationError(
                        f"{name}: appearance delta introduces new path {dotted}"
                    )
                base_node = base[dotted]
                if node["$type"] != base_node["$type"]:
                    raise ValidationError(
                        f"{name}: {dotted} type {node['$type']!r} differs "
                        f"from base type {base_node['$type']!r}"
                    )
                if node["$value"] == base_node["$value"]:
                    raise ValidationError(
                        f"{name}: {dotted} must differ from the base value"
                    )
                if node["$type"] == "color" and not _is_alias(node["$value"]):
                    raise ValidationError(
                        f"{name}: {dotted} color must be an alias, not a raw value"
                    )


def check_material_ownership(documents: dict) -> None:
    """§7: no target at both root and variant; identical-everywhere hoists."""
    for name, tree in documents.items():
        if not name.startswith("component/") or not _is_current_component_schema(tree):
            continue
        for component_name, component in tree.get("component", {}).items():
            root_map = (
                component.get("$extensions", {})
                .get("com.designsystem", {})
                .get("materials", {})
            )
            variants = component.get("variant", {})
            variant_maps = {
                variant_name: variant.get("$extensions", {})
                .get("com.designsystem", {})
                .get("materials", {})
                for variant_name, variant in variants.items()
                if not variant_name.startswith("$")
            }
            for variant_name, variant_map in variant_maps.items():
                overlap = set(root_map) & set(variant_map)
                if overlap:
                    raise ValidationError(
                        f"{name}: {component_name} materials target "
                        f"{sorted(overlap)} at both root and variant "
                        f"{variant_name}"
                    )
            if variant_maps and all(variant_maps.values()):
                maps = list(variant_maps.values())
                common = {
                    target: maps[0][target]
                    for target in maps[0]
                    if all(m.get(target) == maps[0][target] for m in maps)
                }
                if common and len(maps) == len(variant_maps):
                    raise ValidationError(
                        f"{name}: {component_name} materials "
                        f"{sorted(common)} identical in every variant — "
                        "hoist to the component root (§7)"
                    )


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def members(node):
    return {key: value for key, value in node.items() if not key.startswith("$")}


def check_resolver(documents, name, resolver):
    expected = [
        "#/sets/primitive",
        "#/sets/semantic",
        "#/modifiers/theme",
        "#/sets/component",
        "#/modifiers/appearance",
    ]
    require(isinstance(resolver, dict), f"{name}: resolver must be an object")
    require(
        resolver.get("version") == "2025.10", f"{name}: unsupported resolver version"
    )
    require(
        isinstance(resolver.get("sets"), dict)
        and set(resolver["sets"]) == {"primitive", "semantic", "component"},
        f"{name}: expected primitive, semantic, component sets",
    )
    require(
        isinstance(resolver.get("modifiers"), dict)
        and set(resolver["modifiers"]) == {"theme", "appearance"},
        f"{name}: expected theme and appearance modifiers; extend the gate for new axes",
    )
    require(
        resolver.get("resolutionOrder") == [{"$ref": ref} for ref in expected],
        f"{name}: resolutionOrder must be primitive → semantic → theme → component → appearance",
    )
    for kind in ("sets", "modifiers"):
        for key, group in resolver[kind].items():
            require(isinstance(group, dict), f"{name}: invalid {kind}/{key}")
            if kind == "sets":
                lists = [group.get("sources")]
            else:
                contexts = group.get("contexts")
                require(
                    isinstance(contexts, dict) and bool(contexts),
                    f"{name}: {key} contexts must be non-empty",
                )
                require(
                    isinstance(group.get("default"), str)
                    and group["default"] in contexts,
                    f"{name}: {key} default context missing",
                )
                lists = list(contexts.values())
            for sources in lists:
                require(isinstance(sources, list), f"{name}: source list required")
                seen = set()
                for source in sources:
                    require(
                        isinstance(source, dict)
                        and set(source) == {"$ref"}
                        and isinstance(source["$ref"], str),
                        f"{name}: invalid source reference",
                    )
                    ref = source["$ref"]
                    require(
                        ref in documents and ref.endswith(".tokens.json"),
                        f"{name}: missing token source {ref}",
                    )
                    require(ref not in seen, f"{name}: duplicate source {ref}")
                    seen.add(ref)


def groups(node, path=()):
    yield path, node
    if "$value" not in node:
        for key, child in members(node).items():
            yield from groups(child, path + (key,))


def check_delta(name, delta, base):
    base_nodes = dict(groups(base))
    require(bool(list(walk_tokens(delta))), f"{name}: empty override")
    for path, node in groups(delta):
        require(path in base_nodes, f"{name}: new override path {'.'.join(path)}")
        original = base_nodes[path]
        for key in node:
            if key.startswith("$") and key not in {"$value", "$description"}:
                require(
                    node[key] == original.get(key),
                    f"{name}: override changes metadata/type at {'.'.join(path)}",
                )
        if "$value" in node:
            require(
                "$value" in original and node["$type"] == original.get("$type"),
                f"{name}: override type mismatch at {'.'.join(path)}",
            )
            require(
                node["$value"] != original["$value"],
                f"{name}: override must differ from base at {'.'.join(path)}",
            )


def check_platforms(documents):
    base = documents["default.resolver.json"]
    registered = set()
    for name, resolver in documents.items():
        if not name.endswith(".resolver.json"):
            continue
        platform = name.removesuffix(".resolver.json")
        prefix = f"platform/{platform}/"
        if platform != "default":
            require(
                platform in {"ios", "android", "web"}, f"{name}: unregistered platform"
            )
        require(
            resolver["resolutionOrder"] == base["resolutionOrder"],
            f"{name}: platform resolution order differs",
        )
        for kind in ("sets", "modifiers"):
            require(
                set(resolver[kind]) == set(base[kind]),
                f"{name}: platform composition differs",
            )
            for key, group in resolver[kind].items():
                original = base[kind][key]
                if kind == "sets":
                    cells = [(key, group["sources"], original["sources"])]
                else:
                    require(
                        group["default"] == original["default"]
                        and set(group["contexts"]) == set(original["contexts"]),
                        f"{name}: platform contexts/default differ",
                    )
                    cells = [
                        (context, refs, original["contexts"][context])
                        for context, refs in group["contexts"].items()
                    ]
                for cell, refs, originals in cells:
                    names = [ref["$ref"] for ref in refs]
                    core = [ref["$ref"] for ref in originals]
                    if platform == "default":
                        require(
                            not any(ref.startswith("platform/") for ref in names),
                            "default resolver must not contain platform overrides",
                        )
                        for ref in names:
                            expected = key + "/" if kind == "sets" else f"{key}/{cell}/"
                            require(
                                ref.startswith(expected),
                                f"{name}: misplaced source {ref}",
                            )
                    else:
                        require(
                            names[: len(core)] == core,
                            f"{name}: preserve base source order before overrides",
                        )
                        for ref in names[len(core) :]:
                            require(
                                ref.startswith(prefix) and ref[len(prefix) :] in core,
                                f"{name}: override {ref} does not mirror this composition cell",
                            )
                    registered.update(names)
    token_files = {name for name in documents if name.endswith(".tokens.json")}
    require(
        registered == token_files,
        f"unreferenced token files: {sorted(token_files - registered)}",
    )
    for name, delta in documents.items():
        if not name.startswith("platform/"):
            continue
        core = "/".join(name.split("/")[2:])
        require(core in documents, f"{name}: missing mirrored base file {core}")
        check_delta(name, delta, documents[core])
        if core.startswith(("primitive/", "semantic/")):
            for path, node in walk_tokens(delta):
                require(
                    node["$type"]
                    not in {"typography", "shadow", "border", "gradient", "transition"},
                    f"{name}: composite override forbidden at {'.'.join(path)}",
                )


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


COMPOSITE_FIELDS = {
    "typography": {
        "fontFamily": "fontFamily",
        "fontSize": "dimension",
        "fontWeight": "fontWeight",
        "letterSpacing": "dimension",
        "lineHeight": "number",
    },
    "shadow": {
        "color": "color",
        "offsetX": "dimension",
        "offsetY": "dimension",
        "blur": "dimension",
        "spread": "dimension",
    },
    "border": {"color": "color", "width": "dimension", "style": "strokeStyle"},
    "transition": {
        "duration": "duration",
        "delay": "duration",
        "timingFunction": "cubicBezier",
    },
}


def resolve_values(flat, label):
    """Resolve and type-check whole-token and nested composite references."""
    cache = {}

    def token(path, stack=()):
        require(path in flat, f"[{label}] missing token {path}")
        require(
            path not in stack, f"[{label}] alias cycle: {' -> '.join((*stack, path))}"
        )
        if path not in cache:
            node = flat[path]
            cache[path] = value(node["$value"], node["$type"], path, (*stack, path))
        return cache[path]

    def value(raw, kind, where, stack):
        error = f"[{label}] {where}: invalid {kind} value"
        if _is_alias(raw):
            target = raw[1:-1]
            require(target in flat, f"[{label}] {where}: missing token {target}")
            require(
                not target.startswith("component."),
                f"[{label}] {where}: component alias target forbidden",
            )
            require(
                flat[target]["$type"] == kind,
                f"[{label}] {where}: alias type mismatch for {target}, expected {kind}",
            )
            return token(target, stack)
        if kind == "number":
            require(numeric(raw), error)
        elif kind in {"dimension", "duration"}:
            units = {"px", "rem"} if kind == "dimension" else {"ms", "s"}
            require(
                isinstance(raw, dict)
                and set(raw) == {"unit", "value"}
                and isinstance(raw["unit"], str)
                and raw["unit"] in units
                and numeric(raw["value"]),
                error,
            )
            if kind == "duration":
                require(raw["value"] >= 0, error)
        elif kind == "fontFamily":
            require(
                (isinstance(raw, str) and bool(raw))
                or (
                    isinstance(raw, list)
                    and bool(raw)
                    and all(isinstance(item, str) and bool(item) for item in raw)
                ),
                error,
            )
        elif kind == "fontWeight":
            names = {
                "thin",
                "hairline",
                "extra-light",
                "ultra-light",
                "light",
                "normal",
                "regular",
                "book",
                "medium",
                "semi-bold",
                "demi-bold",
                "bold",
                "extra-bold",
                "ultra-bold",
                "black",
                "heavy",
                "extra-black",
                "ultra-black",
            }
            require(
                (numeric(raw) and 1 <= raw <= 1000)
                or (isinstance(raw, str) and raw in names),
                error,
            )
        elif kind == "color":
            require(
                isinstance(raw, dict) and raw.get("colorSpace") == "srgb",
                error
                + " (this gate supports sRGB; extend it before adding another space)",
            )
            rgb = raw.get("components")
            require(
                isinstance(rgb, list)
                and len(rgb) == 3
                and all(numeric(v) and 0 <= v <= 1 for v in rgb),
                error,
            )
            require(
                numeric(raw.get("alpha", 1)) and 0 <= raw.get("alpha", 1) <= 1, error
            )
        elif kind == "cubicBezier":
            require(
                isinstance(raw, list)
                and len(raw) == 4
                and all(numeric(v) for v in raw)
                and 0 <= raw[0] <= 1
                and 0 <= raw[2] <= 1,
                error,
            )
        elif kind in COMPOSITE_FIELDS:
            if kind == "shadow" and isinstance(raw, list):
                require(bool(raw), error)
                return [
                    value(item, kind, f"{where}[{i}]", stack)
                    for i, item in enumerate(raw)
                ]
            fields = COMPOSITE_FIELDS[kind]
            optional = {"inset"} if kind == "shadow" else set()
            require(
                isinstance(raw, dict)
                and set(fields) <= set(raw)
                and set(raw) <= set(fields) | optional,
                error,
            )
            resolved = {
                field: value(raw[field], field_type, f"{where}.{field}", stack)
                for field, field_type in fields.items()
            }
            if "inset" in raw:
                require(isinstance(raw["inset"], bool), error)
                resolved["inset"] = raw["inset"]
            if kind == "shadow":
                require(resolved["blur"]["value"] >= 0, error + " (negative blur)")
            return resolved
        elif kind == "strokeStyle":
            if isinstance(raw, str):
                require(
                    raw
                    in {
                        "solid",
                        "dashed",
                        "dotted",
                        "double",
                        "groove",
                        "ridge",
                        "outset",
                        "inset",
                    },
                    error,
                )
            else:
                require(
                    isinstance(raw, dict)
                    and set(raw) == {"dashArray", "lineCap"}
                    and isinstance(raw["lineCap"], str)
                    and raw["lineCap"] in {"round", "butt", "square"}
                    and isinstance(raw["dashArray"], list)
                    and bool(raw["dashArray"]),
                    error,
                )
                return {
                    "lineCap": raw["lineCap"],
                    "dashArray": [
                        value(item, "dimension", f"{where}.dashArray", stack)
                        for item in raw["dashArray"]
                    ],
                }
        elif kind == "gradient":
            require(isinstance(raw, list) and bool(raw), error)
            stops = []
            for i, item in enumerate(raw):
                require(
                    isinstance(item, dict) and set(item) == {"color", "position"}, error
                )
                position = value(
                    item["position"], "number", f"{where}[{i}].position", stack
                )
                require(0 <= position <= 1, error)
                stops.append(
                    {
                        "position": position,
                        "color": value(
                            item["color"], "color", f"{where}[{i}].color", stack
                        ),
                    }
                )
            return stops
        else:
            raise ValidationError(error + " (unsupported type)")
        return raw

    for path in flat:
        token(path)
    return cache


PART_NAMES = set(
    "container content label title subtitle placeholder helper counter input icon leadingIcon "
    "trailingIcon track fill indicator separator divider segment box dot badge ring outline "
    "bar chevron initials emoji".split()
)
DIMENSION_PROPERTIES = set(
    "borderWidth cornerRadius dashLength dashGap borderWidthTop borderWidthBottom "
    "cornerRadiusTop cornerRadiusBottom width height minWidth minHeight size diameter "
    "thickness paddingHorizontal paddingVertical paddingTop paddingBottom paddingLeading "
    "paddingTrailing gap inset offset offsetX offsetY focusRingWidth focusRingOffset".split()
)
PROPERTY_TYPES = {
    **dict.fromkeys(DIMENSION_PROPERTIES, "dimension"),
    **dict.fromkeys(
        "background color borderColor borderColorTop borderColorBottom focusRingColor".split(),
        "color",
    ),
    "opacity": "number",
    "typography": "typography",
}
FAMILIES = {"size", "layout", "state"}


def shape(surface):
    return {path: node["$type"] for path, node in surface.items()}


def values(surface):
    return {path: node["$value"] for path, node in surface.items()}


def part_surface(parts, label, prefix=()):
    surface = {}
    for part, body in members(parts).items():
        require(part in PART_NAMES, f"{label}: unregistered part {part}")
        here = prefix + ("parts", part)
        for prop, node in members(body).items():
            if prop == "parts":
                surface.update(part_surface(node, label, here))
            elif prop == "shadow":
                _check_shadow_groups(body, label, here)
                for slot, leaf in members(node).items():
                    require(leaf.get("$type") == "shadow", f"{label}: shadow slot type")
                    surface[here + (prop, slot)] = leaf
            else:
                require(
                    prop in PROPERTY_TYPES, f"{label}: unregistered property {prop}"
                )
                require(
                    "$value" in node and node.get("$type") == PROPERTY_TYPES[prop],
                    f"{label}: property type mismatch at {'.'.join(here + (prop,))}",
                )
                surface[here + (prop,)] = node
        require(
            ("dashGap" in body) == ("dashLength" in body),
            f"{label}: dash geometry requires both leaves",
        )
    return surface


def state_words(state, label):
    words = re.findall(r"[A-Z]?[a-z]+", state)
    canonical = [word.lower() for word in words]
    allowed = {"default", "hover", "pressed", "focused", "error", "disabled"}
    require(
        words
        and words[0] == canonical[0]
        and "".join(words) == state
        and set(canonical) <= allowed,
        f"{label}: invalid state name {state}",
    )
    rank = {"hover": 0, "pressed": 0, "focused": 0, "error": 1, "disabled": 2}
    if len(canonical) > 1:
        require(
            "default" not in canonical
            and len(set(canonical)) == len(canonical)
            and all(rank[a] < rank[b] for a, b in zip(canonical, canonical[1:])),
            f"{label}: invalid compound-state order {state}",
        )
    return canonical


def scope_surface(scope, label, inherited_envelope):
    require(
        set(members(scope)) <= {"parts", *FAMILIES},
        f"{label}: invalid axis nesting or loose property",
    )
    envelope = {
        **inherited_envelope,
        **scope.get("$extensions", {}).get("com.designsystem", {}),
    }
    owners = {}

    def own(surface, owner):
        for path, node in surface.items():
            require(
                path not in owners, f"{label}: duplicate owner for {'.'.join(path)}"
            )
            owners[path] = (owner, node)

    own(part_surface(scope.get("parts", {}), label), "base")
    for family in sorted(FAMILIES & set(scope)):
        group = members(scope[family])
        require(len(group) >= 2, f"{label}: {family} needs at least two members")
        if family == "size":
            allowed_sizes = {
                "small",
                "medium",
                "large",
                "extraSmall",
                "extraLarge",
                "compact",
                "default",
                "spacious",
            }
            require(
                set(group) <= allowed_sizes and set(group) != {"default"},
                f"{label}: invalid size names",
            )
        if family == "state":
            require("default" in group, f"{label}: state.default required")
        snapshots = {}
        selection_sets = {}
        for key, body in group.items():
            location = f"{label}.{family}.{key}"
            if family == "state":
                state_words(key, label)
            require(
                set(members(body)) <= {"parts", "selection"},
                f"{location}: invalid family nesting",
            )
            if "selection" in body:
                require(family == "state", f"{location}: selection only under state")
                choices = members(body["selection"])
                require(
                    bool(choices) and set(choices) <= {"selected", "unselected"},
                    f"{location}: invalid selection",
                )
                selection_sets[key] = set(choices)
            else:
                choices = {"": body}
                selection_sets[key] = set()
            for selection, snapshot in choices.items():
                require(
                    set(members(snapshot)) == {"parts"},
                    f"{location}: snapshot requires parts only",
                )
                surface = part_surface(snapshot["parts"], location)
                if "selection" in body:
                    common = part_surface(body.get("parts", {}), location)
                    require(
                        not (set(common) & set(surface)),
                        f"{location}: duplicate state/selection owner",
                    )
                    surface = {**common, **surface}
                require(bool(surface), f"{location}: empty snapshot")
                snapshots[key, selection] = surface
        if family == "state" and any(selection_sets.values()):
            unsupported = envelope.get("unsupportedCombinations", [])
            require(
                isinstance(unsupported, list),
                f"{label}: unsupportedCombinations must be a list",
            )
            missing = {
                (key, selection)
                for key in group
                for selection in ("selected", "unselected")
                if selection not in selection_sets[key]
            }
            declared = set()
            for pair in unsupported:
                require(
                    isinstance(pair, dict)
                    and set(pair) == {"state", "selection"}
                    and isinstance(pair["state"], str)
                    and isinstance(pair["selection"], str),
                    f"{label}: malformed unsupported combination",
                )
                declared.add((pair["state"], pair["selection"]))
            require(
                missing == declared,
                f"{label}: incomplete selection matrix or stale unsupported combination",
            )
        reference = next(iter(snapshots.values()))
        for key, snapshot in snapshots.items():
            require(
                shape(snapshot) == shape(reference),
                f"{label}.{family}.{key}: incomplete family surface",
            )
        own(reference, family)
        if family == "state":
            for (state, selection), snapshot in snapshots.items():
                default = snapshots.get(("default", selection))
                if state == "hover":
                    require(
                        default is not None and values(snapshot) == values(default),
                        f"{label}: authored hover must equal default",
                    )
                words = state_words(state, label)
                if len(words) > 1:
                    constituents = [snapshots.get((word, selection)) for word in words]
                    require(
                        all(c is not None for c in constituents),
                        f"{label}: compound state missing constituent",
                    )
                    for path, node in snapshot.items():
                        require(
                            any(
                                node["$value"] == c[path]["$value"]
                                for c in constituents
                            ),
                            f"{label}: compound state invents third value at {'.'.join(path)}",
                        )
                if default is not None:
                    for interaction in ("pressed", "disabled"):
                        if interaction not in words:
                            continue
                        dimmed = any(
                            n["$value"] == "{opacity." + interaction + "}"
                            for n in snapshot.values()
                        )
                        swapped = any(
                            n["$type"] == "color"
                            and n["$value"] != default[p]["$value"]
                            for p, n in snapshot.items()
                        )
                        require(
                            not (dimmed and swapped),
                            f"{label}: {interaction} double dimming",
                        )
    return owners


def check_components(documents):
    for file, tree in documents.items():
        if not file.startswith("component/"):
            continue
        key = Path(file).name.removesuffix(".tokens.json")
        key = re.sub(r"-([a-z])", lambda match: match[1].upper(), key)
        require(
            set(members(tree)) == {"component"}
            and set(members(tree["component"])) == {key},
            f"{file}: component namespace/file-name mismatch",
        )
        component = tree["component"][key]
        envelope = component.get("$extensions", {}).get("com.designsystem", {})
        require(
            type(envelope.get("schemaVersion")) is int
            and envelope["schemaVersion"] == COMPONENT_SCHEMA_VERSION,
            f"{file}: schemaVersion {COMPONENT_SCHEMA_VERSION} required",
        )
        require(
            envelope.get("variantKind", "structural") == "structural",
            f"{file}: invalid variantKind",
        )
        root = {k: v for k, v in component.items() if k != "variant"}
        root_owners = scope_surface(root, file, envelope)
        variants = members(component.get("variant", {}))
        if "variant" in component:
            require(
                len(variants) >= 2 and "default" not in variants,
                f"{file}: invalid variant family",
            )
        variant_surfaces = []
        for name, variant in variants.items():
            require(
                isinstance(variant.get("$description"), str)
                and bool(variant["$description"].strip()),
                f"{file}: variant {name} needs an instruction description",
            )
            require(
                not (FAMILIES & set(root) & set(variant)),
                f"{file}: family split across root and variant",
            )
            owners = scope_surface(variant, f"{file}.variant.{name}", envelope)
            require(
                not (set(root_owners) & set(owners)),
                f"{file}: duplicate root/variant owner",
            )
            variant_surfaces.append({p: n for p, n in walk_tokens(variant)})
        if variant_surfaces:
            first = variant_surfaces[0]
            for surface in variant_surfaces[1:]:
                if "variantKind" not in envelope:
                    require(
                        shape(surface) == shape(first),
                        f"{file}: intent variant shape mismatch",
                    )
                for path in set(first) & set(surface):
                    require(
                        first[path]["$type"] == surface[path]["$type"],
                        f"{file}: shared structural path type mismatch",
                    )
        slots = envelope.get("slots", [])
        require(
            isinstance(slots, list) and all(isinstance(s, str) for s in slots),
            f"{file}: invalid slots",
        )
        declared = _declared_part_paths(root)
        for variant in variants.values():
            declared |= _declared_part_paths(variant)
        require(set(slots) <= declared, f"{file}: slot targets undeclared part")
        for path, node in walk_tokens(component):
            canonical = path[path.index("parts") :]
            for slot in slots:
                prefix = tuple(slot.split("."))
                if canonical[: len(prefix)] == prefix:
                    require(
                        node["$type"] == "dimension",
                        f"{file}: slot carries paint or typography",
                    )
            if node["$type"] == "color":
                require(
                    _is_alias(node["$value"])
                    and (
                        node["$value"].startswith("{color.")
                        or node["$value"] == "{primitive.color.transparent}"
                    ),
                    f"{file}: component colors must alias semantic roles",
                )


def check_resolved_metrics(flat, resolved, label):
    for path, node in flat.items():
        result = resolved[path]
        if path.startswith("component.") and node["$type"] == "typography":
            require(
                _is_alias(node["$value"]) and node["$value"].startswith("{typography."),
                f"[{label}] {path}: component typography must alias semantic roles",
            )
        if path.startswith("component.") and node["$type"] == "color":
            require(
                _is_alias(node["$value"])
                and (
                    node["$value"].startswith("{color.")
                    or node["$value"] == "{primitive.color.transparent}"
                ),
                f"[{label}] {path}: component colors must alias semantic roles",
            )
        if path.startswith("opacity.") or path.endswith(".opacity"):
            require(
                numeric(result) and 0 <= result <= 1,
                f"[{label}] {path}: opacity outside 0..1",
            )
        if path.endswith(".dashLength"):
            gap = path.removesuffix("dashLength") + "dashGap"
            require(gap in resolved, f"[{label}] {path}: missing dashGap")
            other = resolved[gap]
            require(
                result["unit"] == other["unit"]
                and result["value"] >= 0
                and other["value"] >= 0
                and (
                    (result["value"] == other["value"] == 0)
                    or (result["value"] > 0 and other["value"] > 0)
                ),
                f"[{label}] {path}: invalid dash geometry",
            )


# Explicit executable pair declarations from token usage descriptions.
# Extend these checks with new usage; prose is not a machine rule language.
def component_members(flat, prefix):
    return {
        path[len(prefix) :].split(".")[0] for path in flat if path.startswith(prefix)
    }


def active_states(flat, prefix):
    return {
        state
        for state in component_members(flat, prefix)
        if "disabled" not in state_words(state, prefix)
    }


def disabled_path(path):
    match = re.search(r"\.state\.([^.]+)\.", path)
    return bool(match and "disabled" in state_words(match[1], path))


SURFACES = ["color.canvas.default", "color.canvas.inset"] + [
    f"color.surface.{n}" for n in ("default", "raised", "overlay", "subtle")
]
FILLS = ["color.fill.input", "color.fill.subtle"]
CONTROL = [f"color.fill.control.{n}" for n in ("default", "hover", "pressed")]
STATUSES = ("error", "info", "success", "warning")
WASHES = [f"color.status.{n}.subtle" for n in STATUSES]


def semantic_pairs(flat):
    pairs = set()

    def add(fg, backgrounds, minimum=4.5):
        pairs.update((fg, bg, minimum, None) for bg in backgrounds)

    for rank in ("primary", "secondary", "tertiary"):
        add(f"color.text.{rank}", SURFACES + FILLS + CONTROL + WASHES)
    for rank in ("primary", "secondary"):
        add(f"color.icon.{rank}", SURFACES + FILLS + CONTROL + WASHES, 3)
    for status in STATUSES:
        add(
            f"color.text.{status}", SURFACES + FILLS + [f"color.status.{status}.subtle"]
        )
        add(
            f"color.icon.{status}",
            SURFACES + FILLS + [f"color.status.{status}.subtle"],
            3,
        )
        add(f"color.status.{status}.onBold", [f"color.status.{status}.bold"])
    for kind, on in [("bold", "onBold"), ("danger", "onDanger")]:
        add(
            f"color.interactive.{on}",
            [f"color.interactive.{kind}.{s}" for s in ("default", "hover", "pressed")],
        )
    add("color.interactive.onBold", ["color.fill.control.selected"])
    for state in ("default", "hover", "pressed"):
        add(
            f"color.interactive.tint.{state}",
            SURFACES + FILLS + [f"color.interactive.subtle.{state}"],
        )
    add("color.interactive.tint.default", ["color.interactive.subtle.selected"])
    add("color.interactive.tint.inverse", ["color.surface.inverse"])
    add("color.text.inverse", ["color.surface.inverse"])
    add("color.icon.inverse", ["color.surface.inverse"], 3)
    add("color.text.placeholder", ["color.fill.input"])
    for path in sorted(flat):
        if path.startswith("color.identity.") and path.endswith(".ink"):
            add(path, [path.removesuffix("ink") + "background"])
    for border in ("input", "selected", *STATUSES):
        add(f"color.border.{border}", SURFACES + FILLS, 3)
    add("color.focus.ring", SURFACES + FILLS, 3)
    add("color.interactive.bold.default", ["color.fill.subtle"], 3)
    return sorted(pairs)


def component_pairs(flat):
    pairs = []
    for variant in component_members(flat, "component.badge.variant."):
        base = f"component.badge.variant.{variant}.parts"
        for part, minimum in [("label", 4.5), ("icon", 3)]:
            pairs.append(
                (f"{base}.{part}.color", f"{base}.container.background", minimum, None)
            )
    for variant in component_members(flat, "component.button.variant."):
        for state in active_states(flat, f"component.button.variant.{variant}.state."):
            base = f"component.button.variant.{variant}.state.{state}.parts"
            for part, minimum in [("label", 4.5), ("icon", 3)]:
                for backdrop in SURFACES:
                    pairs.append(
                        (
                            f"{base}.{part}.color",
                            f"{base}.container.background",
                            minimum,
                            backdrop,
                        )
                    )
    for state in active_states(flat, "component.textField.state."):
        for part in (
            "input",
            "label",
            "placeholder",
            "leadingIcon",
            "trailingIcon",
            "chevron",
        ):
            pairs.append(
                (
                    f"component.textField.state.{state}.parts.{part}.color",
                    "component.textField.parts.container.background",
                    3 if part in ("leadingIcon", "trailingIcon", "chevron") else 4.5,
                    None,
                )
            )
        for part in ("helper", "counter"):
            for backdrop in SURFACES:
                pairs.append(
                    (
                        f"component.textField.state.{state}.parts.{part}.color",
                        backdrop,
                        4.5,
                        None,
                    )
                )
        for border in ("borderColorBottom",):
            pairs.append(
                (
                    f"component.textField.state.{state}.parts.container.{border}",
                    "component.textField.parts.container.background",
                    3,
                    None,
                )
            )
    for selection in ("selected", "unselected"):
        background = "indicator" if selection == "selected" else "container"
        for part in ("label", "icon"):
            for backdrop in SURFACES:
                pairs.append(
                    (
                        f"component.segmentedControl.state.default.selection.{selection}.parts.segment.parts.{part}.color",
                        f"component.segmentedControl.parts.{background}.background",
                        4.5 if part == "label" else 3,
                        backdrop,
                    )
                )
    pairs.append(
        (
            "component.progress.parts.fill.background",
            "component.progress.parts.track.background",
            3,
            None,
        )
    )
    pairs.append(
        (
            "component.avatar.parts.icon.color",
            "component.avatar.parts.placeholder.background",
            3,
            None,
        )
    )
    return pairs


def contrast_ratio(foreground, background, backdrop=None):
    """WCAG relative luminance, after sRGB alpha composition; never round to pass."""
    rgb = background["components"]
    alpha = background.get("alpha", 1)
    if alpha < 1:
        require(
            backdrop is not None and backdrop.get("alpha", 1) == 1,
            "translucent background needs an explicit opaque backdrop",
        )
        rgb = [a * alpha + b * (1 - alpha) for a, b in zip(rgb, backdrop["components"])]
    alpha = foreground.get("alpha", 1)
    ink = [a * alpha + b * (1 - alpha) for a, b in zip(foreground["components"], rgb)]

    def luminance(components):
        linear = [
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            for v in components
        ]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    low, high = sorted((luminance(ink), luminance(rgb)))
    return (high + 0.05) / (low + 0.05)


def component_opacity(path, resolved, background=None):
    """Return container and foreground-part opacities for the current recipe scopes."""
    if not path.startswith("component."):
        return 1, 1
    segments = path.split(".")
    scope = path.split(".parts.")[0]
    scopes = {".".join(segments[:2]), scope}
    if "variant" in segments:
        scopes.add(".".join(segments[:4]))
    if ".selection." in scope:
        scopes.add(scope.split(".selection.")[0])
    container = 1
    for prefix in scopes:
        container *= resolved.get(prefix + ".parts.container.opacity", 1)
    parts = path[len(scope) + 1 :].split(".")[:-1]
    background_parts = (
        background.split(".parts.", 1)[1].split(".")[:-1]
        if background and ".parts." in background
        else []
    )
    own = 1
    for end in range(2, len(parts) + 1, 2):
        ancestor = parts[:end]
        if ancestor == ["parts", "container"]:
            continue  # Already accounted for as whole-recipe opacity.
        for prefix in sorted(scopes):
            opacity = resolved.get(prefix + "." + ".".join(ancestor) + ".opacity", 1)
            require(
                opacity == 1 or background_parts[: end - 1] != ancestor[1:],
                f"{path}: shared nested opacity needs explicit contrast recipe support",
            )
            own *= opacity
    return container, own


def check_contrast(flat, resolved, label, high_contrast):
    expected = {
        "avatar",
        "badge",
        "button",
        "card",
        "progress",
        "segmentedControl",
        "textField",
    }
    actual = component_members(flat, "component.")
    require(
        actual == expected,
        f"[{label}] update contrast recipe coverage for components {sorted(actual ^ expected)}",
    )
    semantic = semantic_pairs(flat)
    pairs = semantic + component_pairs(flat)
    covered = {path for fg, bg, _, _ in pairs for path in (fg, bg)}
    for path, node in flat.items():
        if path.startswith(
            ("color.text.", "color.icon.", "color.interactive.tint.")
        ) and not path.endswith(".disabled"):
            require(
                path in covered, f"[{label}] add a declared contrast check for {path}"
            )
        if (
            path.startswith("component.")
            and node["$type"] == "color"
            and not disabled_path(path)
        ):
            if path.endswith(".color") and any(
                f".parts.{part}." in path
                for part in (
                    "label",
                    "input",
                    "placeholder",
                    "helper",
                    "counter",
                    "icon",
                    "leadingIcon",
                    "trailingIcon",
                    "chevron",
                )
            ):
                require(
                    path in covered,
                    f"[{label}] add a component contrast check for {path}",
                )
    for foreground, background, minimum, backdrop in pairs:
        for path in (foreground, background, backdrop):
            if path is not None:
                require(
                    path in resolved,
                    f"[{label}] contrast pair references missing token {path}",
                )
        foreground_value, background_value = resolved[foreground], resolved[background]
        container_opacity, ink_opacity = component_opacity(
            foreground, resolved, background
        )
        if ink_opacity != 1:
            foreground_value = {
                **foreground_value,
                "alpha": foreground_value.get("alpha", 1) * ink_opacity,
            }
        if container_opacity != 1:
            # Whole-element opacity composites the finished local recipe over the host.
            # A missing host must not silently be treated as white or black.
            require(
                backdrop is not None,
                f"[{label}] {foreground}: dimmed recipe needs a declared backdrop",
            )
            host = resolved[backdrop]
            require(
                host.get("alpha", 1) == 1, f"[{label}] opacity backdrop must be opaque"
            )
            bg_alpha = background_value.get("alpha", 1)
            bg_rgb = [
                a * bg_alpha + b * (1 - bg_alpha)
                for a, b in zip(background_value["components"], host["components"])
            ]
            fg_alpha = foreground_value.get("alpha", 1)
            ink_rgb = [
                a * fg_alpha + b * (1 - fg_alpha)
                for a, b in zip(foreground_value["components"], bg_rgb)
            ]
            foreground_value = {
                "components": [
                    a * container_opacity + b * (1 - container_opacity)
                    for a, b in zip(ink_rgb, host["components"])
                ]
            }
            background_value = {
                "components": [
                    a * container_opacity + b * (1 - container_opacity)
                    for a, b in zip(bg_rgb, host["components"])
                ]
            }
        measured = contrast_ratio(
            foreground_value, background_value, resolved.get(backdrop)
        )
        if high_contrast and minimum == 4.5:
            # High-contrast themes owe enhanced text contrast (WCAG 1.4.6).
            minimum = 7
        require(
            measured >= minimum,
            f"[{label}] contrast {foreground} / {background}: {measured:.6f}:1 < {minimum}:1",
        )
    return len(pairs)


def validate_documents(documents: dict) -> dict:
    require("default.resolver.json" in documents, "default.resolver.json missing")
    for name, document in documents.items():
        if name.endswith(".resolver.json"):
            check_resolver(documents, name, document)
    check_token_shapes(documents)
    check_platforms(documents)
    check_components(documents)
    check_material_ownership(documents)
    report = {"contexts": 0, "contrast_checks": 0}
    for name, resolver in documents.items():
        if not name.endswith(".resolver.json"):
            continue
        check_theme_roots(documents, resolver)
        check_theme_parity(documents, resolver)
        check_state_bindings(documents, resolver)
        check_sanctioned_aliases(documents, resolver)
        check_appearance_deltas(documents, resolver)
        axes = sorted(resolver["modifiers"])
        for combination in itertools.product(
            *(resolver["modifiers"][axis]["contexts"] for axis in axes)
        ):
            choices = dict(zip(axes, combination))
            label = (
                name + ":" + ",".join(f"{key}={val}" for key, val in choices.items())
            )
            flat = compose_context(documents, resolver, choices)
            resolved = resolve_values(flat, label)
            check_resolved_metrics(flat, resolved, label)
            report["contrast_checks"] += check_contrast(
                flat, resolved, label, "high-contrast" in choices["theme"]
            )
            report["contexts"] += 1
    return report


def validate(root: Path) -> dict:
    return validate_documents(load_documents(root))


if __name__ == "__main__":
    repository = Path(__file__).resolve().parent.parent
    try:
        report = validate(repository / "tokens")
    except ValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    print(
        f"tokens/ valid — {report['contexts']} contexts, {report['contrast_checks']} contrast checks"
    )
