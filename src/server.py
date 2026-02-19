"""
MCP Server Cookidoo Thermomix

A single tool to import any recipe link into Cookidoo as a Thermomix recipe.
"""
from fastmcp import FastMCP
from .cookidoo_service import CookidooClient, load_credentials, load_locale
from .recipe_scraper import scrape_recipe
from .thermomix_converter import convert_recipe
from .models import ThermomixRecipe

mcp = FastMCP(
    "cookidoo-thermomix",
    instructions=(
        "This server lets you import any recipe from a web link "
        "and automatically convert it into a Thermomix recipe on your Cookidoo account. "
        "Just send a recipe link!\n\n"
        "Supports recipes in French and English. "
        "Set COOKIDOO_COUNTRY and COOKIDOO_LANGUAGE env vars to configure your locale "
        "(defaults: fr / fr-FR).\n\n"
        "IMPORTANT: When displaying ingredients, format them like Cookidoo does:\n"
        "- FR: quantity + unit + 'de/d'' + name (e.g. '200 g de farine', '20 g d'huile')\n"
        "- EN: quantity + unit + name (e.g. '200 g flour', '1 tbsp olive oil')\n"
        "- If a range is available, show both (e.g. '200 - 500 g flour')"
    ),
)

# Global Cookidoo client state
_client: CookidooClient | None = None

@mcp.tool()
async def import_recipe(url: str) -> str:
    """Import a recipe from a web link and save it to Cookidoo.

    Args:
        url: The recipe link to import (e.g. https://www.marmiton.org/recettes/...).

    Returns:
        A confirmation message with the Cookidoo recipe link.
    """
    global _client

    # 1. Connect to Cookidoo if not already done
    if _client is None or not _client.is_connected:
        try:
            email, password = load_credentials()
            country, language = load_locale()
            _client = CookidooClient(email, password, country=country, language=language)
            await _client.login()
        except ValueError as e:
            return (
                f"Missing configuration: {e}\n\n"
                "Add your Cookidoo credentials in the MCP config:\n"
                "COOKIDOO_EMAIL=your@email.com\n"
                "COOKIDOO_PASSWORD=yourpassword"
            )
        except Exception as e:
            return f"Unable to connect to Cookidoo: {e}"

    # 2. Scrape the recipe
    try:
        scraped = await scrape_recipe(url)
    except Exception as e:
        return (
            f"Unable to read the recipe from {url}\n"
            f"Error: {e}\n\n"
            "Make sure the link is correct and the site is accessible."
        )

    # 3. Convert to Thermomix format
    _, language = load_locale()
    locale = language.split("-")[0]  # "fr-FR" -> "fr"
    thermomix_recipe = convert_recipe(scraped, locale=locale)

    # 4. Upload to Cookidoo
    try:
        result = await _client.upload_recipe(thermomix_recipe)
    except Exception as e:
        return (
            f"Unable to save the recipe on Cookidoo: {e}\n\n"
            f"The recipe '{thermomix_recipe.name}' was converted successfully but "
            "the upload failed. Try again in a few moments."
        )

    # 5. Summary for the user
    steps_preview = "\n".join(
        f"  {i+1}. {step.to_text(locale)}"
        for i, step in enumerate(thermomix_recipe.steps[:5])
    )
    if len(thermomix_recipe.steps) > 5:
        steps_preview += f"\n  ... and {len(thermomix_recipe.steps) - 5} more steps"

    return (
        f"Recipe imported successfully!\n\n"
        f"{thermomix_recipe.name}\n"
        f"{thermomix_recipe.servings} servings\n"
        f"{thermomix_recipe.total_time_minutes} min\n"
        f"{len(thermomix_recipe.ingredients)} ingredients\n\n"
        f"Thermomix steps:\n{steps_preview}\n\n"
        f"View on Cookidoo: {result['url']}"
    )


@mcp.tool()
async def preview_recipe(url: str) -> str:
    """Preview a recipe from a link WITHOUT saving it to Cookidoo.

    Args:
        url: The recipe link to preview.

    Returns:
        A preview of the recipe converted to Thermomix format.
    """
    # 1. Scrape
    try:
        scraped = await scrape_recipe(url)
    except Exception as e:
        return f"Unable to read the recipe from {url}\nError: {e}"

    # 2. Convert
    _, language = load_locale()
    locale = language.split("-")[0]  # "fr-FR" -> "fr"
    thermomix_recipe = convert_recipe(scraped, locale=locale)

    # 3. Display preview
    ingredients_text = "\n".join(
        f"  • {ing.to_text(locale)}" for ing in thermomix_recipe.ingredients
    )
    steps_text = "\n".join(
        f"  {i+1}. {step.to_text(locale)}"
        for i, step in enumerate(thermomix_recipe.steps)
    )
    hints_text = "\n".join(f"  - {h}" for h in thermomix_recipe.hints)

    return (
        f"{thermomix_recipe.name}\n"
        f"{thermomix_recipe.servings} servings | "
        f"{thermomix_recipe.total_time_minutes} min\n\n"
        f"Ingredients:\n{ingredients_text}\n\n"
        f"Thermomix steps:\n{steps_text}\n\n"
        f"{hints_text}\n\n"
        f"Use 'import_recipe' to save it to Cookidoo!"
    )


def main():
    """Entry point to start the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
