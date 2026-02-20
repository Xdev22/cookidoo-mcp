"""
Converter from standard recipes to Thermomix recipes.

Transforms cooking steps into Thermomix instructions with:
- Speed (1-10, Turbo)
- Temperature (37°C - 120°C)
- Duration
- Reverse mode (spoon)
"""

import re
import unicodedata

from .models import (
    Ingredient,
    ThermomixStep,
    ScrapedRecipe,
    ThermomixRecipe,
    AnnotationPosition,
    TTSAnnotation,
    IngredientAnnotation,
)
from .constants import (
    MIXING_KEYWORDS,
    COOKING_KEYWORDS,
    TURBO_KEYWORDS,
    UNITS_PATTERN,
    UNIT_MAP,
    FRACTION_MAP,
    TOOL_KEYWORDS,
)


def _strip_accents(text: str) -> str:
    """Remove diacritics/accents from text (e.g. 'émincer' -> 'emincer')."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


# Matches TTS patterns: "5 sec/vitesse 5", "2 min/120°C/vitesse 1", "100°C/speed 1"
_TTS_TEXT_RE = re.compile(
    r"\s*\.?\s*"
    r"(?:\d+\s*(?:sec|min|s)\s*/\s*)?"
    r"(?:\d+\s*°C\s*/\s*)?"
    r"(?:vitesse|speed)\s*[\d.]+"
    r"\s*\.?\s*",
    re.IGNORECASE,
)

# Matches old-format TTS in parentheses: "(100°C, speed 1)", "(30 s, speed 3)"
_OLD_TTS_RE = re.compile(
    r"\s*\([^)]*(?:speed|vitesse)\s*[\d.]+[^)]*\)\s*",
    re.IGNORECASE,
)


def _clean_description(text: str) -> str:
    """Clean step description: strip TTS params and normalize wording."""
    text = _OLD_TTS_RE.sub(" ", text)
    text = _TTS_TEXT_RE.sub(" ", text)
    # "dans le Thermomix" / "au Thermomix" → "dans le bol"
    text = re.sub(r"(?:dans|au)\s+(?:le\s+)?thermomix", "dans le bol", text, flags=re.IGNORECASE)
    # "la spatule du Thermomix" → "la spatule"
    text = re.sub(r"du\s+thermomix", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\.\s*\.$", ".", text)
    return text


def _parse_speed_from_text(text: str) -> int | None:
    """Extract a Thermomix speed from free text (e.g. 'vitesse 5')."""
    match = re.search(r"(?:vitesse|speed)\s*([\d.]+)", text, re.IGNORECASE)
    if match:
        return max(1, round(float(match.group(1))))
    return None


def _parse_duration_from_text(text: str) -> int | None:
    """Extract a duration in seconds from free text.

    Args:
        text: The text to parse (e.g. "cuire 30 minutes").

    Returns:
        The duration in seconds, or None if not found.
    """
    text_lower = text.lower()

    # "30 minutes", "10 min"
    match = re.search(r"(\d+)\s*(?:minutes?|min)", text_lower)
    if match:
        return int(match.group(1)) * 60

    # "30 secondes", "10 sec", "10 s", "30 seconds"
    match = re.search(r"(\d+)\s*(?:secondes?|seconds?|sec|s\b)", text_lower)
    if match:
        return int(match.group(1))

    # "1h30", "1 heure 30", "1 hour 30"
    match = re.search(r"(\d+)\s*(?:h(?:eures?|ours?)?)\s*(\d+)?", text_lower)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        return (hours * 60 + minutes) * 60

    return None


def _parse_temperature_from_text(text: str) -> int | None:
    """Extract a temperature in °C from free text.

    Args:
        text: The text to parse (e.g. "cuire à 180°C").

    Returns:
        The temperature clamped to 37-120°C, or None if not found.
    """
    match = re.search(r"(\d+)\s*°\s*[Cc]?", text)
    if match:
        temp = int(match.group(1))
        # Thermomix caps at 120°C
        return min(temp, 120) if temp >= 37 else None
    return None


def _is_varoma_temperature(text: str) -> bool:
    """Check if the text references Varoma temperature.

    Args:
        text: The text to check.

    Returns:
        True if Varoma temperature is referenced.
    """
    return bool(re.search(r"\bvaroma\b", text.lower()))


def _build_tts_annotation_from_step(
    step: "ThermomixStep", locale: str = "fr"
) -> TTSAnnotation | None:
    """Build a TTS annotation from step cooking parameters.

    Creates an annotation positioned at the TTS text appended to the step.

    Args:
        step: The ThermomixStep with cooking parameters.
        locale: Language code for formatting ("fr" or "en").

    Returns:
        A TTSAnnotation or None if no cooking parameters.
    """
    tts_str = step.tts_text(locale)
    if not tts_str:
        return None

    # TTS text is appended after "{description} "
    offset = len(step.description) + 1

    temp_value = None
    if step.is_varoma:
        temp_value = "varoma"
    elif step.temperature:
        temp_value = str(step.temperature)

    speed_str = None
    if step.is_turbo:
        speed_str = "Turbo"
    elif step.speed:
        speed_str = str(step.speed)

    return TTSAnnotation(
        position=AnnotationPosition(offset=offset, length=len(tts_str)),
        speed=speed_str,
        time=step.duration_seconds,
        temperature_value=temp_value,
    )


_QTY_START = r"[\d¼½¾⅓⅔][\d/.,¼½¾⅓⅔]*\s*"


def _french_article(name: str) -> str:
    """Return the French article + lowercased name."""
    low = name[0].lower() + name[1:] if name else name
    vowels = "aeiouyàâéèêëïîôùûüh"
    if low and low[0] in vowels:
        return "l'" + low
    return "le " + low


def _strip_ingredient_quantities(
    text: str, ingredients: list["Ingredient"], locale: str = "fr"
) -> str:
    """Replace ingredient quantities in step text with articles.

    Transforms '200 grammes de boulgour' into 'le boulgour',
    '20 grammes d'huile d'olive' into "l'huile d'olive", etc.
    """
    # Sort by name length (longest first) to avoid partial matches
    sorted_ings = sorted(ingredients, key=lambda i: len(i.name), reverse=True)

    for ing in sorted_ings:
        if not ing.name:
            continue
        name_escaped = re.escape(ing.name)
        # Match: "qty unit de/d' name" or "qty name"
        pattern = (
            _QTY_START
            + r"(?:" + UNITS_PATTERN + r")?\s*"
            + r"(?:de\s+|d['']\s*)?"
            + name_escaped
        )
        if locale.startswith("fr"):
            replacement = _french_article(ing.name)
        else:
            low = ing.name[0].lower() + ing.name[1:]
            replacement = low
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def _find_ingredient_mentions(
    step_text: str, ingredients: list["Ingredient"]
) -> list[IngredientAnnotation]:
    """Find ingredient mentions in step text and create annotations.

    Args:
        step_text: The step description text.
        ingredients: The list of recipe ingredients.

    Returns:
        A list of IngredientAnnotation for each found ingredient.
    """
    annotations = []
    text_lower = step_text.lower()

    for ingredient in ingredients:
        name_lower = ingredient.name.lower()
        # Search for ingredient name in the step text
        idx = text_lower.find(name_lower)
        if idx != -1:
            annotations.append(
                IngredientAnnotation(
                    position=AnnotationPosition(
                        offset=idx, length=len(ingredient.name)
                    ),
                    ingredient=ingredient,
                )
            )

    return annotations


def convert_step(step_text: str, locale: str = "fr") -> ThermomixStep:
    """Convert a standard cooking step into a Thermomix step.

    Args:
        step_text: The original step description.
        locale: Language code for TTS formatting ("fr" or "en").

    Returns:
        A ThermomixStep with speed, temperature, duration, etc.
    """
    text_normalized = _strip_accents(step_text.lower())

    speed = None
    temperature = None
    duration = None
    reverse = False
    is_turbo = False
    is_varoma = _is_varoma_temperature(step_text)

    # Check turbo keywords
    for kw in TURBO_KEYWORDS:
        if kw in text_normalized:
            is_turbo = True
            duration = 15
            break

    if not is_turbo:
        # Check cooking keywords (high priority)
        for keyword, params in COOKING_KEYWORDS.items():
            if keyword in text_normalized:
                speed = params.get("speed", 1)
                temperature = params.get("temp")
                reverse = params.get("reverse", False)
                duration = params.get("duration")
                if params.get("varoma"):
                    is_varoma = True
                break

        # Check mixing keywords
        if speed is None:
            for keyword, params in MIXING_KEYWORDS.items():
                if keyword in text_normalized:
                    speed = params.get("speed", 3)
                    duration = params.get("duration", 30)
                    reverse = params.get("reverse", False)
                    break

    # Override with explicit values found in text
    if not is_varoma:
        text_temp = _parse_temperature_from_text(step_text)
        if text_temp:
            temperature = text_temp

    text_duration = _parse_duration_from_text(step_text)
    if text_duration:
        duration = text_duration

    text_speed = _parse_speed_from_text(step_text)
    if text_speed is not None:
        speed = text_speed

    step = ThermomixStep(
        description=_clean_description(step_text),
        duration_seconds=duration,
        temperature=temperature,
        speed=speed,
        reverse=reverse,
        is_turbo=is_turbo,
        is_varoma=is_varoma,
    )

    # Build TTS annotation from detected parameters
    tts = _build_tts_annotation_from_step(step, locale)
    if tts:
        step.tts_annotations = [tts]

    return step


def _normalize_unit(unit: str | None) -> str | None:
    """Normalize a unit to its short form.

    Args:
        unit: The raw unit string.

    Returns:
        The normalized unit, or None.
    """
    if unit is None:
        return None
    return UNIT_MAP.get(unit.lower(), unit)


def _normalize_quantity(qty: str | None) -> str | None:
    """Convert decimal quantities to fractions where appropriate.

    Args:
        qty: The raw quantity string (e.g. "0.75").

    Returns:
        A human-readable quantity (e.g. "¾").
    """
    if qty is None:
        return None
    qty = qty.strip()

    # Direct match (e.g. "0.5" -> "½")
    if qty in FRACTION_MAP:
        return FRACTION_MAP[qty]

    # Mixed number (e.g. "1.5" -> "1 ½")
    try:
        val = float(qty.replace(",", "."))
        whole = int(val)
        decimal = round(val - whole, 2)
        decimal_str = f"{decimal:.2g}"
        if decimal > 0 and decimal_str in FRACTION_MAP:
            if whole > 0:
                return f"{whole} {FRACTION_MAP[decimal_str]}"
            return FRACTION_MAP[decimal_str]
    except ValueError:
        pass

    return qty


def _parse_numeric_quantity(raw_qty: str | None) -> float | None:
    """Convert a raw quantity string to a numeric value.

    Args:
        raw_qty: The raw quantity (e.g. "200", "1.5", "3/4").

    Returns:
        The numeric value or None.
    """
    if raw_qty is None:
        return None
    try:
        cleaned = raw_qty.replace(",", ".").strip()
        if "/" in cleaned:
            parts = cleaned.split("/")
            return float(parts[0]) / float(parts[1])
        return float(cleaned)
    except (ValueError, ZeroDivisionError):
        return None


def parse_ingredient(raw: str) -> Ingredient:
    """Parse a raw ingredient string into a structured Ingredient.

    Args:
        raw: The raw ingredient text (e.g. "200 g de farine" or "Oignon - 1").

    Returns:
        An Ingredient with quantity, unit, name, and numeric quantity.
    """
    text = raw.strip()

    # Format "Name - quantity unit" (e.g. "Oignon blanc - 1", "Huile d'olive - 20 grammes")
    match = re.match(
        rf"^(.+?)\s*[-–]\s*([\d/.,]+)\s*({UNITS_PATTERN})?\s*$",
        text,
        re.IGNORECASE,
    )
    if match:
        raw_qty = match.group(2)
        return Ingredient(
            name=match.group(1).strip(),
            quantity=_normalize_quantity(raw_qty),
            unit=_normalize_unit(match.group(3)),
            quantity_numeric=_parse_numeric_quantity(raw_qty),
        )

    # Format "quantity unit name" (e.g. "200 g de farine", "3 oeufs", "1 cup flour")
    match = re.match(
        rf"^([\d/.,]+)\s*({UNITS_PATTERN})?\s*(?:de\s+|d['']|of\s+)?\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if match:
        raw_qty = match.group(1)
        return Ingredient(
            quantity=_normalize_quantity(raw_qty),
            unit=_normalize_unit(match.group(2)),
            name=match.group(3).strip(),
            quantity_numeric=_parse_numeric_quantity(raw_qty),
        )

    return Ingredient(name=text)


def _detect_tools(instructions: list[str]) -> list[str]:
    """Detect required tools and accessories from recipe instructions.

    Args:
        instructions: The list of recipe step texts.

    Returns:
        A list of tool names (always includes TM7).
    """
    tools = ["TM7"]
    text = _strip_accents(" ".join(instructions).lower())

    for tool_name, keywords in TOOL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tools.append(tool_name)

    return tools


def convert_recipe(scraped: ScrapedRecipe, locale: str = "fr") -> ThermomixRecipe:
    """Convert a scraped recipe into a full Thermomix recipe.

    Args:
        scraped: The raw scraped recipe data.
        locale: Language code ("fr" or "en") for ingredient formatting.

    Returns:
        A ThermomixRecipe ready for Cookidoo upload.
    """
    ingredients = [parse_ingredient(ing) for ing in scraped.ingredients]
    steps = [convert_step(step, locale) for step in scraped.instructions]

    # Strip ingredient quantities from step descriptions and link annotations
    for step in steps:
        step.description = _strip_ingredient_quantities(
            step.description, ingredients, locale
        )
        step_text = step.to_text(locale)
        ing_annotations = _find_ingredient_mentions(step_text, ingredients)
        step.ingredient_annotations = ing_annotations

    hints = []
    if scraped.source_url:
        hints.append(f"Original recipe: {scraped.source_url}")

    tools = _detect_tools(scraped.instructions)

    return ThermomixRecipe(
        name=scraped.title,
        ingredients=ingredients,
        steps=steps,
        servings=scraped.servings or 4,
        prep_time_minutes=scraped.prep_time or 15,
        total_time_minutes=scraped.total_time or 45,
        hints=hints,
        tools=tools,
        source_url=scraped.source_url,
        locale=locale,
    )
