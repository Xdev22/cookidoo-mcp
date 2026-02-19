"""
Cookidoo service — authentication and custom recipe upload.

Based on the unofficial reverse-engineered API from the Cookidoo Android app.
"""

import os
import asyncio
from typing import Optional

from aiohttp import ClientSession, TCPConnector
from cookidoo_api import Cookidoo, CookidooConfig
from cookidoo_api.helpers import get_localization_options

from .models import ThermomixRecipe


def load_credentials() -> tuple[str, str]:
    """Load Cookidoo credentials from environment variables.

    Returns:
        A tuple (email, password).
    """
    email = os.getenv("COOKIDOO_EMAIL")
    password = os.getenv("COOKIDOO_PASSWORD")
    if not email or not password:
        raise ValueError(
            "Missing COOKIDOO_EMAIL and COOKIDOO_PASSWORD environment variables. "
            "Set them in your Claude Desktop MCP config under 'env'."
        )
    return email, password


def load_locale() -> tuple[str, str]:
    """Load Cookidoo locale settings from environment variables.

    Returns:
        A tuple (country, language) e.g. ("fr", "fr-FR").
    """
    country = os.getenv("COOKIDOO_COUNTRY", "fr")
    language = os.getenv("COOKIDOO_LANGUAGE", "fr-FR")
    return country, language


class CookidooClient:
    """Client to interact with the Cookidoo API."""

    def __init__(self, email: str, password: str, country: str = "fr", language: str = "fr-FR"):
        self.email = email
        self.password = password
        self.country = country
        self.language = language
        self._api: Optional[Cookidoo] = None
        self._session: Optional[ClientSession] = None

    async def login(self) -> None:
        """Authenticate with Cookidoo and initialize the API client."""
        self._session = ClientSession(connector=TCPConnector(ssl=False))
        localization_options = await get_localization_options(
            country=self.country, language=self.language
        )
        config = CookidooConfig(
            email=self.email,
            password=self.password,
            localization=localization_options[0],
        )
        self._api = Cookidoo(session=self._session, cfg=config)
        await self._api.login()

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()

    @property
    def is_connected(self) -> bool:
        return self._api is not None

    async def upload_recipe(self, recipe: ThermomixRecipe) -> dict:
        """Upload a Thermomix recipe to the Cookidoo account.

        Args:
            recipe: The ThermomixRecipe to upload.

        Returns:
            A dict with "recipe_id" and "url" of the created recipe.
        """
        if not self._api:
            raise RuntimeError("Not connected. Call login() first.")

        auth_data = self._api.auth_data
        if not auth_data:
            raise RuntimeError("No authentication data available.")

        localization = self._api.localization
        url_parts = localization.url.split("/")
        base_url = f"{url_parts[0]}//{url_parts[2]}"
        locale = localization.language

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_data.access_token}",
        }

        api_session = self._api._session

        # Step 1: Create the recipe (name only)
        create_url = f"{base_url}/created-recipes/{locale}"
        async with api_session.post(
            create_url, json={"recipeName": recipe.name}, headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(
                    f"Recipe creation failed (status {response.status}): {error_text}"
                )
            result = await response.json()
            recipe_id = result.get("recipeId")
            if not recipe_id:
                raise RuntimeError("No recipeId returned by the API")

        # Short delay to let the backend propagate
        await asyncio.sleep(3)

        # Step 2: Update with full content
        update_url = f"{base_url}/created-recipes/{locale}/{recipe_id}"
        payload = recipe.to_cookidoo_payload(locale)

        async with api_session.patch(
            update_url, json=payload, headers=headers
        ) as response:
            if response.status not in (200, 204):
                error_text = await response.text()
                raise RuntimeError(
                    f"Recipe update failed (status {response.status}): {error_text}"
                )

        recipe_url = f"https://{localization.url}/recipes/custom-recipes/{recipe_id}"
        return {"recipe_id": recipe_id, "url": recipe_url}
