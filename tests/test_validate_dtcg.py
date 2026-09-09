"""Mutation tests use in-memory copies; the authored token files are never changed."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import validate_dtcg as gate

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = gate.load_documents(ROOT / "tokens")

    def setUp(self):
        self.docs = copy.deepcopy(self.original)

    def node(self, file, path):
        node = self.docs[file]
        for key in path.split("."):
            node = node[key]
        return node

    def rejects(self, message):
        with self.assertRaisesRegex(gate.ValidationError, message):
            gate.validate_documents(self.docs)

    def test_repository_and_advisories(self):
        report = gate.validate_documents(self.docs)
        self.assertEqual(report["contexts"], 16)
        self.assertEqual(report["contrast_checks"], 7840)
        self.assertTrue(report["advisories"])
        self.assertEqual(self.docs, self.original)

    def test_cli_is_independent_of_working_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/validate_dtcg.py")],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("7840 contrast checks", result.stdout)

    def test_schema_version_cannot_bypass_component_gates(self):
        del self.node("component/button.tokens.json", "component.button.$extensions")[
            "com.designsystem"
        ]["schemaVersion"]
        self.rejects("schemaVersion")

    def test_unsupported_schema_version(self):
        for version in (0, 2, "1", True):
            with self.subTest(version=version):
                self.node(
                    "component/button.tokens.json", "component.button.$extensions"
                )["com.designsystem"]["schemaVersion"] = version
                self.rejects("schemaVersion 1 required")

    def test_component_namespace_matches_file(self):
        component = self.docs["component/button.tokens.json"]["component"]
        component["renamed"] = component.pop("button")
        self.rejects("namespace/file-name")

    def test_missing_state_leaf(self):
        del self.node(
            "component/button.tokens.json",
            "component.button.variant.primary.state.pressed.parts.label",
        )["color"]
        self.rejects("incomplete family")

    def test_missing_size_leaf(self):
        del self.node(
            "component/avatar.tokens.json", "component.avatar.size.small.parts.initials"
        )["typography"]
        self.rejects("incomplete family")

    def test_root_variant_duplicate_owner(self):
        button = self.node("component/button.tokens.json", "component.button")
        button.setdefault("parts", {}).setdefault("label", {})["color"] = {
            "$type": "color",
            "$value": "{color.text.primary}",
        }
        self.rejects("duplicate root/variant")

    def test_size_state_duplicate_owner(self):
        button = self.node("component/button.tokens.json", "component.button")
        for size in gate.members(button["size"]).values():
            size["parts"].setdefault("label", {})["color"] = {
                "$type": "color",
                "$value": "{color.text.primary}",
            }
        self.rejects("duplicate root/variant")

    def test_structural_variants_are_locally_complete(self):
        gate.check_components(self.docs)
        del self.node(
            "component/progress.tokens.json",
            "component.progress.variant.circular.size.small.parts.track",
        )["thickness"]
        self.rejects("incomplete family")

    def test_structural_shape_is_not_valid_as_intent(self):
        del self.node(
            "component/progress.tokens.json", "component.progress.$extensions"
        )["com.designsystem"]["variantKind"]
        self.rejects("intent variant shape")

    def test_invalid_property_vocabulary(self):
        node = self.node("component/card.tokens.json", "component.card.parts.container")
        node["bg"] = node.pop("background")
        self.rejects("unregistered property")

    def test_nested_variability_axis(self):
        state = self.node(
            "component/button.tokens.json",
            "component.button.variant.primary.state.default",
        )
        state["size"] = {"small": {"parts": {}}}
        self.rejects("invalid family nesting")

    def test_selection_matrix_gap(self):
        del self.node(
            "component/segmented-control.tokens.json",
            "component.segmentedControl.state.disabled.selection",
        )["unselected"]
        self.rejects("incomplete selection matrix")

    def test_declared_unsupported_selection_is_allowed(self):
        component = self.node(
            "component/segmented-control.tokens.json", "component.segmentedControl"
        )
        del component["state"]["disabled"]["selection"]["unselected"]
        component["$extensions"]["com.designsystem"]["unsupportedCombinations"] = [
            {"state": "disabled", "selection": "unselected"}
        ]
        gate.validate_documents(self.docs)

    def test_hover_must_match_default(self):
        states = self.node(
            "component/button.tokens.json", "component.button.variant.primary.state"
        )
        states["hover"] = copy.deepcopy(states["pressed"])
        self.rejects("hover must equal default")

    def test_invalid_compound_state_order(self):
        states = self.node(
            "component/text-field.tokens.json", "component.textField.state"
        )
        states["errorFocused"] = states.pop("focusedError")
        self.rejects("compound-state order")

    def test_compound_state_third_value(self):
        leaf = self.node(
            "component/text-field.tokens.json",
            "component.textField.state.focusedError.parts.label.color",
        )
        leaf["$value"] = "{color.text.warning}"
        self.rejects("third value")

    def test_double_dimming(self):
        states = self.node(
            "component/button.tokens.json", "component.button.variant.primary.state"
        )
        for state, snapshot in states.items():
            snapshot["parts"]["container"]["opacity"] = {
                "$type": "number",
                "$value": "{opacity.disabled}" if state == "disabled" else 1,
            }
        self.rejects("double dimming")

    def test_dimension_cannot_be_string(self):
        self.node("primitive/spacing.tokens.json", "primitive.spacing.4")["$value"] = (
            "not-a-dimension"
        )
        self.rejects("invalid dimension")

    def test_number_cannot_be_boolean(self):
        self.node("semantic/opacity.tokens.json", "opacity.disabled")["$value"] = True
        self.rejects("invalid number")

    def test_opacity_range(self):
        self.node("semantic/opacity.tokens.json", "opacity.disabled")["$value"] = 1.5
        self.rejects("opacity outside")

    def test_dash_requires_pair(self):
        del self.node(
            "component/avatar.tokens.json",
            "component.avatar.variant.add.parts.container",
        )["dashGap"]
        self.rejects("dash geometry")

    def test_dash_mixed_solid_and_dashed(self):
        self.node(
            "component/avatar.tokens.json",
            "component.avatar.variant.add.parts.container.dashGap",
        )["$value"]["value"] = 0
        self.rejects("invalid dash geometry")

    def test_nested_missing_reference(self):
        self.node("primitive/typography.tokens.json", "primitive.typography.body")[
            "$value"
        ]["fontFamily"] = "{primitive.fontFamily.missing}"
        self.rejects("missing token primitive.fontFamily.missing")

    def test_nested_reference_type(self):
        self.node("primitive/typography.tokens.json", "primitive.typography.body")[
            "$value"
        ]["fontSize"] = "{primitive.fontWeight.regular}"
        self.rejects("alias type mismatch")

    def test_nested_cycle(self):
        flat = {"a": {"$type": "shadow", "$value": "{a}"}}
        with self.assertRaisesRegex(gate.ValidationError, "alias cycle"):
            gate.resolve_values(flat, "test")

    def test_component_alias_forbidden(self):
        self.node(
            "component/card.tokens.json", "component.card.parts.container.background"
        )["$value"] = "{component.avatar.parts.emoji.background}"
        self.rejects("component colors must alias")

    def test_component_alias_in_nested_composite(self):
        self.node("primitive/typography.tokens.json", "primitive.typography.body")[
            "$value"
        ]["fontFamily"] = "{component.card.parts.container.background}"
        self.rejects("component alias target")

    def test_bad_resolution_order(self):
        self.docs["default.resolver.json"]["resolutionOrder"].reverse()
        self.rejects("resolutionOrder")

    def test_missing_resolver_source(self):
        self.docs["android.resolver.json"]["sets"]["primitive"]["sources"].append(
            {"$ref": "primitive/missing.tokens.json"}
        )
        self.rejects("missing token source")

    def test_invalid_modifier_default(self):
        self.docs["default.resolver.json"]["modifiers"]["theme"]["default"] = "missing"
        self.rejects("default context missing")

    def test_android_nested_reference(self):
        self.node(
            "platform/android/primitive/font-family.tokens.json",
            "primitive.fontFamily.text",
        )["$value"] = "{primitive.fontFamily.missing}"
        self.rejects("missing token primitive.fontFamily.missing")

    def test_redundant_android_override(self):
        leaf = self.node(
            "platform/android/primitive/font-family.tokens.json",
            "primitive.fontFamily.text",
        )
        leaf["$value"] = self.node(
            "primitive/font-family.tokens.json", "primitive.fontFamily.text"
        )["$value"]
        self.rejects("must differ from base")

    def test_android_new_path(self):
        group = self.node(
            "platform/android/primitive/font-family.tokens.json", "primitive.fontFamily"
        )
        group["newFont"] = copy.deepcopy(group["text"])
        self.rejects("new override path")

    def test_android_metadata_change(self):
        self.node(
            "platform/android/primitive/font-family.tokens.json", "primitive.fontFamily"
        )["$extensions"] = {"taxonomy": {"changed": True}}
        self.rejects("override changes metadata")

    def test_android_wrong_theme_cell(self):
        sources = self.docs["android.resolver.json"]["modifiers"]["theme"]["contexts"][
            "light"
        ]
        sources.append({"$ref": "platform/android/theme/dark/elevation.tokens.json"})
        self.rejects("does not mirror this composition cell")

    def test_android_missing_base_component(self):
        self.docs["android.resolver.json"]["sets"]["component"]["sources"].pop()
        self.rejects("preserve base source order")

    def test_appearance_new_path(self):
        part = self.node(
            "appearance/pill/segmented-control.tokens.json",
            "component.segmentedControl.parts.container",
        )
        part["width"] = {"$type": "dimension", "$value": {"unit": "px", "value": 30}}
        self.rejects("new override path")

    def test_appearance_cannot_change_shape_metadata(self):
        self.node(
            "appearance/pill/segmented-control.tokens.json",
            "component.segmentedControl",
        )["$extensions"] = {
            "com.designsystem": {"schemaVersion": 1, "variantKind": "structural"}
        }
        self.rejects("override changes metadata")

    def test_malformed_extensions_fail_cleanly(self):
        self.node("component/card.tokens.json", "component.card")["$extensions"] = []
        self.rejects("namespace objects")

    def test_leaf_envelope_location(self):
        self.node(
            "component/card.tokens.json", "component.card.parts.container.background"
        )["$extensions"] = {"com.designsystem": {"schemaVersion": 1}}
        self.rejects("illegal level")

    def test_transparent_appearance_uses_host(self):
        self.node(
            "appearance/pill/segmented-control.tokens.json",
            "component.segmentedControl.parts.container.background",
        )["$value"] = "{color.surface.inverse}"
        self.rejects("contrast component.segmentedControl")

    def test_enabled_container_opacity_is_measured(self):
        button = self.node("component/button.tokens.json", "component.button")
        container = button.setdefault("parts", {}).setdefault("container", {})
        container["opacity"] = {"$type": "number", "$value": 0.1}
        self.rejects("contrast component.button")

    def test_nested_shadow_field_type(self):
        leaf = self.node("theme/light/elevation.tokens.json", "elevation.raised.shadow")
        leaf["$value"]["blur"] = "{primitive.fontWeight.regular}"
        self.rejects("alias type mismatch")

    def test_android_whole_composite_override(self):
        source = "platform/android/primitive/typography.tokens.json"
        node = copy.deepcopy(
            self.node("primitive/typography.tokens.json", "primitive.typography.body")
        )
        node["$value"]["lineHeight"] = 2
        self.docs[source] = {"primitive": {"typography": {"body": node}}}
        self.docs["android.resolver.json"]["sets"]["primitive"]["sources"].append(
            {"$ref": source}
        )
        self.rejects("composite override forbidden")

    def test_resolver_composition_propagates_nested_android_override(self):
        resolver = self.docs["android.resolver.json"]
        flat = gate.compose_context(
            self.docs, resolver, {"theme": "light", "appearance": "contained"}
        )
        resolved = gate.resolve_values(flat, "android")
        self.assertEqual(resolved["typography.body.large"]["fontFamily"], "Roboto")

    def test_unreferenced_file(self):
        self.docs["primitive/unused.tokens.json"] = {
            "primitive": {"unused": {"$type": "number", "$value": 1}}
        }
        self.rejects("unreferenced token files")

    def test_theme_type_parity(self):
        leaf = self.node("theme/light/color.tokens.json", "color.text.placeholder")
        leaf["$type"] = "dimension"
        leaf["$value"] = {"unit": "px", "value": 10}
        self.rejects("path/type parity")

    def test_required_contrast_failure(self):
        self.node("theme/light/color.tokens.json", "color.text.placeholder")[
            "$value"
        ] = "{primitive.color.neutral.500}"
        self.rejects("contrast color.text.placeholder")

    def test_component_pair_uses_actual_references(self):
        self.node(
            "component/badge.tokens.json",
            "component.badge.variant.warning.parts.label.color",
        )["$value"] = "{color.text.primary}"
        self.rejects("contrast component.badge.variant.warning")

    def test_new_identity_entry_gets_contrast_check(self):
        for file in self.docs:
            if file.startswith("theme/") and file.endswith("color.tokens.json"):
                palette = self.docs[file]["color"]["identity"]
                palette["9"] = copy.deepcopy(palette["0"])
                palette["9"]["ink"]["$value"] = palette["9"]["background"]["$value"]
        self.rejects("contrast color.identity.9.ink")

    def test_new_text_role_needs_contrast_coverage(self):
        for file in self.docs:
            if file.startswith("theme/") and file.endswith("color.tokens.json"):
                group = self.docs[file]["color"]["text"]
                group["newRole"] = copy.deepcopy(group["primary"])
        self.rejects("add a declared contrast check")

    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            json.loads(
                '{"x": 1, "x": 2}', object_pairs_hook=gate._reject_duplicate_keys
            )

    def test_component_typography_requires_semantic_alias(self):
        sizes = self.node("component/avatar.tokens.json", "component.avatar.size")
        for value in (
            "{primitive.typography.body}",
            {
                "fontFamily": "Arial",
                "fontSize": {"value": 12, "unit": "px"},
                "fontWeight": 400,
                "letterSpacing": {"value": 0, "unit": "px"},
                "lineHeight": 1.5,
            },
        ):
            with self.subTest(value=value):
                for size in gate.members(sizes).values():
                    size["parts"]["initials"]["typography"]["$value"] = value
                self.rejects("component typography must alias semantic roles")

    def test_nested_parent_opacity_affects_contrast(self):
        self.node(
            "component/segmented-control.tokens.json",
            "component.segmentedControl.parts.segment",
        )["opacity"] = {"$type": "number", "$value": "{opacity.loading}"}
        self.rejects("contrast component.segmentedControl")

    def test_non_finite_json(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            json.loads('{"x": NaN}', parse_constant=gate._reject_constant)


class ContrastMathTests(unittest.TestCase):
    def test_nested_opacity_inherited_from_root_scope(self):
        path = "component.example.state.default.parts.segment.parts.label.color"
        resolved = {"component.example.parts.segment.opacity": 0.6}
        self.assertEqual(gate.component_opacity(path, resolved), (1, 0.6))

    def test_shared_nested_opacity_fails_closed(self):
        path = "component.example.parts.segment.parts.label.color"
        resolved = {"component.example.parts.segment.opacity": 0.6}
        with self.assertRaisesRegex(gate.ValidationError, "explicit contrast recipe"):
            gate.component_opacity(
                path, resolved, "component.example.parts.segment.background"
            )

    def color(self, gray, alpha=1):
        return {"colorSpace": "srgb", "components": [gray] * 3, "alpha": alpha}

    def test_black_white(self):
        self.assertEqual(gate.contrast_ratio(self.color(0), self.color(1)), 21)

    def test_equal_colors(self):
        self.assertEqual(gate.contrast_ratio(self.color(0.4), self.color(0.4)), 1)

    def test_alpha_foreground(self):
        self.assertAlmostEqual(
            gate.contrast_ratio(self.color(0, 0.5), self.color(1)), 3.9766530249
        )

    def test_alpha_background(self):
        self.assertAlmostEqual(
            gate.contrast_ratio(self.color(0), self.color(0, 0.5), self.color(1)),
            gate.contrast_ratio(self.color(0), self.color(0.5)),
        )

    def test_missing_backdrop_fails(self):
        with self.assertRaisesRegex(gate.ValidationError, "explicit opaque backdrop"):
            gate.contrast_ratio(self.color(0), self.color(1, 0.5))

    def test_no_rounding_to_pass(self):
        luminance = 1.05 / 4.4999 - 0.05
        gray = 1.055 * luminance ** (1 / 2.4) - 0.055
        ratio = gate.contrast_ratio(self.color(gray), self.color(1))
        self.assertEqual(round(ratio, 2), 4.5)
        self.assertLess(ratio, 4.5)


if __name__ == "__main__":
    unittest.main()
