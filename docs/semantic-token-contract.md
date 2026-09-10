# Semantic Token Contract

**The semantic tier has two kinds of semantics:**

- **static** — roles whose value is the same in every mode; they live in
  `semantic/`, one file per category (`spacing`, `sizing`, `cornerRadius`,
  `borderWidth`, `opacity`, `typography`);
- **dynamic** — roles whose value differs per mode (light, dark, high
  contrast); they live in `theme/`, one folder per mode with one file
  per dynamic category (`color`, `elevation`).

Both kinds are the same tier — named decisions published into the same
bare namespace — split only by mode variance. This document is the
structure and rules for both: how roles are named and what shape values
take. The contract defines the form — the concrete role values live in
the token files themselves. Companion to the
[primitive contract](primitive-token-contract.md) and the
[contrast contract](contrast-contract.md).

Normative words: **MUST** (contract requirement), **SHOULD** (deviation
needs a reason), **MAY** (allowed). Unless explicitly attributed to
DTCG 2025.10, they define this token system's architecture contract, not
requirements of the DTCG 2025.10 specification.

Core token paths, categories and value contracts are platform-neutral.
Platform metadata lives only in namespaced `$extensions` (§5)
and MUST NOT change the shared taxonomy.

## 1. The formula

```
{category}.{role path}          (bare namespace — no tier prefix)

static   → semantic/<category>.tokens.json — one value, all modes:
           spacing.inline.related · sizing.icon.medium · opacity.disabled
dynamic  → theme/<mode>/<category>.tokens.json — identical paths in
           every mode, values differ per mode:
           color.text.primary · elevation.raised.shadow
```

A role is named by usage intent — what it is *for* — never by its value or
its position on a scale.

Two placement rules:

- **Mode variance places the category.** Does the category's value set
  differ per mode? Differs → `theme/`; invariant → `semantic/`. Placement
  is decided per category, not per leaf: a mode-invariant decision inside
  a dynamic category does not move to `semantic/` — it belongs to the
  component tier or stays a same-value declaration in every mode.
- **Simultaneity test names the axis.** Values that co-exist on one
  screen are separate NAMES; values that are mutually exclusive per
  resolution (theme, contrast, brand, size class, density) are resolver
  CONTEXTS on one name. Mode words (`dark`, `highContrast`, brand names)
  MUST NOT appear in role names, and a second value axis is added as a
  context — never as graded name variants.

```
valid: spacing.inline.related
invalid: spacing.8 (a fact, not a decision — primitive tier)
invalid: spacing.small (magnitude ladder, not intent)

valid: color.text.primary
invalid: color.purple.600 (palette position — primitive tier)
invalid: color.text.primaryDark (mode word — resolver context)

valid: opacity.disabled
invalid: opacity.40 (scale entry — no opacity scale exists)
```

## 2. The principle

**A semantic token is a named decision.** Where a primitive states a fact
(`spacing.8` = "8 exists"), a role assigns one (`spacing.inline.related` =
"this is the gap between related inline elements"). The primitive tier is
the menu; this tier is the order.

Two tests decide whether a role exists:

1. **Instruction test** — can you write a concrete "when and how to
   apply" instruction for the role? If only an abstract description comes
   out ("generic de-emphasis"), the role does not exist — the value stays
   inline in its component.
2. **Generic-role ban** — a role MUST name a specific usage intent, never
   a vague quality (`muted`, `emphasis2`). Vagueness is the failure mode
   of the instruction test made visible in the name.

A role does **not** need a consumer to exist. A category MAY close
completely as a skeleton template — every role backed by a writable
instruction — before any component references it; a role authored ahead
of its first consumer is marked `RESERVED` in its description. Reuse
counts are not a criterion in either direction.

## 3. Files and namespace

- **Static half**: `semantic/<category>.tokens.json`, one file per
  category, kebab-case file name matching the camelCase category. Static
  categories are mode-invariant by definition — a static category
  appearing in a theme file is a contract violation, not a variant. A new
  static file MUST also be registered as a `$ref` in the resolver.
- **Dynamic half**: `theme/<mode>/<category>.tokens.json` — one folder
  per mode context of the resolver's theme modifier, one file per
  dynamic category inside it. **Shape parity** is a contract on the
  resolved output: every resolved mode declares the identical path set —
  adding a role means adding it to every mode; a mode never omits,
  renames or extends the shared shape. Theme files declare complete
  category sets with matching token paths and types; their references
  resolve in the selected resolver's composition.
- **Bare namespace** — semantic and theme files publish the public token
  API (`spacing.*`, `color.*`, `elevation.*`): no tier prefix, because
  this tier is the reference surface the system converges on. Category
  ownership is exclusive: a category root lives in exactly one half,
  never both.
- **Resolution order**: after `primitive`, before `component`; the theme
  modifier selects exactly one mode set.
- **References** — a role resolves to one of:
  - an alias to a primitive (the default where a neutral foundation
    exists);
  - an inline value (§5, only where no foundation exists);
  - a same-tier alias, which MUST come from the **sanctioned list
    only**. Cross-family aliases are forbidden by default — in
    particular `status` and `interactive` MUST NOT alias each other in
    either direction. The sanctioned aliases are: the selected-state bridges
    (`fill.control.selected`, `border.selected` → `interactive.bold`),
    recipe-internal leaves (`elevation.*.surface` → `color.surface.*`),
    hover slots (§5), and addressed rhythm aliases (`spacing.screen` →
    `spacing.content`). Extending this list is an architecture decision,
    not a convenience.
  - A role MUST NOT reference component tokens.

## 4. Category roster

The roster is a **closed allowlist**. Static half:

| Category | `$type` | Role shape |
|---|---|---|
| `spacing` | `dimension` | rhythm roles + relationship scales (`inline.*`, `stack.*`) |
| `sizing` | `dimension` | closed variant axes (`control.height.*`, `icon.*`) |
| `cornerRadius` | `dimension` | curated set + `full` |
| `borderWidth` | `dimension` | intent roles (`hairline`, `default`, `strong`, `focus`) |
| `opacity` | `number` | whole-element dimming roles, values inline |
| `typography` | `typography` | role × size matrix referencing the primitive menu |

Dynamic half:

| Category | Leaf `$type`s | Role shape |
|---|---|---|
| `color` | `color` | role families (`text`, `surface`, `fill`, `border`, `icon`, `identity`, `interactive`, `status`, `canvas`, `focus`, `scrim`) — most carry state/emphasis leaves; single-token roles (`scrim`) and structural pairs (`focus.ring`/`ringInner`) are legal shapes |
| `elevation` | `shadow`, `color` | recipe per role: `shadow` + `border` leaves, plus `surface` where a single referent exists (`none` deliberately has no surface) |

Explicitly **not** in this tier (and MUST NOT appear):

- **A second ordinal scale.** No `spacing.small/medium/large`, no
  `spacing.100/200` — a role tier that mirrors the primitive scale with
  new names is a fork, not semantics. Relationship and intent names only.
- **A "full opacity" role.** The absence of dimming is not a decision;
  where a component surface needs the leaf for shape completeness, it
  carries the component-local literal `1`, never a published role.
- **Raw value roles.** A role whose name restates its value
  (`opacity.40`, `borderWidth.0_5`) belongs to the primitive tier's
  grammar and fails the instruction test here.
- **A layout category.** Screen geometry gets no category of its own; the
  screen inset is an addressed alias inside `spacing`. Safe area is never
  a token — composition mechanics live in `$extensions`, never in values.
- **Platform-enforced constants.** Values every supported implementation
  already guarantees outside the token system (minimum touch target) are
  not tokens — the platform holds them. The exclusion holds only while
  that enforcement does; a supported platform or custom component that
  stops guaranteeing the value is the named re-entry trigger for a
  shared authored role.
- **Co-existing component anatomy.** Parts that appear simultaneously and
  must contrast with each other (thumb vs track, indicator vs container)
  are component anatomy tokens, not semantic roles. A shared data-selected
  palette such as `color.identity` remains semantic; the component declares
  its anatomy and names the palette in the relevant part description
  (component contract §3.6).

A new category enters the roster only through an explicit architecture
decision that fixes, before any token lands: the half (static or
dynamic), the DTCG 2025.10 representation, the role-name shape, and an
instruction-backed role set — a skeleton roster is acceptable, a side
effect of a component needing a value is not. An excluded category may
be reconsidered only when its stated exclusion no longer applies; the
contract MUST record the new classification and its conditions before
tokens in that category are added.

## 5. Value shapes

| Case | `$value` shape |
|---|---|
| foundation exists | alias to a primitive: `"{primitive.spacing.8}"` |
| sanctioned same-tier alias (§3) | `"{color.surface.raised}"`, `"{spacing.content}"` |
| no neutral foundation | inline value owned by the role |

Inline ownership is legal where no neutral primitive menu exists:

- `opacity` roles — inline numbers in `0…1` (never a `%` string); there is
  no opacity scale to reference.
- alpha colors (`color.scrim`, translucent borders) — alpha is part of
  the color; the translucent color is authored inline in the mode sets
  that use it. A high-contrast mode MAY legally override an alpha inline
  with an opaque primitive alias — parity binds paths, not value shapes.
- `shadow` composites inside `elevation` recipes — shadows are per-mode
  recipes, not menu entries.

**Hover is a slot, not an authored state**: in the authored base its
value MUST equal its family base (`hover` = `default`);
pointer-driven platforms supply distinct values through sparse value
overrides — values only, never new paths.

**`$extensions` carries platform metadata** and never changes
token paths, types or value shapes:

- state relationships are NOT metadata — they derive from the name
  grammar (§6); a state leaf carries no machine marker;
- platform metadata — composition mechanics (safe-area addition),
  platform mapping anchors;
- platform token extras, if ever needed, enter as additive namespaces
  referencing core roles — an extension, never a fork of the shared
  taxonomy.

## 6. Naming rules

- **Segment order is fixed**: `category → role → prominence → state`.
  The domain comes first, the state is ALWAYS last.
- **Roles are named by intent or relationship, never by magnitude.**
  Spacing uses relationship names (`tight` / `related` / `unrelated`) and
  rhythm names (`content`, `section`, `screen`); a magnitude ladder over
  metrics is forbidden (§4).
- **Closed variant axes MAY use size words.** `control.height.*` uses
  density words with an anchor (`compact`/`default`/`large`); `icon.*` is
  a deliberately ordinal ramp (`small`…`extraLarge`); `cornerRadius`
  carries a curated set. All are bounded axes, not open scales.
- **One prominence ladder per role family**: `subtle → (default) → bold`.
  Ordinal ladders (`primary`/`secondary`/`tertiary`) exist only in `text`
  and `icon`; mixing ordinal and adjectival ladders inside one role
  family is forbidden.
- **State leaves are complete values**: `hover`, `pressed`, `disabled`,
  `selected` over the family base — each leaf is a full color, not a
  delta. The state words are a closed set and always the final segment,
  so state membership derives from the name alone — no metadata marker.
  The family base is the sibling `default`, or the ordinal anchor
  (`primary`) where the family ladder is ordinal; a state leaf MUST
  have its family base declared. A leaf whose final segment is not a
  state word is a stateless variant. How leaves compose into a resolved
  state is the compound-state algorithm (§7), not extra names.
- **States stay distinguishable**: within `interactive.subtle` and
  `fill.control`, `default`, `pressed`, and `selected` MUST resolve to
  three different colors in every context. Two states sharing one color
  is a gate error.
- **`inverse` is polarity, not a state**: a stateless variant for
  opposite-polarity surfaces — it is not a state of any base and has no
  states of its own.
- **Content-on-background uses the `on` prefix** (`onBold`), and pairs
  are **declared**, not derived: role or family descriptions name which
  content role belongs to which background (an `onBold` is not automatically the
  inverse ink), and two-sided pairs (`focus.ring` + `ringInner`) are
  always applied together.
- **Typed absence is explicit.** A role set that can be "off" declares
  the absence as a role (`elevation.none`); consumers never express
  "none" by omitting a reference.
- **Forbidden name shapes**: abbreviations (`bg`, `fg`); `-variant` /
  `-alt` suffixes (a naming smell — reject at review); numeric suffixes
  where the number is not itself the semantics (no `foreground2`); mode
  words (§1). Path segments are camelCase.

## 7. Doctrines

### compound state — the algorithm that joins the halves

Static `opacity.*` and dynamic `color.*.{state}` are one system,
composed by a normative algorithm, not by extra tokens:

- base = `selected` ? `<family>.selected` : `<family>.default`;
- `disabled` → `<family>.disabled` if the family declares it, otherwise
  `opacity.disabled` over the whole element, base unchanged — never
  both (the no-stacking rule below);
- `pressed` → `<family>.pressed` if the family declares it, otherwise
  `opacity.pressed` over base;
- `hover` → `<family>.hover` if the family declares it, otherwise base
  unchanged — hover is a slot (§5), so no opacity fallback exists;
- precedence: `disabled` > `pressed` > `hover`;
- axes are orthogonal: `selected + pressed` = `<family>.selected` +
  `opacity.pressed`; `selected + hover` keeps `<family>.selected`
  unchanged unless the family explicitly declares a selected-hover
  mechanism;
- `focus` is always additive (dual ring outside the element), never a
  replacement; validation states are not an interaction axis.

### opacity — whole-element dimming

- A dimming role applies to an entire element at exactly **one
  boundary**: a container role and a child role MUST NOT stack on the
  same subtree — multiplied dimming is a diagnostic, not a look.
- Dimming MUST NOT stack on already-resolved muted/disabled colors —
  double dimming breaks contrast in high-contrast modes.
- Mechanical animation endpoints (the `0`/`1` of a crossfade) are runtime
  mechanics, not roles.

### elevation — recipes, not shadows

- An elevation role is a **recipe**: a component consumes the recipe as
  the elevation policy for a lifted surface — it MUST NOT assemble
  surface × shadow combinations manually across roles. The `surface`
  leaf is recipe-internal (consumed via the recipe, not referenced
  directly); geometry stays separate: border *width* comes from the
  static `borderWidth` roles, the recipe owns the border *color*
  (geometry/color seam).
- Each mode authors its own recipe values: dark elevation is a deliberate
  design decision (heavier alpha, keylines, surface shifts), never a copy
  of light.
- `elevation.none` is the typed absence: it follows the same consumer
  contract with neutralizing effect values and deliberately has no
  `surface` leaf — absence has no single surface referent. The recipe
  shape therefore permits a missing `surface` where no referent exists.
- Depth has **two directions**. A level is either lifted (outward
  shadow, consumed through `shadow.outer`) or recessed (`inset`
  layers, consumed through `shadow.inner`); one level MUST NOT mix
  directions. A recessed level paints no surface of its own — like
  `none`, it has no `surface` leaf. Where a mode drops a recess's
  shadow, the recipe's `border` carries the boundary.

### typography — the role scale

- The semantic matrix (`display/heading/body/label/caption/code` × sizes)
  is the **only typography surface** consumers may reference; the
  primitive text-style menu is reachable exclusively from here.
- Rows may be sparse (a family MAY exist in one size) — no filler roles
  to complete the grid.
- Two roles resolving to the same primitive style is not a merge signal —
  role identity is the contract — but a deliberate coincidence MUST be
  justified in the description; an unjustified one is a remap candidate.
- Platform variance enters as sparse value overrides on the same
  primitive paths — values only, never new paths — through the mirrored
  `platform/<name>/` tree defined by
  the [platform contract](platform-contract.md). Semantic typography
  paths and references never change across platforms.

## 8. Descriptions and lifecycle

- The inverse of the primitive rule: a primitive description states facts
  and MUST NOT contain usage guidance — a role description IS usage
  guidance. `$description` SHOULD read as an instruction ("separators,
  dividers, subtle outlines"); a role for which no such instruction can
  be written fails the instruction test (§2) and does not exist.
- The instruction lives **at the leaf or at the family level** — a group
  `$description` covers members that share one instruction; per-leaf
  descriptions are for leaf-specific rules.
- A role authored ahead of its first consumer carries `RESERVED` in its
  description; the marker is removed when the first consumer lands.
- **Deprecation is a rename pipeline, not a delete**: deprecated alias →
  deprecation note in `$extensions` → removal in the next major. Roles
  are the public API; paths never vanish without the pipeline.
- A description that names another token's key spells it exactly.
