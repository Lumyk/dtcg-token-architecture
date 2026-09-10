# Contrast Contract

**Contrast is an acceptance policy on values, not a token form.** This
document owns the invariants every resolved color pair in the system
must satisfy. It contains no color data: palettes, ramps and themes
change freely underneath it — a change of values never changes this
contract, because this contract is the criterion the new values are
accepted against. Companion to the
[primitive contract](primitive-token-contract.md) and the
[semantic contract](semantic-token-contract.md).

Normative words: **MUST** (contract requirement), **SHOULD** (deviation
needs a reason), **MAY** (allowed). This contract uses the WCAG 2.x
contrast-ratio calculation. WCAG AA contrast minima are requirements in every theme;
high-contrast themes additionally require the enhanced text targets below.

## 1. Thresholds

### Required minima — every theme

The same minima MUST hold in `light`, `dark`, and their high-contrast
counterparts, subject to the exemptions in §3:

| Content | Required minimum |
|---|---|
| ordinary text | ≥ 4.5:1 |
| large text with guaranteed qualifying typography | ≥ 3:1 |
| non-text visual information needed to identify controls, states, or meaningful graphics | ≥ 3:1 against adjacent colors |

Text minima follow
[WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html);
non-text minima follow
[WCAG 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
The non-text requirement includes meaningful icons, necessary control
borders, and authored focus indicators, not every decorative stroke.

The large-text minimum MAY be used only when the declared usage
guarantees at least 18 pt text, or 14 pt bold text, as defined by WCAG
(24 CSS px or approximately 18.67 CSS px bold). A token's numeric size
alone does not establish that guarantee across platforms. A text role
with unspecified or mixed-size usage MUST meet 4.5:1; a name such as
`title` is not evidence of large text.

### Required enhancement — high-contrast themes

- In `light-high-contrast` and `dark-high-contrast`, text MUST reach the
  [WCAG 1.4.6](https://www.w3.org/WAI/WCAG22/Understanding/contrast-enhanced.html)
  enhanced ratio of 7:1. In these contexts the validator treats every
  4.5:1 text pair as a 7:1 pair and fails on a miss.
- No declared pair currently uses the large-text minimum; every 3:1 pair
  is non-text. If a large-text pair is ever declared, its high-contrast
  minimum is 4.5:1, and the validator needs to tell it apart from
  non-text pairs before that can be enforced.
- Reaching 7:1 by nudging fills MUST NOT erase state cues. In every
  context, `interactive.subtle` and `fill.control` resolve `default`,
  `pressed`, and `selected` to three different colors; the validator
  rejects two states that share one.
- High-contrast themes SHOULD improve meaningful pair contrast over
  the corresponding light or dark theme where improvement is possible.
  Non-text contrast SHOULD exceed the 3:1 minimum where practical;
  there is no separate mandatory 4.5:1 non-text threshold.

Passing the required minima establishes only the declared contrast
checks, not conformance with all WCAG AA criteria for an interface.

## 2. Scope — declared pairs on resolved values

- Required minima bind **declared pairs** (semantic contract §6): a content
  role against its declared background (`onBold` on
  its `bold`, status ink on its `subtle` wash, text roles on the
  surfaces they are declared for). Role or family descriptions MUST
  identify the intended pairings; pairs are declared, never inferred.
  Token descriptions are the source of pairing declarations, not a
  separate registry. Put shared usage instructions on the relevant
  family and exceptions on its leaves. Spell referenced paths exactly;
  a named group includes its members unless exclusions are explicit.
- Component descriptions MUST identify how content, local backgrounds,
  and surrounding host surfaces pair in their authored configurations.
  Transparent containers reveal the declared underlying surface; they
  are not themselves the background against which text is judged.
- Measurement happens on the **resolved output of each mode** — after
  aliases resolve and alpha composites over the declared background.
  A translucent color is judged by its composited result, not its
  authored alpha.
- Every non-exempt declared pair MUST meet its applicable minimum in
  every mode context. Recommended enhancements are assessed separately.
  Shape parity guarantees the paths exist; contrast verification checks
  the resolved pairs.

## 3. Exemptions

- **Inactive controls (`disabled`).** Their text and non-text visuals MAY
  fall below the minima — the platform convention and WCAG both
  exempt inactive controls. Nothing else inherits this: `placeholder`
  is NOT exempt and MUST meet the text threshold on its input surface.
- **Decorative strokes** (`border.subtle`) MAY fall below the non-text
  minimum in any theme while they carry no meaning a user must perceive.
  A high-contrast theme SHOULD improve their visibility where useful
  (the opaque-override route, semantic contract §5).
  A border that communicates state (`input`, `selected`, status) is
  never decorative.

## 4. Contrast beats brand

When a brand or identity hue fails a required minimum on its declared
background, the **value moves, never the requirement**: the role shifts
to an adjacent ramp step (or the ramp is re-stepped at the primitive
tier) until the pair passes. Weakening a threshold, exempting a pair,
or accepting a near-miss for brand fidelity is not an available
resolution. A deliberate value shift made for contrast SHOULD be noted
in the role's description.

## 5. Tier rule — a11y-critical roles are alias-only downstream

Component tokens for user-perceived content — text, icons, control
borders, focus indicators — MUST alias semantic roles and MUST NOT
carry inline color values: an inline value bypasses the pair
declarations this contract is verified against. The component contract
§5 applies the stricter alias-only rule to all component colors,
including decorative surfaces; its only primitive exception is
`{primitive.color.transparent}` for typed absence.

## 6. Verification

- Changes MUST satisfy the applicable minimum for every non-exempt
  declared pair in every affected mode context, using resolved
  composited values without rounding a failing ratio up to the minimum.
  Appearance and platform overrides MUST preserve the same obligations.
  A failing minimum blocks the change that introduced it.
- The high-contrast 7:1 text requirement is checked and reported the
  same way as the required minima; missing it blocks the change.
- Verify actual component references after composition as well as the
  semantic pairs: a valid palette does not guarantee that a recipe
  selects the correct ink. Tests explicitly encode pairs according to
  the token descriptions; they do not parse free-form prose as a rule
  language. A new or changed pairing MUST update its description
  and verification together. Additional host backgrounds need explicit
  pair declarations, not an assumption that any background is safe.
- Resolved pair checks do not verify rendered geometry, selection
  recognition, focus-ring area and placement, material effects, or
  image content; these need interface-level verification.
- Pair declarations identify usage; measured ratios are verification
  results. Neither becomes a token value or a threshold encoded in a
  role name.
- Additional contrast measurements MAY supplement verification; the
  required minima in §1 remain the acceptance criteria.
