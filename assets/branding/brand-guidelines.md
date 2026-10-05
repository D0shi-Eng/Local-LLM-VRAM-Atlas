# Atlas Visual Identity — Brand Guidelines

Original identity work for the **Local LLM VRAM Atlas** repository.
This document defines the visual system and its usage rules.

> Read the Arabic counterpart: [الهوية البصرية لدليل الأطلس](brand-guidelines_AR.md)

---

## 1. Brand concept

The mark is a **stratified atlas plate resolving into a memory die**.

An *atlas* is a layered, cross-referenced map rather than a list. An *atlas of
local models* therefore has to be legible in two directions at once: horizontally,
by capability; vertically, by **memory capacity**. The mark encodes both, plus the
project's central engineering stance — **capacity is a boundary, and evidence is
what tells you where you stand relative to it.**

| Element | Meaning | Engineering justification |
|---|---|---|
| Four horizontal strata | The four VRAM tiers: 4 / 8 / 12 / 16 GB | Tier ladder is the project's primary axis of analysis |
| Upper stratum densest | 4 GB is the most constrained tier | Visually encodes constraint without adding a label |
| Notched aperture on the leading edge | VRAM capacity boundary | Fit is a boundary condition, not a score |
| Vertical bus | Architecture-aware memory model | The single component that links tiers to models |
| Bus cap in amber | The Atlas memory model itself | Single point of technical authority |
| Node lattice | Canonical model records | The catalog is the product; the tooling serves it |
| Opacity steps in the lattice | Partial evidence coverage | Coverage is visibly uneven, and the mark admits it |
| Two amber evidence markers | Strata carrying recorded evidence | Evidence exists where it exists, and nowhere else |

**Design position.** Atlas does not sell certainty. The mark therefore contains no
trophy, no crown, no checkmark, no medal, and no ranking arrow. It shows structure
and the location of evidence, and it leaves the gaps visible.

---

## 2. Colour system

Restrained, technical, and deliberately non-promotional. Two neutrals, one
structural ramp, one accent.

### Structural ramp — "Atlas Blue"

A single-hue ramp descending in luminance from the constrained tier to the
unconstrained tier. Monotonic luminance means the tier order survives greyscale
printing and low-quality displays.

| Token | Light variant | Dark variant | Use |
|---|---|---|---|
| `atlas-plate` | `#0F1620` | `#05090E` | Plate substrate |
| `atlas-4gb` | `#3E7CB1` | `#2C5C88` | 4 GB stratum |
| `atlas-8gb` | `#2F5F8F` | `#234A72` | 8 GB stratum |
| `atlas-12gb` | `#24486E` | `#1B3A5C` | 12 GB stratum |
| `atlas-16gb` | `#1B3552` | `#142B46` | 16 GB stratum |
| `atlas-rule` | `#7FA8C9` | `#9FC3DE` | Plate outline |
| `atlas-record` | `#DCE7F1` | `#E7F0F8` | Record lattice |

### Accent — "Evidence Amber"

| Token | Light variant | Dark variant | Use |
|---|---|---|---|
| `atlas-evidence` | `#E8B45A` | `#F0C070` | Evidence markers only |

**Accent budget.** Amber is reserved for evidence. If amber appears anywhere in a
derived asset, that element must be traceable to a recorded evidence state. Using
it decoratively breaks the meaning of the system.

### Surfaces

| Token | Value | Use |
|---|---|---|
| `atlas-surface` | `#0B1119` | Banner and documentation header background |
| `atlas-grid` | `#16202C` | Banner grid ruling |
| `atlas-text-muted` | `#6E8AA3` | Secondary banner text |
| `atlas-text-faint` | `#5F7A93` | Tertiary banner text |

### Forbidden

- No gradients. Layered flat strata carry the depth; gradients would soften a
  system whose entire purpose is sharp distinctions.
- No third-party brand colours, marks, or logo geometry.
- No red/green "pass/fail" pair. A missing evidence state is **absent**, not failed.
- No colour outside the tokens above.

---

## 3. Typography

The repository renders in two scripts, so the type system is deliberately generic
and requires no webfont fetch.

| Context | Stack |
|---|---|
| Banner and image text | `'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif` |
| README headings | Repository default (GitHub) |
| README body and code | Repository default (GitHub) |
| Arabic body text | Repository default (GitHub) — do **not** force a font |

**Banner rules.** Wordmark: 600 weight, `letter-spacing: 3`. Tagline: 400 weight,
`letter-spacing: 0.4`. Labels: 400 weight, `letter-spacing: 1.2`, uppercase only for
tier labels (`4 GB`, `8 GB`, `12 GB`, `16 GB`).

### Why the banner carries Latin script only

An SVG embedded through an `<img>` element is rasterised by the host renderer.
Arabic shaping, ligature formation and bidi reordering are **not guaranteed** across
those renderers, and a broken or reordered Arabic wordmark is a worse outcome than
no Arabic wordmark.

Therefore:

- `banner.svg` contains **Latin script only**.
- The Arabic project name and Arabic tagline are set as **styled text in the README**,
  where the browser performs shaping with full font support.
- Any future image that must carry Arabic has to be exported through a shaping-aware
  rasteriser (see §6) and verified visually before use.

This is a deliberate engineering constraint, not an oversight.

---

## 4. Assets

| File | Purpose | Size |
|---|---|---|
| `icon.svg` | Repository icon, light-surface default | 128 × 128 |
| `icon-dark.svg` | Repository icon, dark-surface variant | 128 × 128 |
| `banner.svg` | README header and social-preview source | 1280 × 360 |
| `brand-guidelines.md` | This document | — |
| `brand-guidelines_AR.md` | Arabic counterpart | — |

### Icon construction rules

- All geometry sits on a **4 px sub-grid** inside a `0 0 128 128` viewBox.
- Minimum feature size is **2 px** at native scale, so the mark stays clean at 32 px.
- Stratum order is fixed: `4 GB` at the top, `16 GB` at the bottom. Reversing the
  ladder inverts the meaning of the mark.
- Do not scale non-uniformly. Do not rotate. Do not add drop shadows.
- When the mark appears on a surface that is neither near-white nor near-black,
  place it on an `atlas-plate` backing rectangle for contrast.

### Banner construction rules

- Aspect ratio is fixed at **1280 × 360** (16 : 4.5).
- Safe area: keep content inside a **48 px** inset on every edge.
- Text minimum size is **13 px** at native scale.
- The tier band is informational. It must not be redrawn as a progress bar, a
  gauge, or a score.

---

## 5. Honest-claims rule for visual assets

Any asset in this directory, and any derivative asset, must satisfy the same rule
as the documentation:

- No badge, tick, seal, or caption may state or imply that Atlas has verified a
  strict fit for any VRAM tier. **Atlas currently reports zero strict recommendations
  at 4, 8, 12 and 16 GB**, and no asset may contradict that.
- No asset may imply model coverage completeness, a ranking, or a "best model" claim.
- No asset may present popularity signals (downloads, likes, trending) as quality.
- No asset may use security language beyond what is measurable.

If an asset cannot be made honest by editing the asset, the asset is not made.

---

## 6. Export requirements

The repository ships vector-first. Two raster exports are required for GitHub
features that do not accept SVG:

| Target | Required format | Dimensions |
|---|---|---|
| Repository icon (profile avatar) | PNG | 128 × 128 |
| Social preview card | PNG or JPG | 1280 × 640 |

Export from the vector sources with any shaping-aware rasteriser, for example:

```bash
# Inkscape — icon
inkscape assets/branding/icon.svg --export-type=png \
  --export-width=128 --export-height=128 \
  --export-filename=assets/branding/icon.png

# Inkscape — social preview (source art is 1280x360; place it on the brand surface)
inkscape assets/branding/banner.svg --export-type=png \
  --export-width=1280 --export-height=640 \
  --export-background="#0B1119" \
  --export-filename=assets/branding/social-preview.png
```

Then upload through repository settings rather than committing the PNG, unless a
raster file is deliberately wanted in-tree. Keep the repository tree vector-only
by default.

---

## 7. Naming and tone

- Asset filenames are lowercase and hyphenated: `icon.svg`, `icon-dark.svg`,
  `banner.svg`.
- Variant suffixes are functional, never ornamental: `-dark`, `-light`, `-compact`.
- Any new variant must ship with a usage rule in this document. An undocumented
  variant is not part of the identity.

---

## 8. Quick reference

```
Primary mark          assets/branding/icon.svg          (light surface)
Dark-surface mark     assets/branding/icon-dark.svg    (dark surface)
Header / preview      assets/branding/banner.svg        1280 x 360
Accent                #E8B45A light  /  #F0C070 dark   — evidence only
Structural ramp       #3E7CB1 -> #1B3552 light         — 4 GB -> 16 GB
Grid                  4 px sub-grid inside 128 x 128
Stratum order         4 GB (top)  ->  16 GB (bottom)   — never reversed
Gradients             not permitted
Third-party marks     not permitted
Strict-fit badges     not permitted
```