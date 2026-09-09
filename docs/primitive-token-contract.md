# Primitive Token Contract

The structure and rules for the primitive tier of the token tree: what may
live here, how files are organized, how keys are named, what shape values
take. The contract defines the form — the concrete foundation contents live
in the token files themselves.

Normative words: **MUST** (contract requirement), **SHOULD** (deviation
needs a reason), **MAY** (allowed). Unless explicitly attributed to
DTCG 2025.10, they define this token system's architecture contract, not
requirements of the DTCG 2025.10 specification.

Core token paths, categories and value contracts are platform-neutral.
Platform-specific metadata lives only in namespaced `$extensions` (§5) and
MUST NOT change the shared taxonomy.

## 1. The formula

```
primitive.{category}.{key}

metric   → key IS the authored magnitude:
           spacing.8 = 8 · borderWidth.0_5 = 0.5 · spacing.negative.4 = -4
           one named exception: cornerRadius.full (pill)
ordinal  → color.{hue}.{step}: step = rank on the lightness ramp,
           not a measurement · plus color.brand.{role} and color.transparent
named    → fontFamily / fontWeight / typography / letterSpacing: full
           descriptive words, no abbreviations, no t-shirt sizes
```

For menu-path categories: if the category is measured in design units —
the key is the value; if the value belongs to an ordered ramp — the key is
its ordinal position; if it is a named composite or family choice — the
key is a descriptive name. Addressability-path categories use named keys
mirroring their foundation source table (§2, §6) — never by-value keys.
If the token encodes a decision, not a magnitude — it is a role and lives
above this tier.

```
valid: primitive.spacing.8
invalid: primitive.spacing.cardPadding

valid: primitive.borderWidth.0_5
invalid: primitive.borderWidth.hairline

valid: primitive.color.brand.primary
invalid: primitive.color.button.primary

valid: primitive.typography.body
invalid: primitive.typography.primaryText
```

## 2. The principle

**A primitive is a neutral, reusable, mode-independent foundation fact
with no usage intent.** A primitive carries no intent: `spacing.8` says
"8 exists", never "use this for card padding". The moment a value is
*assigned* — to a role, a state, a mode — that assignment is a decision,
and decisions live above the primitive tier.

A value enters the tier through one of two paths:

- **Menu path** — the value belongs to a real neutral menu or scale that
  designers genuinely choose from (`spacing`, `color`, `fontWeight`, …).
- **Addressability path** — the value is a neutral field of a foundation
  composite, not a browsable menu entry, but it MUST have its own address
  because a supported platform overrides it independently and the DTCG
  representation cannot override a sub-field of a token (whole-token
  merge, platform contract §3).

The addressability path is open only when **all** of these hold:

* a real supported-platform consumer exists — never a speculative future;
* the value is a neutral foundation fact with no usage or component
  intent;
* the platform variance concerns the foundation fact itself;
* the existing DTCG representation cannot address the field
  independently;
* the extraction does not change the semantic taxonomy;
* the extraction preserves resolved output **bit-for-bit** for every
  existing target — it is an addressing refactor, never a redesign (a
  verifiable gate).

If any condition fails, the field stays inline in its composite.
Addressability-token keys mirror the **stable logical grouping of the
foundation source table** — never the structure of a particular consumer,
so the primitive taxonomy cannot inherit an unstable consumer shape. They
MUST NOT encode component or usage intent. One token represents one
independently addressable value row.

Three tests, applied in order, decide whether a value belongs here:

1. **Menu/addressability test** — does the value either belong to a
   neutral foundation menu, or require independent addressability because
   a supported platform varies this foundation fact independently? If
   neither is true, it does not belong in primitives. A scale nobody
   browses and no platform varies is a role table wearing a scale
   costume.
2. **Assignment test** — does the token name state *what it is* (fact) or
   *what it is for* (role)? `borderWidth.0_5` is a fact; `hairline`,
   `disabled`, `raised`, `control` — roles. Role words MUST NOT appear in
   primitive keys.
3. **Mode test** — does the value need to differ per theme/mode (Light/Dark,
   HighContrast)? Primitives are mode-invariant by construction; anything
   mode-dependent MUST live in the theme sets.

Addressability replaces only the browsable-menu requirement; it never
bypasses the assignment or mode tests. The invariant:
**addressability may promote a neutral fact into the primitive tier; it
can never promote a decision.**

Failing a test excludes the value from the primitive tier — it does not
automatically make it semantic. Reusable role decisions live in `semantic/`;
mode-dependent decisions live in `theme/`; a component-specific decision
lives inline in the component file; a composite's sub-values stay inline in
their composite token until the addressability path opens for them.

## 3. Files and namespace

- **One file per category**: `primitive/<category>.tokens.json`, DTCG 2025.10
  format, kebab-case file name matching the camelCase category
  (`cornerRadius` → `corner-radius.tokens.json`). File = category =
  independent foundation domain.
- **Namespace `primitive.*`** — the root key of every primitive file
  (`{ "primitive": { "spacing": { … } } }`). The component tier is likewise
  prefixed (`component.*`, component contract §1); only semantic and theme
  sets publish into the bare namespace (`spacing.*`, `color.*`,
  `elevation.*`) — they are the consumer-facing API. The prefix resolves a
  real collision: `primitive.typography.body` is a token while
  `typography.body.*` is a semantic group — on one unprefixed path a token
  and a group would collide.
- **Resolution order**: `primitive` → `semantic` → theme modifier →
  `component`. Primitives resolve first and never reference anything above
  them; the only references inside the tier are the declared composite
  fields (typography → fontFamily, fontWeight, letterSpacing).
- **Mode-invariant**: one value per token within the base primitive set,
  no per-theme variants, ever (mode test, §2) — no theme or contrast
  context may alter a primitive value. The default brand is authored in
  the base primitive set. If multiple brands require different foundation
  values, a brand modifier MAY override the same primitive paths through
  brand-specific resolver contexts before theme resolution — identical
  paths, never a fork of the taxonomy. Platform variance (fonts, metrics)
  is likewise legal on identical primitive
  paths as build-time sparse overrides per the
  [platform contract](platform-contract.md) — mode-invariance restricts
  theme and contrast contexts only.

## 4. Category roster

The roster is a **closed allowlist**. Exactly nine categories:

| Category | `$type` | Key shape |
|---|---|---|
| `spacing` | `dimension` | by-value numeric |
| `sizing` | `dimension` | by-value numeric, flat — no `control.*`, no `icon.*` |
| `cornerRadius` | `dimension` | by-value numeric + named `full` |
| `borderWidth` | `dimension` | by-value numeric |
| `color` | `color` | ordinal `hue.step` ramps + `brand.{role}` + `transparent` |
| `fontFamily` | `fontFamily` | named menu |
| `fontWeight` | `fontWeight` | named menu — named keys mapping to numeric weight facts |
| `typography` | `typography` | named menu of platform text-style composites |
| `letterSpacing` | `dimension` | named per text-style size group — addressable foundation (§2), not a menu; see below |

Explicitly **not** in the roster (and MUST NOT be authored):

- `opacity` — fails the assignment test: authored opacity values in this
  system are always usage decisions (`disabled`, `pressed`), never neutral
  facts. No entry path can admit a decision (§2 invariant). Roles live in
  `semantic/` with inline values — there is no scale to reference.
- `boxShadow` — fails the mode test: shadows are elevation policy, alpha and
  color differ between Light and Dark. Intent-named roles
  (`elevation.{none raised overlay modal}`) live in the theme sets, one full
  role set per mode. Dark values are a deliberate design decision, not a
  copy of Light. The explicit `elevation.none` is the typed absence — "no
  shadow" is never expressed by omitting a leaf.
- `fontSize` / `lineHeight` — fail the menu/addressability test on both
  branches: not menus (hard-linked rows of the typography table, and a
  menu without choice is not a menu) and no supported platform varies
  them (line-height ratios are the brand's vertical rhythm, shared across
  platforms by design). They live inline in the typography composites
  (§7) until a real platform variance opens the addressability path —
  symmetry with `letterSpacing` alone never does.

`letterSpacing` illustrates the **addressability path** (§2). Typography
composites reference the named tracking values, and
`platform/android/primitive/letter-spacing.tokens.json` overrides those
values independently of the other composite fields. Keys mirror the
stable size groups of the foundation typography table (`body`, `title1`,
…), one token per distinct tracking row. Extracting another composite
field MUST satisfy all six §2 conditions, including unchanged resolved
output for existing targets.

A new category enters the roster only through an explicit architecture
decision that fixes, before any token lands: a real consumer, the tier
classification (primitive menu / primitive addressable foundation /
semantic role / theme role / component-local), the DTCG 2025.10
representation, and the key shape — never as a side effect of a component
needing a value.

## 5. Value shapes

| `$type` | `$value` shape |
|---|---|
| `dimension` | `{ "value": 8, "unit": "px" }` — key parses to `value` in metric categories (`0_5` → 0.5, `negative.4` → -4) |
| `color` | `{ "colorSpace": "srgb", "components": [r, g, b], "alpha": 1, "hex": "#…" }` — components in `0…1`; `transparent` is `alpha: 0` |
| `fontFamily` | font name string |
| `fontWeight` | number `100…900` |
| `typography` | composite: `fontFamily`, `fontWeight` and `letterSpacing` are references (`{primitive.fontFamily.text}`, `{primitive.letterSpacing.body}`), `fontSize` is a `px` dimension, `lineHeight` is a unitless ratio (number) |

- **Canonical unit vs transport unit**: metric keys encode the canonical
  design-unit magnitude; source files use DTCG 2025.10 `px` as the
  transport unit. Platform translators map the canonical unit to their
  native representation (`pt`, `dp`, CSS `px`).
- `cornerRadius.full` transports the `9999` sentinel (DTCG 2025.10
  `dimension` requires a number); renderers clamp it to half the element's
  smaller dimension. The sentinel lives only in the value, never as a key.
- **Platform metadata lives in namespaced `$extensions`** and never changes
  token paths, types or value shapes. Every typography composite MUST
  declare `$extensions."com.apple.swift".textStyle` — its Dynamic Type
  anchor — plus `weight` when the style is a weight variant of its
  anchor; styles without a direct platform
  counterpart anchor to the nearest style. Additional platform metadata
  MAY use its own namespace without touching the shared taxonomy.

## 6. Naming rules

- **By-value metric keys**: `spacing.8` = 8; key and value MUST agree.
- **T-shirt sizes (`xs`/`sm`/`md`/`lg`) are forbidden everywhere in the
  primitive tier.** They rank entries relative to each other, which breaks
  the moment the scale grows a new middle entry, and the ladder runs out of
  names at the ends. Full size words belong to closed axes such as
  `component.button.size.small/medium/large`, where they name choices
  within a component rather than primitive scale entries.
- **Decoupled ordinals for metrics (`spacing.100/200/…`) are forbidden.**
  Their purpose is to detach name from value so values can be re-based
  later. Metric primitive identities are value-locked — a redesign changes
  semantic aliases, never the value behind `primitive.spacing.16` — so the
  indirection buys nothing. Position ordinals hide the authored
  measurement; by-value keys keep exposing the exact authored magnitude,
  while aliases and semantic roles absorb redesign decisions.
- **Fractional values** use an underscore: `borderWidth.0_5` = 0.5.
  Canonical spelling only — `0_5`, never `0_50`.
- **Negative values** nest under `negative`: `spacing.negative.4` = -4.
- **`cornerRadius.full`** is the one legitimate named metric: its meaning is
  "as round as possible", not a measurement.
- **Color steps are ordinals**: ranks on a lightness ramp, not measurements,
  so by-value naming does not apply. Re-stepping a ramp changes values, not
  the naming scheme.
- **Named menus use full descriptive words**; abbreviations are forbidden.
- **Addressability-token keys** (§2) mirror the stable logical grouping of
  their foundation source table (`letterSpacing.body`, `.title1`), never a
  consumer's structure and never usage words.
- **`color.brand.*` is a deliberate, named exception to the assignment
  test** — a role-like name kept because the brand palette is an identity
  fact of the product. Multiple brand palettes use the same paths through
  a brand modifier (§3). This is not a precedent for other role names.
  Brand roles identify approved identity swatches only:
  `primary`/`secondary`/`tertiary` MUST
  NOT imply primary action, text hierarchy or any other UI usage — usage is
  assigned by semantic tokens referencing the swatches.
  `fontFamily`/`typography` platform names (`display`, `body`, …) are a
  separate named-menu case, not a second exception: descriptive names of a
  platform-scoped table, not role assignments.

## 7. Typography — two layers

- **`primitive.typography`** is the text-style menu of the active platform
  implementation: named composites with the size/lineHeight pair **inline**
  (one hard-linked table); `fontFamily` and `fontWeight` referenced because
  they genuinely combine (body regular / body semibold; text / rounded /
  mono); `letterSpacing` referenced because platforms override it (§4).
- **`semantic.typography`** (in `semantic/`) is the platform-neutral role
  scale — `display/heading/body/label/caption × large/medium/small` —
  referencing the primitive menu. Everything above the semantic tier
  references only the role scale, never the primitive menu directly.
- Two layers, not one: merging would collide platform style names with role
  names on a single path (`body` is both a text style and a role family).
- `fontFamily` encodes the optical-size facts in descriptions: `display`
  for large sizes, `text` below the optical threshold.

## 8. Color notes

- **Alpha is part of the color.** A translucent color effect (scrim,
  material tint, glass overlay) MUST be a color token with baked-in alpha,
  never an opaque color plus a separate opacity token. If a transparency
  ramp is ever needed, it enters the roster via the §4 process as
  transparent *colors* (`color.alpha.black.10`), not as opacity scalars.
- **`transparent` is a primitive color**: transparent black — sRGB
  components `[0, 0, 0]`, `alpha: 0` — a structural fact with no semantic
  role and no theme variance. Consumers MUST NOT assume all zero-alpha
  colors are interchangeable during interpolation.

## 9. Values, reserve, descriptions

- **Unused entries are legitimate.** A menu exists to be chosen from later;
  a `color.pink.300` with zero references today is reserve capacity, not
  debt. Prune only what fails the §2 tests, never for having no consumers.
- **Descriptions state facts only**: the numeric value, an optical
  threshold, a trade name, a platform table row. "Use for…" guidance is
  semantic knowledge and MUST NOT appear in a primitive description — the
  role tier carries it (`borderWidth.0_5` stays a bare fact; the hairline
  story lives on the semantic `borderWidth.hairline`). A description that
  names another token's key spells it exactly (`borderWidth.0_5`, not
  "hairline (0.5)").
