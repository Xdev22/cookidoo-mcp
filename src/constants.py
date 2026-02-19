"""
Constants for Thermomix recipe conversion.

Keyword dictionaries, unit patterns, and mapping tables used by the converter.
"""

# ---------------------------------------------------------------------------
# Keyword-to-Thermomix-parameter mappings for mixing actions
# ---------------------------------------------------------------------------
MIXING_KEYWORDS = {
    # French — sources: doc Vorwerk, recettes Cookidoo officielles
    "melanger": {"speed": 3, "duration": 30},
    "mixer": {"speed": 8, "duration": 30},
    "battre": {"speed": 4, "duration": 45},
    "fouetter": {"speed": 4, "duration": 60},
    "petrir": {"speed": 6, "duration": 120},        # dough mode, speed 6 = approx
    "hacher": {"speed": 5, "duration": 5},
    "emincer": {"speed": 5, "duration": 5},
    "pulveriser": {"speed": 10, "duration": 15},
    "broyer": {"speed": 10, "duration": 30},
    "raper": {"speed": 5, "duration": 10},
    "concasser": {"speed": 5, "duration": 10},
    "incorporer": {"speed": 3, "duration": 30, "reverse": True},
    "remuer": {"speed": 1, "duration": 60, "reverse": True},   # spoon speed
    "touiller": {"speed": 1, "duration": 30, "reverse": True},  # spoon speed
    # English
    "mix": {"speed": 3, "duration": 30},
    "blend": {"speed": 8, "duration": 30},
    "beat": {"speed": 4, "duration": 45},
    "whisk": {"speed": 4, "duration": 60},
    "whip": {"speed": 4, "duration": 60},
    "knead": {"speed": 6, "duration": 120},
    "chop": {"speed": 5, "duration": 5},
    "dice": {"speed": 5, "duration": 5},
    "slice": {"speed": 5, "duration": 5},
    "mince": {"speed": 5, "duration": 5},
    "grind": {"speed": 10, "duration": 30},
    "grate": {"speed": 5, "duration": 10},
    "shred": {"speed": 5, "duration": 10},
    "crush": {"speed": 5, "duration": 10},
    "puree": {"speed": 8, "duration": 30},
    "fold": {"speed": 3, "duration": 30, "reverse": True},
    "combine": {"speed": 3, "duration": 30},
    "stir": {"speed": 1, "duration": 60, "reverse": True},
    "emulsify": {"speed": 4, "duration": 30},
}

# ---------------------------------------------------------------------------
# Keyword-to-Thermomix-parameter mappings for cooking actions
# ---------------------------------------------------------------------------
COOKING_KEYWORDS = {
    # French — sources: doc Vorwerk, recettes Cookidoo officielles
    "cuire": {"speed": 1, "temp": 100},
    "mijoter": {"speed": 1, "temp": 90, "reverse": True},
    "rissoler": {"speed": 1, "temp": 120},
    "sauter": {"speed": 1, "temp": 120},
    "saute": {"speed": 1, "temp": 120},
    "revenir": {"speed": 1, "temp": 120, "reverse": True},
    "faire revenir": {"speed": 1, "temp": 120, "reverse": True},
    "dorer": {"speed": 1, "temp": 120, "reverse": True},
    "fondre": {"speed": 1, "temp": 50},
    "faire fondre": {"speed": 1, "temp": 50},
    "chauffer": {"speed": 2, "temp": 90},
    "rechauffer": {"speed": 2, "temp": 70},
    "bouillir": {"speed": 1, "temp": 100},
    "fremir": {"speed": 1, "temp": 90},
    "porter a ebullition": {"speed": 1, "temp": 100},
    "blanchir": {"speed": 1, "temp": 100},
    "braiser": {"speed": 1, "temp": 100, "reverse": True},
    "compoter": {"speed": 1, "temp": 90, "reverse": True},
    "confire": {"speed": 1, "temp": 80, "reverse": True},
    "carameliser": {"speed": 2, "temp": 120},
    "vapeur": {"speed": 1, "temp": 100, "varoma": True},
    # English
    "cook": {"speed": 1, "temp": 100},
    "simmer": {"speed": 1, "temp": 90, "reverse": True},
    "sear": {"speed": 1, "temp": 120},
    "fry": {"speed": 1, "temp": 120},
    "brown": {"speed": 1, "temp": 120, "reverse": True},
    "melt": {"speed": 1, "temp": 50},
    "heat": {"speed": 2, "temp": 90},
    "warm": {"speed": 2, "temp": 70},
    "reheat": {"speed": 2, "temp": 70},
    "boil": {"speed": 1, "temp": 100},
    "bring to a boil": {"speed": 1, "temp": 100},
    "blanch": {"speed": 1, "temp": 100},
    "braise": {"speed": 1, "temp": 100, "reverse": True},
    "caramelize": {"speed": 2, "temp": 120},
    "steam": {"speed": 1, "temp": 100, "varoma": True},
    "roast": {"speed": 1, "temp": 120},
    "reduce": {"speed": 1, "temp": 100},
    "poach": {"speed": 1, "temp": 80},
    "scald": {"speed": 1, "temp": 90},
}

# ---------------------------------------------------------------------------
# Keywords that trigger Turbo mode
# ---------------------------------------------------------------------------
TURBO_KEYWORDS = {
    # French
    "mixer finement", "reduire en poudre", "glace pilee",
    # English
    "crush ice", "grind to powder", "finely blend",
}

# ---------------------------------------------------------------------------
# Ingredient unit regex pattern (used by parse_ingredient)
# ---------------------------------------------------------------------------
UNITS_PATTERN = (
    # EN units (longer patterns first to avoid partial matches)
    r"tablespoons?|tbsp|teaspoons?|tsp|cups?|ounces?|oz|pounds?|lbs?"
    r"|pinch|slices?|leaves?|cloves?|bunch|sprigs?|sticks?|cans?|pieces?"
    # FR units
    r"|grammes?|kilogrammes?|litres?|kg|ml|cl|g"
    r"|c\.\s*à\s*[sc]|cuillère[s]?\s*à\s*\w+|pincée[s]?|sachet[s]?|tranche[s]?|feuille[s]?"
    # Single-letter units last (l must not match lb)
    r"|l\b"
)

# ---------------------------------------------------------------------------
# Normalize verbose units to short form
# ---------------------------------------------------------------------------
UNIT_MAP = {
    # FR
    "gramme": "g",
    "grammes": "g",
    "kilogramme": "kg",
    "kilogrammes": "kg",
    "litre": "l",
    "litres": "l",
    # EN
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "ounce": "oz",
    "ounces": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "cup": "cup",
    "cups": "cup",
}

# ---------------------------------------------------------------------------
# Decimal-to-fraction display mapping
# ---------------------------------------------------------------------------
FRACTION_MAP = {
    "0.25": "¼",
    "0.33": "⅓",
    "0.5": "½",
    "0.66": "⅔",
    "0.75": "¾",
}

# ---------------------------------------------------------------------------
# Tool detection keywords (keyword list → tool name)
# ---------------------------------------------------------------------------
TOOL_KEYWORDS = {
    "Four": ["four", "enfourner", "oven", "bake", "baking", "prechauffer", "preheat"],
    "Varoma": ["varoma", "vapeur", "steam", "steaming"],
    "Fouet papillon": ["fouet papillon", "butterfly", "butterfly whisk", "monter en neige", "chantilly", "creme fouettee", "whipped cream", "stiff peaks", "soft peaks"],
    "Panier de cuisson": ["panier de cuisson", "steaming basket", "steam basket"],
}
