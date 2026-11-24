# KrushiMitra AI — Dataset Strategy & Data Moat

> The moat is **not** the AI. It's the founder's trusted, direct access to Maharashtra farmers
> (via his father) growing the exact 3 crops. This doc turns that access into a proprietary dataset
> before competitors notice. That is the whole game.

## Public seed datasets (bootstrap detection only)
- **Soybean:** *Soybean Leaf Disease* sets (Kaggle, Mendeley Data); PlantDoc (limited).
- **Pomegranate:** Mendeley "Pomegranate fruit/leaf disease" sets; Kaggle pomegranate disease sets.
- **Onion:** sparsest publicly → rely most on own collection (also where the moat is strongest).
- **General:** PlantVillage (clean but lab-condition; use to *pretrain*, not to trust in-field).

> **Honest caveat:** public sets are lab-condition and class-imbalanced → demo-grade detector, not
> field-grade. Field data from the farmer network is what makes it real.

## The collection flywheel (the unfair advantage)
1. Every farmer photo stored with crop + location + date → free in-field data.
2. In-app **thumbs up/down + "what was it really?"** correction → cheap labels (`expert_labels`, `feedback`).
3. **Father + 2–3 local agronomists / KVK contacts** grade a subset for **severity** (paid per-label or
   goodwill) → proprietary severity labels nobody else has.
4. **Longitudinal capture:** the crop-twin nudges re-photographing the same plot every ~15 days →
   disease **progression sequences** — the rarest, most valuable agri data in existence.

## Severity labeling strategy
- Start with **ordinal 5-class** (Healthy/Mild/Moderate/Severe/Critical) via a phone-friendly sheet.
- Graduate to **lesion segmentation masks** (CVAT, self-hosted/free) once an agronomist can spend ~1 hr/week.
- `severity_pct = diseased_leaf_area / total_leaf_area` from masks → explainable severity.

## Annotation strategy
- Tooling: CVAT (free) for masks; a lightweight in-house web form for ordinal labels.
- Maintain a **held-out, expert-verified gold test set per crop from day one** — never train on it.
- Track inter-annotator agreement once >1 labeler.

## Farmer data-collection strategy
- Recruit first 10–100 farmers through the father's network; onboard in person/WhatsApp.
- Incentivize photos with immediate value (free advice) — collection is a side effect of usefulness.
- Capture metadata cheaply: crop + sowing date at cycle creation; GPS from device; stage derived.

## Data moat thesis
> "The largest field-condition, longitudinally-tracked, severity-labeled image dataset for
> **onion / soybean / pomegranate in Maharashtra**."

Defensible because it (a) compounds with usage, (b) is region- and crop-specific — exactly where
DeHaat/AgroStar/Plantix/Cropin/Fasal are thin — and (c) includes progression over time, which
one-shot detection apps never capture.

See also: [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) (how the data trains the models).

## Field context and split integrity (added 2026-11-13)

Every `/vision/diagnose` call may carry a `context` object. It is optional on the wire so an older
app build keeps working, but it is what separates a training example from a photograph.

| Field | Why it has to be captured at the time, not later |
|---|---|
| `plot_id` / `farmer_id` | **The split group.** One plot photographed weekly is the *same plant*. Without a grouping key those photos land in both train and test, and the measured accuracy is fiction. There is no way to reconstruct the grouping afterwards. |
| `sowing_date` | Fixes the crop's age (`days_after_sowing` is derived at capture). Purple blotch at 30 days and at 90 days call for different advice. |
| `district` / `taluka` / `lat` / `lon` | Disease pressure is regional — Nashik onion is not Solapur onion. Also the join key to weather. |
| `device_model` | Camera quality is a real domain shift. Accuracy on a ₹6,000 phone is not accuracy on a flagship. |

**Grouping rule** (`capture.normalize_context`): prefer `plot:<plot_id>`, fall back to
`farmer:<farmer_id>`, otherwise `None`. Two plots of one farmer are genuinely different fields, so
the plot is the tighter and more correct group.

**Privacy.** `farmer_id` is an anonymous per-install random id — never a phone number, name or
device identifier. Coordinates are rounded to 3 decimal places (~110 m) *before* they are written
to disk: enough to map disease pressure onto a village, not enough to point at a household.
Precision that is never stored cannot later leak.

**Watch `not_splittable`.** `GET /vision/dataset` reports `splittable`, `not_splittable`,
`distinct_plots`, `distinct_farmers`, `with_location` and `with_sowing_date` alongside the raw
count. A growing `not_splittable` means the app has stopped sending context and the data arriving
is worth a fraction of what it looks like.
