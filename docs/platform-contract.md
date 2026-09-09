# Platform Contract

The structure and rules for platform variance: how an additional platform
(Android, web, …) enters the token tree, where its overrides live, and
how resolvers expose them. The contract defines the mechanism — the
concrete platform values live in the token files themselves. Companion
to the [primitive contract](primitive-token-contract.md), the
[semantic contract](semantic-token-contract.md), the
[component contract](component-token-contract.md) and the
[contrast contract](contrast-contract.md).

Normative words: **MUST** (contract requirement), **SHOULD** (deviation
needs a reason), **MAY** (allowed). Unless explicitly attributed to
DTCG 2025.10, they define this token system's architecture contract, not
requirements of the DTCG 2025.10 specification.

## 1. The model: base plus exceptions

The base tree (`primitive/`, `semantic/`, `component/`, `theme/`) is the
single source of truth and is **never** forked, copied or renamed for a
platform. A platform contributes only **exceptions** — sparse override
files holding exactly the tokens whose values differ on that platform.
Everything shared lives once, in the base.

Two axes, two levels:

- **theme** is a runtime axis — the app switches it live; it stays a
  resolver modifier (`light` / `dark` / …).
- **platform** is a build-time axis — an iOS binary never becomes an
  Android one; it is expressed as the choice **between resolvers**,
  never as a resolver modifier.

## 2. File layout: the mirrored sparse tree

Platform overrides live under `platform/<name>/` and **mirror the base
tree path for path**:

```
tokens/
  primitive/ semantic/ component/ theme/ — shared base
  platform/
    android/
      primitive/font-family.tokens.json — theme-independent
      primitive/letter-spacing.tokens.json
      theme/light/elevation.tokens.json — light × android
      theme/dark/elevation.tokens.json — dark × android
```

- A platform file exists **only if** that platform has a difference in
  that category. Mirroring says where a file lives *when it exists* —
  it never demands completeness.
- `platform/<name>/theme/<mode>/…` is the theme×platform matrix cell,
  expressed by position: it applies exactly when that theme *and* that
  platform are active. No conditional reference mechanism is needed.
- Platform names are lowercase full words: `ios`, `android`, `web`.

## 3. Sparse override discipline

- **Identical paths, value-only**: a platform
  file repeats existing base token paths with different values. It MUST
  NOT introduce new token paths, change a `$type`, or alter the
  taxonomy in any way. New paths enter the base tree first.
- **Every token path in a platform file MUST exist in the base** file
  it mirrors, with a matching type.
- **A platform override MUST differ from the base value.** An override
  equal to the base is a gate error — an exception without a difference
  is deleted, so duplicate trees cannot accrete by construction.
- **Aliases propagate platform values.** Aliases resolve after all sets
  merge, so overriding `primitive.fontFamily.text` re-points every semantic and
  component token that references it — downstream tiers are never
  touched to propagate a platform difference.
- Any tier MAY be overridden — primitive (fonts, metrics), semantic,
  theme, component. The mode-invariance rule of the primitive contract
  (§3) restricts *theme and contrast* contexts, not platform: platform
  is a build-time context and MAY override primitive values on
  identical paths.
- **Composite tokens are never overridden whole.** DTCG merges whole
  tokens, so overriding one field of a composite (typography, shadow)
  would duplicate every other field and silently drift when the base
  changes. A composite field that any platform varies MUST be a reference
  to its own primitive (primitive contract §2, addressability path —
  e.g. `letterSpacing`); the
  platform then overrides that primitive, and the cascade updates the
  field. Theme-set composites (`elevation.*.shadow`) are already
  per-theme decisions, not shared bases — a platform MAY override those
  leaves whole.
- A11y-critical leaves stay under the contrast contract: an override
  MUST keep every contrast obligation of the path it overrides.

## 4. Resolvers: base composition plus platform overrides

`default.resolver.json` defines the base composition without platform
overrides. Each platform with overrides has a `<platform>.resolver.json`
that MUST preserve the base sets, modifiers, contexts, defaults, source
order, and resolution order. Resolvers use the DTCG 2025.10 format:

- every set and theme context lists the base refs first, then the
  platform's mirrored refs (later wins on merge):

```json
"contexts": {
  "dark": [
    { "$ref": "theme/dark/color.tokens.json" },
    { "$ref": "theme/dark/elevation.tokens.json" },
    { "$ref": "platform/android/theme/dark/elevation.tokens.json" }
  ]
}
```

- platform resolvers MUST retain the base `theme` and `appearance`
  contexts; platform names MUST NOT be encoded in their context names;
- a resolution uses exactly one resolver and one context per modifier;
- a theme-specific override MUST appear only in its matching theme
  context. An override for `dark` does not implicitly apply to
  `dark-high-contrast`; a context without an override keeps its base
  values.

Adding or removing a base source or context MUST update every platform
resolver's corresponding composition. The only source additions relative
to the base resolver are that platform's applicable mirrored overrides.

## 5. Adding or extending a platform

1. Identify an existing base token whose value needs to differ. If the
   path does not exist, introduce it under the owning tier's contract
   before adding a platform override.
2. Add only the differing leaves to the mirrored file under
   `platform/<name>/`. A directory or file MUST NOT be added without a
   concrete override.
3. Introduce the platform resolver together with its first override, or
   extend its existing resolver. Register each override after the base
   sources in the corresponding set or theme context (§4).
4. Check the criteria in §6 and the resolved combinations affected by
   the override. When a base value changes, recheck its overrides and
   remove any that no longer differ.

## 6. Gates

Every platform change MUST satisfy these conformance criteria:

1. Every file under `platform/<name>/` mirrors an existing base file
   path; orphan overrides are an error.
2. Every token path in a platform file exists in the mirrored base file
   with a matching `$type`.
3. Platform files carry value overrides only: no new paths, no new
   groups, no `$extensions` that change taxonomy.
4. Every override value differs from the base value it shadows.
5. Platform names come from the registered set (`ios`, `android`,
   `web`); a new name enters together with its first override file.
6. Platform resolvers preserve the base composition (§4) and match the
   override tree: every existing platform file is
   referenced by exactly its platform's resolver, after the base ref of
   the same category; no resolver references a non-existent file.
7. Overrides on a11y-critical paths satisfy the contrast contract.
8. No platform file overrides a composite-typed token from the base
   `primitive/` or `semantic/` sets; composite variance goes through the
   referenced field primitive (§3). Theme-set composite leaves
   (`elevation.*.shadow`) are exempt.
