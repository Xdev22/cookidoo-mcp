"""
Recipe scraping from any website.
Uses recipe-scrapers (200+ supported sites) with fallback to raw HTML parsing.
"""
import re
import aiohttp
from typing import Optional
from recipe_scrapers import scrape_html
from .models import ScrapedRecipe


async def fetch_html(url: str) -> str:
    """Fetch the HTML content of a web page.

    Args:
        url: The URL to fetch.

    Returns:
        The raw HTML string.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            return await resp.text()


def _parse_time(time_str: Optional[str | int]) -> Optional[int]:
    """Parse a time value in minutes from various formats.

    Args:
        time_str: A time value as int, float, or string.

    Returns:
        The time in minutes, or None if parsing fails.
    """
    if time_str is None:
        return None
    if isinstance(time_str, (int, float)):
        return int(time_str)
    try:
        return int(time_str)
    except (ValueError, TypeError):
        return None


def _is_step_header(text: str) -> bool:
    """Check if a line is just a step header like 'Etape 1', 'Step 3', etc."""
    return bool(re.match(
        r"^(?:étape|etape|step|fase|schritt|paso)\s*\d+\s*[:.>)\-]?\s*$",
        text,
        re.IGNORECASE,
    ))


async def scrape_recipe(url: str) -> ScrapedRecipe:
    """Scrape a recipe from a URL (200+ sites supported).

    Args:
        url: The recipe page URL.

    Returns:
        A ScrapedRecipe with title, ingredients, instructions, etc.
    """
    html = await fetch_html(url)

    try:
        scraper = scrape_html(html=html, org_url=url, online=False)
    except Exception:
        # Fallback: try with wild mode (generic schema.org parsing)
        scraper = scrape_html(html=html, org_url=url, online=False, wild_mode=True)

    # Extract data
    title = _safe_call(scraper.title, "Untitled recipe")
    ingredients = _safe_call(scraper.ingredients, [])
    instructions_raw = _safe_call(scraper.instructions, "")
    total_time = _parse_time(_safe_call(scraper.total_time, None))
    prep_time = _parse_time(_safe_call(scraper.prep_time, None))
    cook_time = _parse_time(_safe_call(scraper.cook_time, None))

    # Parse servings
    servings = None
    try:
        servings_raw = scraper.yields()
        if servings_raw:
            match = re.search(r"(\d+)", str(servings_raw))
            if match:
                servings = int(match.group(1))
    except Exception:
        pass

    image_url = _safe_call(scraper.image, None)

    # Split instructions into a list and filter step headers
    if isinstance(instructions_raw, str):
        instructions = [
            step.strip()
            for step in instructions_raw.split("\n")
            if step.strip() and not _is_step_header(step.strip())
        ]
    else:
        instructions = [
            step for step in instructions_raw
            if step.strip() and not _is_step_header(step.strip())
        ]

    return ScrapedRecipe(
        title=title,
        ingredients=ingredients if isinstance(ingredients, list) else [ingredients],
        instructions=instructions,
        total_time=total_time,
        prep_time=prep_time,
        cook_time=cook_time,
        servings=servings,
        image_url=image_url,
        source_url=url,
    )


def _safe_call(func_or_val, default):
    """Call a scraper method safely, returning a default on failure.

    Args:
        func_or_val: A callable or a value to evaluate.
        default: The fallback value if the call fails.

    Returns:
        The result of the call, or the default value.
    """
    try:
        if callable(func_or_val):
            result = func_or_val()
        else:
            result = func_or_val
        return result if result else default
    except Exception:
        return default
