# Component Token Contract

The structure and rules for the component tier of the token tree: how a
component's token file is shaped, which axes of variability exist, how
anatomy is declared, and what a component may reference. The contract
defines the form — the concrete components and their values live in the
token files themselves. Companion to the
[primitive contract](primitive-token-contract.md), the
[semantic contract](semantic-token-contract.md) and the
[contrast contract](contrast-contract.md).

Normative words: **MUST** (contract requirement), **SHOULD** (deviation
needs a reason), **MAY** (allowed). Unless explicitly attributed to
DTCG 2025.10, they define this token system's architecture contract, not
requirements of the DTCG 2025.10 specification.

Core token paths, axes and value contracts are platform-neutral.
Platform-specific metadata lives only in namespaced `$extensions` (§7)
and MUST NOT change the shared taxonomy.

## 1. The formula

```
component.{component}
  .[variant.{variant}]
  .[ size.{size} | layout.{layout} | state.{state}[.selection.{selection}] ]
  .parts.{part}[.parts.{child}]*
  .{property}[.{slot}]
```

The `.{slot}` tail exists for exactly one property: `shadow.outer` /
`shadow.inner` (§4). Every other property is a leaf.

- One component per file: `component/<kebab-name>.tokens.json` publishes
  one camelCase component key (`text-field.tokens.json` → `textField`)
  under the `component.*` namespace
  (`{ "component": { "textField": { … } } }`). The namespace makes a
  collision with a primitive or semantic category root structurally
  impossible — no collision rule exists because no collision can.
  Component tokens MUST NOT be alias targets (§5).
- Segment order is fixed. Every axis is explicitly marked. An unused
  axis has no level — never `variant.default`, never a `size` level for
  a component with one size.
- `size`, `layout` and `state` are disjoint sibling branches: they MUST
  NOT nest inside one another.
- `parts` is recursive: `parts.segment.parts.label`.
- One parser shape for every component. No generic resolution DSL
  exists — no conditionals, no prop bindings, no delta merging.

## 2. Ownership: cause of variability, not token type

**Variant is an outer contract scope, not a peer variability owner.**
Within each component — or, when the component has variants, within each
variant scope — every leaf is owned by exactly one of:

| Why the leaf changes (within its scope) | Owner |
|---|---|
| it never changes | base `parts` |
| it changes with size | `size.{size}` |
| it changes with layout/configuration | `layout.{layout}` |
| it changes with presentation state | `state.{state}` snapshot |

A variant-only property lives in the base of its variant scope; a
state-owned property lives in that scope's state snapshots. The same
leaf appearing under two different variants is two different scopes,
not a violation.

**Variant owns only what varies by variant.** When a component
activates `variant`:

- a base `parts` leaf lives at the component root only when it applies
  to every variant with the same meaning and value; otherwise it lives
  inside variant scopes. The same leaf path MUST NOT appear at both
  levels;
- each whole family (`size` / `layout` / `state`) lives at the component
  root only when its members, owned paths, types, and values are shared
  by every variant. Otherwise the family lives wholly inside variant
  scopes. A family split across the two levels is a gate error;
- **intent variants** declare every variant-owned leaf and family in
  every variant scope, with identical paths and types;
- **structural variants** declare only the leaves and families their
  anatomy requires. Their part/property sets and family members MAY
  differ. Every declared size, layout, or state family MUST be complete
  within its own variant scope; a path shared by scopes keeps the same
  meaning and type.

For example, `progress.variant.linear` declares a track `cornerRadius`
and size-owned `height`; `progress.variant.circular` declares size-owned
`diameter` and `thickness`. Neither variant adds unused geometry to match
the other. Every size within `linear` still declares the same height
surface, and every size within `circular` the same diameter/thickness
surface.

Composition stays a disjoint union of root-owned surfaces plus the
selected variant's surfaces; there is no fallback from a variant scope
to the root, because no leaf exists in both.

**Single-owner rule:** within one scope, one canonical leaf path MUST
have exactly one owner among base / `size` / `layout` / `state`. The
same leaf in two branches of one scope is a gate error. If a leaf needs
to depend on both size and state, the contract MUST define that
composition and its conformance criteria before the new structure is
authored (§9). Duplicating the leaf across owners is not permitted.

**Composition:** the final resolved look is the disjoint union of
base-owned leaves + the selected size surface + the selected layout
surface + the selected state snapshot. No fallback, no precedence — the
four families never overlap.

## 3. Axes

### 3.1 `variant` — intent or structure, never appearance

Legitimate in exactly two cases:

- **Semantic intent** — the call site names a different meaning:
  a button's `primary/…/destructive`, a status component's
  `success/error`. Intent variants over statuses draw from the closed
  status roster: `neutral / brand / info / success / warning / error`.
  A component uses a contiguous subset; inventing a synonym for a
  roster word is a gate error.
- **Structural mode** — different anatomy, content contract, or
  consumer-visible behavior: a progress indicator's `linear/circular`.
  An internal implementation detail is never the criterion — only what
  the consumer can observe. Structural variants MUST retain the common
  purpose of one component; unrelated components do not share a variant
  axis merely because their token files could be grouped together.

**The variant test:** if the same capabilities and behavior can be
achieved with different values in the same slots, it is an appearance
recipe, not a variant — it MUST NOT become an axis of the component
shape. Each component has one canonical recipe (§8); replacing it is a
value edit, while coexisting recipes use appearance overrides (§9).

Control question: *if the designer completely changes the visual
recipe, does this choice survive in product code?* Names are
descriptive intent words, never appearance words; `v1`/`v2` are
forbidden. At most one variant axis per component.

**Every variant MUST carry an instruction `$description`** — a
call-site instruction saying when to choose it (the same instruction
test as semantic roles, semantic contract §2), and the variant group
SHOULD carry a family-level `$description` naming the axis's meaning.
A variant whose instruction cannot be written is an appearance recipe
in disguise. A widely known appearance term MAY live in the
description as a searchable synonym, never in the name.

### 3.2 `size` — a discrete size ramp

Exists only when the consumer genuinely chooses a size. Canonical names
are full words (`small / medium / large`, extended with `extraSmall` /
`extraLarge` prefix steps where a ramp needs them; density ramps use
`compact / default / spacious`). Abbreviations (`sm`, `md`, `lg`, `xl`,
single letters) are forbidden. Invariant metrics live in base — a fake
`size.default` level MUST NOT exist. All sizes within one owning scope
declare the identical size-owned metric surface (family shape
completeness); structural variant scopes may differ under §2.

### 3.3 `layout` — arrangement of the same anatomy

A named owned surface for arranging one superset anatomy. Composite
layout names concatenate configuration cases in the canonical order the
component's configuration vocabulary declares (`floatingMultiline`,
never `multilineFloating`). Every layout within one owning scope MUST
declare the identical, complete layout-owned metric surface. Layout is a full
axis, not a half-axis over a hidden baseline: if a metric is
layout-owned, it exists in every layout and nowhere else.

**Layout vs structural variant:** same anatomy, different
placement/metrics → layout; different anatomy/parts → structural
variant.

### 3.4 `state` — a complete snapshot of the state-owned surface

A state is a **snapshot, not a delta**. Every state key declares the
complete state-owned surface — every property that changes with state
in *any* state of the set — with full values of any token types.
Properties that never change with state never appear in a state.

- **State words are a closed set**: `default / hover / pressed /
  focused / error / disabled`. A new state word enters the contract
  only with a component that needs it and defined semantics, combination
  order, and precedence relative to the existing states.
- **An active state set MUST contain `state.default`** plus at least
  one other state — the default snapshot *is* the normal look of the
  state-owned surface. A component with no runtime states has no
  `state` level at all.
- **Completeness:** all snapshots of one state set MUST have identical
  paths and types. A missing leaf is a gate error, never a fallback. A
  sparse "delta state" (a state carrying only the properties it
  changes) is forbidden.
- **Snapshots are authored, never computed.** The author applies the
  semantic compound-state algorithm (semantic contract §7) when
  choosing references; the runtime picks one ready typed snapshot. No
  runtime cascade, no merge order.
- **No stacking inside a snapshot:** a `disabled` snapshot either swaps
  to declared disabled colors with opacity `1`, or keeps base colors
  and applies `{opacity.disabled}` — never both (double dimming).
  The same rule applies to `pressed` / `{opacity.pressed}`.
- **`hover` is a slot, not an authored look** (mirrors semantic §5):
  the snapshot MAY exist only as a platform-override surface — in the
  authored base file its leaves MUST equal `state.default` leaf for
  leaf; pointer-driven platforms supply distinct values through
  value-only overrides, never new paths.
- **Combined states** concatenate registered words in the conceptual
  order `interaction → validation → availability`: `focusedError`,
  never `errorFocused`. The gate decomposes the identifier into
  registered state words. A combined state exists only when the
  combination genuinely has its own designed look — and it joins the
  set's shape-completeness contract like any other state.
- **Combined states invent no third look**: each channel of a combined
  snapshot cites the same role as that channel in one of its
  constituent states (`focusedError` → the `focused` or the `error`
  value). A combined state may only choose, per channel, which
  constituent wins — never introduce a role neither constituent uses.

**Grammar seam with the semantic tier** (deliberate, not a conflict):
in semantic color families `default` is the family base and not a
state, and validation/focus are not interaction states — because a
semantic leaf is one role's color. A component state is a snapshot of a
whole element, so `default` is its mandatory base snapshot and
`focused` / `error` are legitimate presentation snapshots that consume
`color.focus.*` and `color.status.error.*` / `color.*.error` roles.

### 3.5 `selection` — the only sub-dimension of state

Only for selectable components:

```
state.default.selection.selected
state.default.selection.unselected
```

The state × selection matrix MUST be complete, or the unsupported pairs
are declared in `unsupportedCombinations` (§7). Selection is never
duplicated inside combined state names and never encoded in property
names (`selectedBackground` is forbidden — that is a selection axis
escaping the shape gate).

### 3.6 `parts` — all anatomy, recursive

- **Every visual leaf MUST live in `parts`.** The surface of a simple
  component is `parts.container`. Root-level properties do not exist —
  one spelling for all components.
- **Data-driven paint**: a semantic palette selected by runtime data
  (`color.identity`) owns the selected paint values. The component owns
  the anatomy, geometry, and typography to which those values apply.
  The relevant part or paint-leaf `$description` MUST name the palette;
  its background and ink MUST come from the same selected entry.
  A component MUST NOT alias an arbitrary entry to stand in for the
  data selection. A choice made by usage intent is a variant, not
  data-driven paint.
- **Palette-owned color**: a part whose color comes exclusively from
  that declared palette MAY omit a component `color` leaf. If a paint
  property is already part of an authored family or intent-variant
  surface, it MUST remain present in every member, using typed absence
  for the configuration whose paint comes from data. Palette ownership
  MUST NOT be used to omit a token-owned state or size value.

  In the `avatar` identity variant's monogram configuration,
  `color.identity.{item}.background` paints `parts.container`, and the
  same entry's `ink` paints `parts.initials`. The container keeps its
  typed-absence `background` leaf because that property is shared by
  the intent variants. Initials have no component-owned `color` leaf;
  their size-owned `typography` remains in the component tree. The
  palette's ink/background contrast obligation applies to every entry.
- Part names are roles: `container, content, label, title, subtitle,
  placeholder, helper, counter, input, icon, leadingIcon, trailingIcon,
  track, fill, indicator, separator, divider, segment, box, dot, badge,
  ring, outline, bar, chevron, initials, emoji`. A new role enters the vocabulary together
  with the component that needs it. `chevron` is the host-owned
  disclosure affordance — distinct from `trailingIcon` (content); the
  two MAY coexist, and the chevron never carries consumer-supplied
  content. Glyph direction is component behavior, not a token. Forbidden: compound hierarchy in a key
  (`segmentLabel` → `segment.parts.label`), type suffixes
  (`titleText`), abbreviations.
- **Slots are declared anatomy without paint.** A part whose content is
  supplied by the consumer (a swapped-in component instance) is listed
  in the `slots` array of the envelope (§7). A slot part MAY carry only
  host-owned placement metrics (`gap`, `size`, offsets) and MUST NOT
  carry paint or typography — the slotted component brings its own
  tokens.

## 4. Property vocabulary

Full words. The part role provides context — `parts.label.color`, never
`labelColor` or separate text/icon color names.

| Group | Canonical properties |
|---|---|
| paint | `background`, `color`, `borderColor`, `opacity`, `shadow` (a fixed two-slot group, see below) |
| border geometry | `borderWidth`, `cornerRadius`, `dashLength`, `dashGap` (+ edge-qualified `borderColorTop/Bottom`, `borderWidthTop/Bottom`, `cornerRadiusTop/Bottom`) |
| box | `width`, `height`, `minWidth`, `minHeight`, `size` (square part metric), `diameter`, `thickness` |
| padding | `paddingHorizontal`, `paddingVertical`, `paddingTop/Bottom/Leading/Trailing` |
| rhythm | `gap`, `inset`, `offset`, `offsetX/Y` |
| text | `typography` |
| focus | `focusRingColor`, `focusRingWidth`, `focusRingOffset` |

- Abbreviations are forbidden: no `bg`, `fg`, `paddingH/V`. The
  radius property is `cornerRadius`, matching the primitive and
  semantic category — `borderRadius` does not exist in this tree.
- Directionality: `Leading/Trailing`, never `Left/Right`.
- An edge qualifier is always the **final** segment (`borderColorBottom`,
  never `borderBottomColor`). A contract declares either the plain
  property or its edge-qualified pair, never both. The full border and
  the bottom underline are two independent renderer capabilities and
  MAY coexist in one contract.
- **Dash geometry**: `dashLength` is the length of a painted border
  segment; `dashGap` is the unpainted interval between segments. Both
  are non-negative `dimension` leaves using the same unit. A part that
  supports this pattern MUST declare both within the same owner surface.
  A dashed recipe uses positive values for both; a solid recipe keeps
  both leaves at zero. Intrinsic values carry the explanation required
  by §5. The avatar's add/identity variants use this shared geometry.
- **Focus ring geometry**: the ring is a separate layer drawn above the
  part's border, concentric with its corner radius. `focusRingOffset`
  measures the gap between the border's outer edge and the ring:
  `0` — the ring sits directly on top of the border stroke (overlay);
  positive — a halo outside the border; negative — inside the edge.
  The ring layer never replaces or recolors the border stroke.
- **`shadow` is the one property-group**: a part's shadow surface is
  always the fixed pair `shadow.outer` (drop) and `shadow.inner`
  (inset). Each slot is a single `shadow`-typed token; typed absence is
  `{elevation.none.shadow}`; a declared `shadow` group always declares
  both slots. No other property nests — the pair exists because outer
  and inner shadows are two independent rendering channels, not two
  values of one channel. A bare `shadow` leaf does not exist.

  The shadow **value contract**, everywhere in the tree: a `$value` is
  an alias, a single layer object, or an ordered list of layer objects
  (outermost first). A layer object carries exactly
  `offsetX, offsetY, blur, spread, color` plus the optional boolean
  `inset`; `inset` defaults to false and marks the layer as drawn
  inside the surface. Core theme elevation levels author a single
  layer per level — one level is one depth phenomenon; layer lists are
  legal for platform-tier value overrides whose native depth model is
  itself multi-layer. Component slots consume levels by alias only
  (§5), so a slot never authors layers inline.
- A state word inside a property name is forbidden (`disabledOpacity`,
  `colorPressed` → the state snapshot owns the leaf). A configuration
  word inside a property name is forbidden (`floatingMinHeight` → the
  metric is layout-owned).
- Visibility booleans (`showHelper`) are configuration, not tokens, and
  MUST NOT exist in any form (§7).

## 5. Reference discipline

| Component leaf | Source |
|---|---|
| color | **only** `color.*` roles; the single primitive exception is `{primitive.color.transparent}` as a typed-absence value (§8) |
| shadow | `elevation.{role}.shadow` under the recipe-coherence rule below |
| typography | `typography.*` roles |
| opacity (element dimming) | `opacity.*` roles; the full-opacity leaf a state set needs for shape completeness is the component-local literal `1`, never a published role |
| metrics (spacing/sizing/radius/border width) | a semantic metric role where one matches the **intent** (`sizing.icon.*`, `spacing.*`, `cornerRadius.*`, `borderWidth.*`), else the `primitive.*` menu; a role is chosen by matching intent, never by matching value — a coincidental value match (a role chosen only because its resolved value happens to equal the needed one) couples the leaf to a foreign decision and is forbidden; a metric that must vary per mode or brand is promoted to a semantic role first |
| intrinsic literal (`0`, bespoke geometry: concentric radii, negative overlap, dash patterns) | component-local inline value with a `$description` explaining why it is intrinsic |

- A part-property `$description` states the slot's invariant — what the
  token owns and why it exists — never the rationale for the currently
  chosen value; value rationale lives in the variant recipe or this
  contract.

- **Recipe coherence (elevation):** DTCG 2025.10 aliases reference
  single tokens, so a recipe is consumed leaf by leaf — but all
  elevation leaves of one part in one snapshot MUST cite the **same**
  elevation role (`elevation.raised.shadow` next to
  `elevation.modal.border` is a gate error). Two refinements: the
  typed-absence role `elevation.none` is always exempt, and the two
  `shadow` slots MAY cite different roles — `shadow.outer` at
  `elevation.raised` with `shadow.inner` at `elevation.concave` is one
  coherent surface (lift and concavity are independent depth channels). The `surface` leaf is
  recipe-internal (semantic contract §7) and is never referenced from
  a component.
- A component MUST NOT reference another component's tokens.
- A component MUST NOT alias its own leaves (`pressed.shadow` repeating
  `{elevation.raised.shadow}` is correct;
  `{component.button.primary.default.shadow}`
  is not) — every snapshot spells its references explicitly (WYSIWYG).
- All references MUST resolve, types MUST match, zero cycles.

Primitive key naming and the primitive/semantic boundary are governed by
the primitive contract; role naming and the compound-state algorithm by
the semantic contract; a11y-critical component leaves are alias-only per
the contrast contract.

## 6. File format

The component tier is authored directly in DTCG 2025.10 — `$value` /
`$type` / `$description` / `$extensions`. The canonical vocabulary (§4)
MUST appear verbatim in the files; alternate spellings and implicit
normalization are not permitted. A component file participates in a
resolver's composition only when listed in its `component` set. Adding
a file to that composition MUST update the base resolver and each
platform resolver (platform contract §4).

## 7. `$extensions` envelope

All system metadata lives under the `com.designsystem` namespace; Swift
mapping metadata lives under `com.apple.swift`. The system namespace is
deliberately brand-free: the tree is a reusable template, and adopting
projects never rename it. Platform extensions are additive and MUST NOT
change token paths, types or value shapes.

```json
{
  "component": {
    "textField": {
      "$extensions": {
        "com.designsystem": {
          "schemaVersion": 1,
          "slots": ["parts.leadingIcon", "parts.trailingIcon"],
          "unsupportedCombinations": [
            { "state": "focusedError", "selection": "unselected" }
          ],
          "materials": {
            "parts.container": { "kind": "glass" }
          }
        }
      }
    }
  }
}
```

- `schemaVersion` MUST be `1` at the component root — it versions the
  grammar of this contract, not the component's design, the repository
  release, or the DTCG specification.
- `slots` (§3.6) and `unsupportedCombinations` (§3.5) are declarative
  contracts for the gates; both are optional when empty.
- `variantKind` MAY be declared at the component root as `"structural"`
  when the variant axis is structural (§3.1); absence means intent.
- The envelope exists in exactly two places: the **component root**
  and each **variant scope**. No other level — no `size`, `layout`,
  `state`, `selection`, and no `parts` node at any depth — carries a
  `com.designsystem` envelope.
- `materials` declares surface material intent **per surface part**:
  an optional, non-empty map from part path to a structured
  descriptor — never a boolean, never a bare scope-wide object. Each
  key is a `parts.…` path in the same dot notation as `slots`
  (recursive segments included) and MUST resolve, in the owning
  scope's composed shape, to a declared part whose `background` leaf
  exists in every configuration the declaration governs — the owner
  may be base, `size`, `layout`, or any state snapshot. A part listed
  in `slots` MUST NOT be a target — the slotted component brings its
  own material. Each descriptor carries at least `kind`; new kinds and
  categorical qualifiers enter as additive keys — never a schema
  change. A part absent from the map is the **solid baseline**; a
  `kind: "solid"` entry MUST NOT exist. Because materials live only in
  scope envelopes, material cannot vary per state — the shape forbids
  it, no prose prohibition needed.
- Ownership mirrors §2 in both directions: an assignment identical
  across every variant scope MUST be hoisted to the component root,
  and the same target path MUST NOT appear in both the root map and a
  variant map.
- **One component MAY mix materials.** Different surfaces of one
  anatomy are different physical planes: a glass track with a solid
  selection indicator is a legitimate — often the correct — stack.
  Each surface resolves independently from the map.
- **Material changes the rendering strategy, never the semantic
  appearance contract.** Every snapshot authors the complete solid
  recipe; an adapter that does not support — or does not know — a
  material kind MUST render that authored solid recipe. Adapters opt
  in to the kinds they know; an unknown kind is never an error. An
  adapter MUST NOT broaden a material to surfaces the map does not
  name; one mapping onto a native control that admits a single
  material honors the entry for the part it maps onto that control
  and renders every other surface from its authored solid recipe.
- Material settings route by nature: categorical words (`kind`, or
  `style` when a material needs that distinction) are descriptor keys,
  because DTCG 2025.10 has no string token type; designer-tuned quantities become typed token
  leaves on the surface part named by the entry — `dimension` for a
  blur radius, `color` for a tint, `number` for an opacity — owned by
  the scope that owns the entry, and authored only when the value
  becomes this system's decision, never to freeze a platform default.
- Forbidden anywhere in the envelope: derived inversions
  (`solidBackground`), visibility
  booleans (`showInside`, `showHelper` — configuration, not tokens),
  and state-relationship metadata (the name grammar carries it).

## 8. The template doctrine: shape is API, values are design

A component token file is a **template**: its shape declares anatomy and
ownership; its values define the visual recipe on that shape.

- **The shape is the superset.** Within each scope, configurations retain
  the declared token-owned surface; "absent" capabilities are expressed
  by typed absence values — `{primitive.color.transparent}`, `borderWidth`
  referencing the zero entry, `{elevation.none.shadow}`, opacity `1` —
  never by omitting the leaf. Structural variants define separate
  surfaces under §2. Color supplied exclusively by a declared
  data-selected palette follows §3.6; it does not create an incomplete
  token-owned surface.
- **One canonical recipe per component.** The component file authors the
  canonical appearance recipe. Replacing its look (filled → outlined,
  elevated → flat) changes values on the same shape. If both recipes
  must coexist, the additional recipe uses an appearance override (§9).
- **Change classes:**

| Change | Token edit | Contract requirements |
|---|---|---|
| value edit (re-skin, retheme) | edit values or references on existing paths | preserve types, role intent, ownership, and contrast obligations |
| new variant | add a scope for a distinct intent or structural mode | apply the variant test (§3.1), ownership rules (§2), and scope completeness (§11) |
| shape change (new part/property/axis) | extend the declared anatomy or owned surfaces | use the existing grammar and vocabulary; extend the contract under §9 if they cannot express the need |

## 9. Extension rules

### Additional appearance recipes

When multiple visual recipes must coexist on the same component shape:

- The canonical recipe MUST remain in the `component` set.
- Additional recipes MUST live in `appearance/<name>/<component>.tokens.json`
  and be referenced by an `appearance` resolver modifier, after the
  `component` set. The default context MUST be empty.
- Overrides MUST use existing component token paths with matching
  `$type`s. Every authored override value MUST differ from the base;
  omitted paths retain the base values.
- Color overrides MUST be aliases under §5 so theme and appearance
  selections compose. Appearance overrides MUST NOT change anatomy,
  ownership, or metadata that defines the component shape.
- A new appearance context MUST be included in the base and platform
  resolvers, and its references MUST resolve in every theme.

### Platform differences

When a platform needs different values, use sparse overrides on
identical paths in `platform/<name>/` and the corresponding platform
resolver. Placement, composition, and conformance follow the
[platform contract](platform-contract.md).

### Needs outside the existing grammar

The following needs require a contract extension before authoring their
new token structure. They do not permit an exception to the existing
grammar by themselves.

| Need | What the extension must establish |
|---|---|
| two independent variant dimensions | distinct meanings, why one variant axis cannot express them, composition, ownership, and completeness rules |
| `collection.{name}.{item}` | a component-local algorithmic set that fails the semantic-role tests, its key/type grammar, and how it is consumed without component-to-component aliases |
| a new state word | a component that needs it, its meaning, combination order, precedence, and snapshot completeness |
| a leaf depending on multiple owners | why disjoint ownership cannot express it and explicit composition and completeness rules |
| specialized shape policy | anatomy that the existing superset and structural-variant rules cannot express, with explicit scope and conformance criteria |

A new part role or property similarly MUST enter the vocabulary with
its meaning and first component use. Each extension MUST document the
concrete need, permitted structure, and conformance criteria in this
contract together with its first use. Existing invariants remain binding
unless the extension explicitly revises them.

## 10. The composed shape

Every rule of this contract composes into one skeleton:

```
component.{component}
  $extensions."com.designsystem" — schemaVersion; optional declarations (§7)

  parts.{part}.{property} — invariant leaves (base)
  size.{size}.parts.…
  layout.{layout}.parts.…
  state.{state}[.selection.{selection}].parts.…

  variant.{variant} — only for a different meaning or structure
    $description
    $extensions."com.designsystem" — materials when variant-owned
    parts / size / layout / state — holds only what varies by variant
```

Each member of a size, layout, or state family declares the identical
owned surface. Root-owned and variant-owned surfaces are disjoint (§2).

The resolved look of one configuration is the disjoint union of the
base surface, one member per active family, and — when variant is
active — the selected variant's surfaces (§2). No fallback, no
precedence, no merge: every leaf comes from exactly one owner. An
appearance style is never an axis of this skeleton — it is a set of
values on it (§8). Content, behavior flags, and slot fills are not token
axes; the token tree describes only their authored visual configurations.

Files in `component/` MUST conform to this contract. Their concrete
anatomies and values provide examples of the shared grammar.

## 11. Gates

Every component change MUST satisfy these conformance criteria:

1. One component per file under the `component.*` namespace; the
   component key matches the file name; the envelope carries
   `schemaVersion`.
2. Active markers: `variant / size / layout / state / selection /
   parts`. `collection` is reserved and MUST NOT be authored before a
   contract extension defines its grammar (§9).
3. Segment order follows §1; `size` / `layout` / `state` never nest.
4. `selection` exists only under `state.{state}`; the matrix is
   complete or the missing pairs appear in `unsupportedCombinations`.
5. At most one variant axis. The component envelope declares the axis
   kind — `variantKind: "structural"`; an absent declaration means
   intent. Intent variant scopes hold only variant-owned surfaces with
   identical paths and types across scopes. Structural variant scopes
   (§3.1: different anatomy, content contract, or consumer-visible
   behavior) MAY differ in parts, properties, and family members. Each
   declared family is complete within its own scope; shared paths keep
   the same meaning and type. The truthfulness of a `structural`
   declaration is judged by the §3.1
   test (gate 6). No leaf path exists both at the root and inside a
   variant scope; each of `size` / `layout` / `state` lives wholly at
   one level; status-intent variants use the closed status roster
   (§3.1).
6. An appearance recipe never becomes an axis of the component shape
   (§3.1 test — human review).
7. Single owner: each leaf path has exactly one owner from §2.
8. Every variability family is shape-complete within its owning scope:
   all states of one set, all sizes of one size family, and all layouts
   of one layout family declare identical owned paths and types. A
   missing leaf is an error; sparse delta states are forbidden.
9. An active state set contains `state.default` plus at least one other
   state; state words come from the closed set (§3.4); combined names
   decompose into registered words in canonical order.
10. An authored `hover` snapshot equals `state.default` leaf for leaf
    (§3.4).
11. A `disabled` (or `pressed`) snapshot never combines declared
    swapped colors with the corresponding dimming role (no stacking).
12. All visual leaves live under `parts`; no root or axis-level loose
    properties; part names come from the role vocabulary.
13. Property names come from §4: no abbreviations, no state or
    configuration words, no edge-qualifier-first spellings, no
    `borderRadius`. Dash geometry declares both `dashLength` and
    `dashGap` under one owner, with non-negative dimensions in the same
    unit: both positive for a dashed recipe, both zero for solid.
14. Slot parts carry only host-owned placement metrics — no paint, no
    typography (§3.6).
15. References follow §5: colors from `color.*` (transparent excepted),
    shadows under recipe coherence, no component-to-component and no
    intra-component references, everything resolves with matching
    types and zero cycles.
16. The envelope follows §7: it occurs only at the component root and
    variant scopes; `materials` is a non-empty map keyed by `parts.…`
    paths (a singular `material` field is forbidden), every
    key resolves to a declared non-slot part with a `background` leaf
    in the governed configurations, no `kind: "solid"`, no
    `solidBackground`, no visibility booleans, single
    `com.designsystem` namespace. Ownership parity: a target identical
    in every variant map is hoisted to the root map; no target appears
    at both levels.
17. References to renamed semantic roles follow the role lifecycle
    (semantic contract §8): deprecated alias → note in `$extensions` →
    removal in the next major. Component aliases remain forbidden (§5).
18. Every variant carries an instruction-style `$description` (§3.1).
19. Appearance overrides follow §9: existing paths and types, differing
    values, alias-only colors, unchanged component shape, an empty
    default context, and valid references in every theme.
20. Data-driven paint follows §3.6: descriptions name the semantic
    palette, background and ink use the same entry, and palette-owned
    color does not remove leaves from a token-owned family surface.
