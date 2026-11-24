"""Closed disease taxonomy for the 3 active crops — the backbone of an honest diagnosis.

Why a closed label set matters:
  * A vision model asked an open question ("what disease is this?") will confabulate a
    plausible-sounding disease name every time. Asked to pick from a fixed menu — with
    `unknown` and `not_a_plant` as first-class options — it can decline, which is exactly
    the behaviour the product promises ("if it doesn't know, it must say so").
  * Every slug here has a matching entry in `app/services/knowledge.py`, so treatment is
    looked up by the DETECTED DISEASE, never by the crop the farmer happened to tap.

`signs` is sent to the model as part of the menu. It is visual grounding, not training: it
tells an un-fine-tuned VLM what distinguishes each option, which is the single cheapest way
to lift accuracy before we have our own labelled field data. Keep each one to the symptoms a
farmer can actually see in a phone photo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --- Kinds (drives the treatment framing: fungicide vs bactericide vs insecticide vs none) ---
FUNGAL = "fungal"
BACTERIAL = "bacterial"
VIRAL = "viral"
PEST = "pest"
ABIOTIC = "abiotic"
NONE = "none"


@dataclass(frozen=True)
class DiseaseLabel:
    slug: str          # canonical id; also the knowledge-base key
    en: str            # English name (shown as secondary text in the app)
    mr: str            # Marathi name (the primary thing the farmer reads)
    kind: str
    signs: str         # visual signs, English — sent to the model as grounding


# --- Crop-agnostic outcomes. These exist so the model can refuse. ---
HEALTHY = DiseaseLabel(
    slug="healthy",
    en="Healthy",
    mr="निरोगी पीक",
    kind=NONE,
    signs=(
        "no lesions, spots, pustules, wilting, chewing damage or discolouration; "
        "foliage uniformly green and intact"
    ),
)
UNKNOWN = DiseaseLabel(
    slug="unknown",
    en="Not identified",
    mr="निदान निश्चित नाही",
    kind=NONE,
    signs=(
        "symptoms are visible but match none of the listed options, OR the photo is too "
        "blurry, dark, distant or partial to judge confidently"
    ),
)
NOT_A_PLANT = DiseaseLabel(
    slug="not_a_plant",
    en="No crop in photo",
    mr="फोटोत पीक दिसत नाही",
    kind=NONE,
    signs="the photo does not show a crop plant (a person, soil, sky, animal, document or object)",
)

GLOBAL_LABELS: tuple[DiseaseLabel, ...] = (HEALTHY, UNKNOWN, NOT_A_PLANT)


# --- Onion (कांदा) ---
_ONION: tuple[DiseaseLabel, ...] = (
    DiseaseLabel(
        "onion_purple_blotch", "Purple Blotch", "जांभळा करपा", FUNGAL,
        "small white sunken flecks enlarging into purple-brown oval lesions with concentric "
        "rings and a yellow halo; leaf tips die back and collapse",
    ),
    DiseaseLabel(
        "onion_stemphylium_blight", "Stemphylium Blight", "स्टेम्फिलियम करपा", FUNGAL,
        "yellow-orange streaks that become elongated spindle-shaped dark olive-brown to black "
        "lesions, usually starting at the leaf tip and moving down; whole leaf collapses",
    ),
    DiseaseLabel(
        "onion_downy_mildew", "Downy Mildew", "केवडा (डाउनी मिल्ड्यू)", FUNGAL,
        "pale green to yellow oval patches bearing fuzzy violet-grey growth visible in morning "
        "dew; affected leaves bend over and collapse",
    ),
    DiseaseLabel(
        "onion_anthracnose_twister", "Anthracnose / Twister", "करपा–पीळ (ट्विस्टर)", FUNGAL,
        "curling, twisting and yellowing of leaves with an abnormally long slender neck; "
        "pink-orange spore masses arranged in concentric rings",
    ),
    DiseaseLabel(
        "onion_basal_rot", "Fusarium Basal Rot", "मूळकूज (बेसल रॉट)", FUNGAL,
        "yellowing and dieback from the leaf tips, white mould at the bulb base, rotted roots; "
        "the bulb lifts away from its base plate easily",
    ),
    DiseaseLabel(
        "onion_thrips", "Thrips", "फुलकिडे (थ्रिप्स)", PEST,
        "silvery-white streaks and blotches on leaves with curling and distortion; tiny slender "
        "insects hiding in leaf axils plus black specks of frass",
    ),
    DiseaseLabel(
        "onion_iris_yellow_spot", "Iris Yellow Spot Virus", "आयरिस यलो स्पॉट विषाणू", VIRAL,
        "diamond-shaped or straw-coloured chlorotic lesions on scapes and leaves, often with "
        "green centres; thrips usually present",
    ),
    DiseaseLabel(
        "onion_nutrient_deficiency", "Nutrient Deficiency", "अन्नद्रव्यांची कमतरता", ABIOTIC,
        "uniform pale-yellow or purplish leaves with NO spots, rings or fungal growth; the whole "
        "plant is evenly affected rather than patchy",
    ),
)

# --- Soybean (सोयाबीन) ---
_SOYBEAN: tuple[DiseaseLabel, ...] = (
    DiseaseLabel(
        "soybean_rust", "Soybean Rust", "तांबेरा (रस्ट)", FUNGAL,
        "small grey-brown angular lesions on the LOWER leaf surface bearing raised tan pustules "
        "that shed powdery spores; rapid defoliation from the lower canopy upward",
    ),
    DiseaseLabel(
        "soybean_bacterial_blight", "Bacterial Blight", "जिवाणूजन्य करपा", BACTERIAL,
        "small angular water-soaked spots turning brown with a yellow halo and a narrow "
        "translucent margin; dried centres tear away leaving ragged holes",
    ),
    DiseaseLabel(
        "soybean_frogeye_leaf_spot", "Frogeye Leaf Spot", "फ्रॉगआय ठिपके", FUNGAL,
        "circular spots with grey to light-brown centres ringed by a distinct reddish-brown "
        "border, scattered across the upper leaf surface",
    ),
    DiseaseLabel(
        "soybean_yellow_mosaic", "Yellow Mosaic Virus", "पिवळा मोझॅक विषाणू", VIRAL,
        "bright yellow mottling and mosaic patches alternating with green, puckered distorted "
        "leaves and a stunted plant; whiteflies usually present",
    ),
    DiseaseLabel(
        "soybean_anthracnose", "Anthracnose", "करपा (अँथ्रॅक्नोज)", FUNGAL,
        "irregular brown blotches on stems and pods studded with tiny black spine-like "
        "structures; pod blight and stem cankers",
    ),
    DiseaseLabel(
        "soybean_charcoal_rot", "Charcoal Rot", "चारकोल रॉट", FUNGAL,
        "wilting during dry heat with a light-grey discoloured stem bearing numerous tiny black "
        "specks under the skin near the soil line",
    ),
    DiseaseLabel(
        "soybean_girdle_beetle", "Girdle Beetle", "खोडकिडा (गर्डल बीटल)", PEST,
        "two neat parallel rings cut right around the stem or petiole; everything above the "
        "girdle dries and droops while the rest stays green",
    ),
    DiseaseLabel(
        "soybean_defoliator", "Leaf-eating Caterpillar", "पाने खाणारी अळी", PEST,
        "chewed irregular holes and skeletonised leaves with caterpillars and droppings present; "
        "no rings, halos or pustules",
    ),
)

# --- Pomegranate (डाळिंब) ---
_POMEGRANATE: tuple[DiseaseLabel, ...] = (
    DiseaseLabel(
        "pomegranate_bacterial_blight", "Bacterial Blight (Telya)", "तेल्या रोग", BACTERIAL,
        "small water-soaked oily dark spots with a yellow halo on leaves; on fruit, greasy "
        "dark brown-black irregular patches that crack in an L or Y shape; black nodal cankers "
        "on twigs",
    ),
    DiseaseLabel(
        "pomegranate_cercospora_leaf_spot", "Cercospora Leaf & Fruit Spot", "सरकोस्पोरा ठिपके", FUNGAL,
        "small reddish-brown to black irregular spots with a slightly raised margin on leaves "
        "and fruit, heavy leaf fall and blackening of twigs",
    ),
    DiseaseLabel(
        "pomegranate_anthracnose", "Anthracnose", "करपा (अँथ्रॅक्नोज)", FUNGAL,
        "dark sunken circular lesions on the fruit showing concentric pinkish-orange spore "
        "masses; leaf spots with greyish centres",
    ),
    DiseaseLabel(
        "pomegranate_wilt", "Pomegranate Wilt", "मर रोग (विल्ट)", FUNGAL,
        "yellowing and wilting of one branch or the whole plant with dry leaves still clinging; "
        "brown discoloured vascular tissue inside the stem or root; slow decline",
    ),
    DiseaseLabel(
        "pomegranate_fruit_borer", "Fruit Borer", "फळ पोखरणारी अळी", PEST,
        "a single round bore hole in the fruit with frass and excreta oozing out; the fruit rots "
        "internally while the skin looks mostly intact",
    ),
    DiseaseLabel(
        "pomegranate_thrips", "Thrips", "फुलकिडे (थ्रिप्स)", PEST,
        "scabby silvery-brown corky russeting over the fruit skin and curled deformed young "
        "leaves; NO water-soaked spots and no ooze",
    ),
    DiseaseLabel(
        "pomegranate_mealybug_scale", "Mealybug / Scale", "मिलीबग / खवले कीड", PEST,
        "white cottony masses or brown scale encrustations on twigs and the fruit calyx with "
        "sticky honeydew and black sooty mould",
    ),
    DiseaseLabel(
        "pomegranate_sunscald", "Sunscald", "उन्हाचा चटका (सनस्काल्ड)", ABIOTIC,
        "a pale bleached tan patch confined to the sun-exposed side of the fruit, leathery and "
        "dry; leaves carry no spots and there is no ooze",
    ),
)

CROP_LABELS: dict[str, tuple[DiseaseLabel, ...]] = {
    "onion": _ONION,
    "soybean": _SOYBEAN,
    "pomegranate": _POMEGRANATE,
}

ALL_LABELS: dict[str, DiseaseLabel] = {
    label.slug: label
    for group in (*CROP_LABELS.values(), GLOBAL_LABELS)
    for label in group
}


def labels_for(crop: str | None) -> tuple[DiseaseLabel, ...]:
    """The menu the model must choose from: the crop's diseases + healthy/unknown/not_a_plant.

    With no crop selected we offer every disease we know — less precise, but the farmer is not
    forced to classify their own plant before getting an answer.
    """
    if crop and crop in CROP_LABELS:
        specific = CROP_LABELS[crop]
    else:
        specific = tuple(label for group in CROP_LABELS.values() for label in group)
    return specific + GLOBAL_LABELS


def prompt_menu(crop: str | None) -> str:
    """Render the label menu for the model prompt — slug, English name, and visual signs."""
    return "\n".join(f"- {label.slug} ({label.en}): {label.signs}" for label in labels_for(crop))


def _normalise(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")


# Free-text the model (or a future dataset) may emit, mapped onto canonical slugs.
_ALIASES: dict[str, str] = {
    "purple_blotch": "onion_purple_blotch",
    "alternaria_porri": "onion_purple_blotch",
    "alternaria_leaf_blight": "onion_purple_blotch",
    "stemphylium_blight": "onion_stemphylium_blight",
    "stemphylium_leaf_blight": "onion_stemphylium_blight",
    "downy_mildew": "onion_downy_mildew",
    "twister_disease": "onion_anthracnose_twister",
    "onion_twister": "onion_anthracnose_twister",
    "basal_rot": "onion_basal_rot",
    "fusarium_basal_rot": "onion_basal_rot",
    "thrips": "onion_thrips",
    "iris_yellow_spot_virus": "onion_iris_yellow_spot",
    "iysv": "onion_iris_yellow_spot",
    "nutrient_deficiency": "onion_nutrient_deficiency",
    "rust": "soybean_rust",
    "soybean_rust": "soybean_rust",
    "phakopsora_pachyrhizi": "soybean_rust",
    "frogeye_leaf_spot": "soybean_frogeye_leaf_spot",
    "frog_eye_leaf_spot": "soybean_frogeye_leaf_spot",
    "cercospora_sojina": "soybean_frogeye_leaf_spot",
    "yellow_mosaic": "soybean_yellow_mosaic",
    "yellow_mosaic_virus": "soybean_yellow_mosaic",
    "mymv": "soybean_yellow_mosaic",
    "charcoal_rot": "soybean_charcoal_rot",
    "macrophomina_phaseolina": "soybean_charcoal_rot",
    "girdle_beetle": "soybean_girdle_beetle",
    "stem_borer": "soybean_girdle_beetle",
    "defoliator": "soybean_defoliator",
    "leaf_eating_caterpillar": "soybean_defoliator",
    "semilooper": "soybean_defoliator",
    "spodoptera": "soybean_defoliator",
    "telya": "pomegranate_bacterial_blight",
    "bacterial_blight": "pomegranate_bacterial_blight",
    "xanthomonas_axonopodis": "pomegranate_bacterial_blight",
    "cercospora_leaf_spot": "pomegranate_cercospora_leaf_spot",
    "cercospora_punicae": "pomegranate_cercospora_leaf_spot",
    "wilt": "pomegranate_wilt",
    "pomegranate_fruit_rot": "pomegranate_anthracnose",
    "fruit_borer": "pomegranate_fruit_borer",
    "anar_butterfly": "pomegranate_fruit_borer",
    "mealybug": "pomegranate_mealybug_scale",
    "scale_insect": "pomegranate_mealybug_scale",
    "sunscald": "pomegranate_sunscald",
    "sunburn": "pomegranate_sunscald",
    "anthracnose": "pomegranate_anthracnose",
    "colletotrichum": "pomegranate_anthracnose",
    "no_disease": "healthy",
    "none": "healthy",
    "healthy_plant": "healthy",
    "not_identified": "unknown",
    "uncertain": "unknown",
    "unclear": "unknown",
    "unidentified": "unknown",
    "other": "unknown",
    "no_plant": "not_a_plant",
    "not_plant": "not_a_plant",
    "no_crop": "not_a_plant",
    "irrelevant_image": "not_a_plant",
}


def resolve(raw: str | None, crop: str | None = None) -> DiseaseLabel:
    """Map whatever the model returned onto a canonical label. Never guesses — falls back to UNKNOWN.

    Resolution order: exact slug -> crop-prefixed slug -> alias table -> crop-scoped alias ->
    English-name match within the crop. Anything unrecognised becomes UNKNOWN, which makes the
    endpoint abstain rather than invent a disease.
    """
    if not raw:
        return UNKNOWN

    key = _normalise(raw)
    if key in ALL_LABELS:
        return ALL_LABELS[key]

    if crop:
        prefixed = f"{_normalise(crop)}_{key}"
        if prefixed in ALL_LABELS:
            return ALL_LABELS[prefixed]

    # Alias, preferring one that belongs to the selected crop (e.g. "anthracnose" differs by crop).
    if crop:
        crop_slugs = {label.slug for label in CROP_LABELS.get(crop, ())}
        for alias, slug in _ALIASES.items():
            if alias == key and slug in crop_slugs:
                return ALL_LABELS[slug]
        # "anthracnose" on onion -> onion_anthracnose_twister, on soybean -> soybean_anthracnose
        for slug in crop_slugs:
            if slug.endswith(f"_{key}") or key in slug.split("_", 1)[-1].split("_"):
                return ALL_LABELS[slug]

    if key in _ALIASES:
        return ALL_LABELS[_ALIASES[key]]

    for label in labels_for(crop):
        if _normalise(label.en) == key:
            return label

    return UNKNOWN
