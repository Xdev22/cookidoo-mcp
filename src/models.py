"""
Pydantic models for recipes and their Thermomix conversion.

Supports Cookidoo structured annotations for:
- TTS (Time/Temperature/Speed) cooking parameters per step
- INGREDIENT links between steps and ingredients
"""

from pydantic import BaseModel, Field
from typing import Optional


class Ingredient(BaseModel):
    """An ingredient with optional quantity."""

    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    quantity_numeric: Optional[float] = Field(
        None, description="Numeric quantity for annotations (e.g. 200.0)"
    )
    quantity_max: Optional[float] = Field(
        None, description="Max quantity for ranges (e.g. 200-300)"
    )

    def to_text(self, locale: str = "fr") -> str:
        """Format the ingredient as a readable string.

        Args:
            locale: Language code ("fr" or "en").

        Returns:
            FR: "200 g de boulgour" or "20 g d'huile d'olive".
            EN: "200 g flour" or "1 tbsp olive oil".
        """
        name = self.name[0].lower() + self.name[1:] if self.name else self.name
        if self.quantity and self.unit:
            if locale.startswith("fr"):
                vowels = "aeiouyàâéèêëïîôùûüAEIOUY"
                if name and name[0] in vowels:
                    return f"{self.quantity} {self.unit} d'{name}"
                return f"{self.quantity} {self.unit} de {name}"
            return f"{self.quantity} {self.unit} {name}"
        if self.quantity:
            return f"{self.quantity} {name}"
        return name

    def to_volume_annotation(self) -> dict | None:
        """Build a VOLUME annotation for this ingredient.

        Returns:
            A dict like {"amount": 200, "unit": "g"} or None.
        """
        if self.quantity_numeric is None:
            return None
        data: dict = {"amount": self.quantity_numeric}
        if self.quantity_max is not None:
            data["amountMax"] = self.quantity_max
        if self.unit:
            data["unit"] = self.unit
        return data


class AnnotationPosition(BaseModel):
    """Position of an annotation within step text."""

    offset: int = Field(..., description="Character offset from start of step text")
    length: int = Field(..., description="Length of the annotated text")


class TTSAnnotation(BaseModel):
    """Time/Temperature/Speed annotation for a Thermomix step.

    Maps to Cookidoo's {"type": "TTS"} annotation format.
    """

    position: AnnotationPosition
    speed: Optional[str] = Field(None, description="Speed value as string (1-10)")
    time: Optional[int] = Field(None, description="Duration in seconds")
    temperature_value: Optional[str] = Field(
        None, description="Temperature value (e.g. '100' or 'varoma')"
    )
    temperature_unit: str = Field("C", description="Temperature unit")

    def to_cookidoo_annotation(self) -> dict:
        """Convert to Cookidoo API annotation format."""
        data: dict = {}
        if self.speed is not None:
            data["speed"] = self.speed
        if self.time is not None:
            data["time"] = self.time
        if self.temperature_value is not None:
            data["temperature"] = {
                "value": self.temperature_value,
                "unit": self.temperature_unit,
            }
        return {
            "type": "TTS",
            "position": {
                "offset": self.position.offset,
                "length": self.position.length,
            },
            "data": data,
        }


class IngredientAnnotation(BaseModel):
    """Ingredient annotation linking an ingredient to a position in step text.

    Maps to Cookidoo's {"type": "INGREDIENT"} annotation format.
    """

    position: AnnotationPosition
    ingredient: "Ingredient"

    def to_cookidoo_annotation(self, locale: str = "fr") -> dict:
        """Convert to Cookidoo API annotation format."""
        return {
            "type": "INGREDIENT",
            "position": {
                "offset": self.position.offset,
                "length": self.position.length,
            },
            "data": {
                "description": {
                    "text": self.ingredient.to_text(locale),
                    "annotations": [],
                }
            },
        }


class ThermomixStep(BaseModel):
    """A recipe step in Thermomix format."""

    description: str
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    temperature: Optional[int] = Field(None, description="Temperature in °C (37-120)")
    speed: Optional[int] = Field(None, description="Thermomix speed (1-10 or Turbo)")
    reverse: bool = Field(False, description="Reverse mode (spoon)")
    is_turbo: bool = False
    is_varoma: bool = Field(False, description="Varoma temperature mode")
    tts_annotations: list[TTSAnnotation] = Field(
        default_factory=list, description="Cooking parameter annotations"
    )
    ingredient_annotations: list[IngredientAnnotation] = Field(
        default_factory=list, description="Ingredient link annotations"
    )

    def tts_text(self, locale: str = "fr") -> str | None:
        """Format cooking parameters as Cookidoo TTS text.

        Returns:
            A string like "30 sec/vitesse 3" or "5 min/100°C/vitesse 1",
            or None if no cooking parameters.
        """
        details = []
        if self.duration_seconds:
            minutes, secs = divmod(self.duration_seconds, 60)
            if minutes > 0:
                time_str = f"{minutes} min"
                if secs:
                    time_str += f" {secs} sec"
                details.append(time_str)
            else:
                details.append(f"{secs} sec")
        if self.is_varoma:
            details.append("Varoma")
        elif self.temperature:
            details.append(f"{self.temperature}°C")
        if self.is_turbo:
            details.append("Turbo")
        elif self.speed:
            speed_label = "vitesse" if locale.startswith("fr") else "speed"
            details.append(f"{speed_label} {self.speed}")
        return "/".join(details) if details else None

    def to_text(self, locale: str = "fr") -> str:
        """Format the step as Cookidoo step text.

        Returns:
            A string like "Mix ingredients 5 min/100°C/vitesse 1".
        """
        tts = self.tts_text(locale)
        if tts:
            return f"{self.description} {tts}"
        return self.description

    def build_annotations(self, locale: str = "fr") -> list[dict]:
        """Build all Cookidoo annotations for this step.

        Combines INGREDIENT and TTS annotations.
        """
        annotations = []
        for ing in self.ingredient_annotations:
            annotations.append(ing.to_cookidoo_annotation(locale))
        for tts in self.tts_annotations:
            annotations.append(tts.to_cookidoo_annotation())
        return annotations


class ScrapedRecipe(BaseModel):
    """Raw recipe extracted from a website."""

    title: str
    ingredients: list[str] = []
    instructions: list[str] = []
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    prep_time: Optional[int] = Field(None, description="Prep time in minutes")
    cook_time: Optional[int] = Field(None, description="Cook time in minutes")
    servings: Optional[int] = None
    image_url: Optional[str] = None
    source_url: str = ""


class ThermomixRecipe(BaseModel):
    """Complete Thermomix recipe, ready for Cookidoo."""

    name: str
    ingredients: list[Ingredient] = []
    steps: list[ThermomixStep] = []
    servings: int = 4
    prep_time_minutes: int = 30
    total_time_minutes: int = 60
    hints: list[str] = []
    source_url: str = ""
    tools: list[str] = Field(default=["TM7"])
    locale: str = "fr"

    def to_cookidoo_payload(self, locale: str = "fr-FR") -> dict:
        """Convert the recipe to a Cookidoo API payload.

        Args:
            locale: The locale string (e.g. "fr-FR").

        Returns:
            A dict ready to be sent to the Cookidoo API.
        """
        lang = self.locale
        unit_text = "portion" if lang.startswith("fr") else "serving"

        instructions = []
        for step in self.steps:
            step_dict: dict = {
                "type": "STEP",
                "text": step.to_text(lang),
                "annotations": step.build_annotations(lang),
                "missedUsages": [],
            }
            instructions.append(step_dict)

        return {
            "name": self.name,
            "image": None,
            "tools": self.tools,
            "yield": {"value": self.servings, "unitText": unit_text},
            "prepTime": self.prep_time_minutes * 60,
            "cookTime": 0,
            "totalTime": self.total_time_minutes * 60,
            "ingredients": [
                {"type": "INGREDIENT", "text": ing.to_text(lang)}
                for ing in self.ingredients
            ],
            "instructions": instructions,
            "hints": "\n".join(self.hints) if self.hints else "",
            "workStatus": "PRIVATE",
            "recipeMetadata": {"requiresAnnotationsCheck": False},
        }
