# dtcg-token-architecture

Reference architecture for design tokens in the [DTCG 2025.10](https://www.designtokens.org/) format.
The token files provide concrete examples; the contracts define their structure,
allowed changes, and conditions for extending it.

Start with the tier and axis model below. Use the change guide to find the contract
that governs an edit. A new value or component follows the existing rules; a new
category, vocabulary entry, or unsupported structural pattern requires the relevant
contract to define its placement and invariants together with its first use.

## Idea

The tree separates foundations, shared decisions, and component anatomy:

- **primitive** — neutral scales and addressable foundation values, named by magnitude,
  ramp position, or foundation identity.
- **semantic** — usage roles; static categories live in `semantic/`, and mode-dependent
  categories live in `theme/<context>/`.
- **component** — per-component anatomy and owned surfaces for variants, sizes,
  layouts, and states. Leaves reference semantic roles, with the primitive and
  literal exceptions defined in the [component contract §5](docs/component-token-contract.md#5-reference-discipline).

Theme, appearance, and platform select values on these shared token paths:

| Axis | Kind | Contexts here |
|---|---|---|
| theme | runtime | light, dark, light-high-contrast, dark-high-contrast |
| appearance | runtime | contained (default), pill |
| platform | compile-time | default, android (separate resolver) |

Themes declare complete color and elevation sets with matching paths across modes.
Appearance and platform files contain only overrides. Component states are complete
snapshots of the state-owned surface, not sparse overrides.

[`default.resolver.json`](tokens/default.resolver.json) declares the base composition.
[`android.resolver.json`](tokens/android.resolver.json) preserves that composition and
adds Android overrides. Each resolver selects one theme and one appearance context.
A theme-specific platform override applies only in its matching theme context.

Composition is explicit: a file participates only when the selected resolver
references it. Both resolvers include all seven component examples: `avatar`,
`badge`, `button`, `card`, `progress`, `segmentedControl`, and `textField`. Adding
a component file requires registering it in both resolvers to include it in the
resolved composition.

## Layout

```
tokens/
  default.resolver.json — base sets + modifiers (theme, appearance)
  android.resolver.json — platform overlay resolver
  primitive/ — tier 1
  semantic/ — tier 2, static roles
  theme/<context>/ — tier 2, mode-dependent roles (color, elevation)
  appearance/<context>/ — sparse appearance overrides
  platform/<name>/ — sparse platform overrides
  component/ — tier 3, one file per component
docs/
  primitive-token-contract.md — foundations, naming, value shapes
  semantic-token-contract.md — role grammar, static vs themed, alias rules
  component-token-contract.md — anatomy, axes, reference rules
  platform-contract.md — platform overrides and resolver composition
  contrast-contract.md — acceptance policy for resolved color pairs
scripts/
  validate_dtcg.py — structural validation
```

## How to change the tree

Paths below are relative to `tokens/`. The linked contracts define the full rules.

| Intended change | Where and how | Rules to preserve |
|---|---|---|
| Add a foundation value | Add it to the matching `primitive/` category after applying the menu/addressability tests. | [Primitive §2, §6](docs/primitive-token-contract.md): no usage intent; metric keys continue to equal their values. |
| Add or retarget a shared role | Use `semantic/` for a static category or every theme set for a dynamic category. | [Semantic §2–5](docs/semantic-token-contract.md): instruction-backed intent, matching paths and types, allowed references. |
| Add a component | Add one `component/<name>.tokens.json` file; register it in the base and platform resolvers when including it in their composition. | [Component §1–7](docs/component-token-contract.md): namespace, envelope, anatomy, ownership, reference discipline. |
| Change a component's recipe | Edit values or references on the existing shape. | [Component §5, §8](docs/component-token-contract.md): preserve meaning, types, ownership, and complete family surfaces. |
| Add a size, layout, state, or variant | Use the axis that describes why the values differ; declare its complete owned surface. | [Component §2–3](docs/component-token-contract.md): single ownership, family completeness, and the distinction between intent and structural variants. |
| Keep an additional appearance recipe | Add sparse files under `appearance/<name>/` and an appearance context in each resolver. | [Component §9](docs/component-token-contract.md#9-extension-rules): existing paths and types, differing values, alias-only colors, empty default context. |
| Add a theme | Add its complete dynamic categories and register the context in each resolver. | [Semantic §3](docs/semantic-token-contract.md#3-files-and-namespace) and [contrast contract](docs/contrast-contract.md): path/type parity and declared contrast obligations. |
| Add a platform difference | Mirror the base file under `platform/<name>/` and include it after the base source in that platform's resolver. | [Platform §3–5](docs/platform-contract.md): sparse value-only overrides; theme-specific sources stay in their matching context. |
| Extend a closed vocabulary or introduce a new structure | Define the need, placement, naming, types, and conformance criteria in the owning contract together with the first use. | [Primitive §4](docs/primitive-token-contract.md#4-category-roster), [semantic §4](docs/semantic-token-contract.md#4-category-roster), or [component §9](docs/component-token-contract.md#9-extension-rules). Existing invariants remain binding unless explicitly revised. |

For each change, follow its references to identify the affected components, themes,
appearances, and platforms. Review those combinations against the contracts. A shared
value edit can affect many components even when their files do not change.

## Validate

```
python3 scripts/validate_dtcg.py
python3 -m unittest discover -s tests -v
```

Both commands use only the Python standard library (Python 3.12+). The existing
validator checks every resolver and theme × appearance context, including mirrored
platform overrides, nested typed aliases, value shapes, component ownership,
family completeness, selection, state grammar, and material/appearance rules.
Required contrast minima fail validation. In high-contrast themes the text minimum
is the enhanced 7:1 target. Pair checks are explicit code derived from token usage descriptions,
not a parser for `$description`. Extend recipe/pair coverage alongside new usage.

Tests mutate in-memory copies to verify rejection of invalid tokens without changing
the authored files. GitHub Actions runs both commands on pushes and pull requests.

This is a repository-contract gate, not a complete DTCG implementation or official
JSON Schema validator. Its supported profile uses explicit leaf types, brace aliases,
sRGB colors, and the current theme/appearance axes. New color spaces or resolver axes
need corresponding gate support. Human review still owns role intent, description
accuracy, structural-variant justification, recipe coherence, and rendered
accessibility (including selection cues, focus geometry, and materials). Passing
numeric contrast checks alone does not establish WCAG conformance.

## License

MIT. Copyright (c) 2026 Yevhenii Kalashnikov. See [LICENSE](LICENSE).
