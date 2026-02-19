# MCP Cookidoo Thermomix

MCP Server to import any web recipe as a Thermomix recipe on your Cookidoo account.

Supports **200+ recipe sites** in French and English (Marmiton, 750g, AllRecipes, BBC Good Food, Food Network, etc.).

## Quick setup

### Automatic (recommended)

Run this single command in your terminal:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Xdev22/mcp-cookidoo-thermomix/main/install.sh)
```

The wizard will guide you through:
- Installing dependencies automatically
- Entering your Cookidoo credentials
- Choosing your language/country
- Writing the Claude Desktop config

### Manual

<details>
<summary>Click to expand</summary>

#### 1. Install the MCP

```bash
pip install mcp-cookidoo-thermomix
```

Or for development:

```bash
git clone https://github.com/Xdev22/mcp-cookidoo-thermomix.git
cd mcp-cookidoo-thermomix
pip install -e .
```

#### 2. Add the MCP to Claude Desktop

Edit the file `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cookidoo-thermomix": {
      "command": "mcp-cookidoo-thermomix",
      "env": {
        "COOKIDOO_EMAIL": "your@email.com",
        "COOKIDOO_PASSWORD": "yourpassword",
        "COOKIDOO_COUNTRY": "fr",
        "COOKIDOO_LANGUAGE": "fr-FR"
      }
    }
  }
}
```

#### 3. Restart Claude Desktop

</details>

## Switch account

Already configured? Run the setup again to quickly switch Cookidoo account:

```bash
mcp-cookidoo-setup
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `COOKIDOO_EMAIL` | *(required)* | Your Cookidoo account email |
| `COOKIDOO_PASSWORD` | *(required)* | Your Cookidoo account password |
| `COOKIDOO_COUNTRY` | `fr` | Country code (`fr`, `gb`, `us`, `de`, etc.) |
| `COOKIDOO_LANGUAGE` | `fr-FR` | Language locale (`fr-FR`, `en-GB`, `en-US`, `de-DE`, etc.) |

### Supported locales

| Language | `COOKIDOO_COUNTRY` | `COOKIDOO_LANGUAGE` |
|----------|-------------------|-------------------|
| French | `fr` | `fr-FR` |
| English (UK) | `gb` | `en-GB` |
| English (US) | `us` | `en-US` |
| German | `de` | `de-DE` |
| Spanish | `es` | `es-ES` |
| Italian | `it` | `it-IT` |
| Portuguese | `pt` | `pt-PT` |

## Usage

Just tell Claude:

> "Import this recipe: https://www.marmiton.org/recettes/recette_poulet-basquaise_17715.aspx"

> "Import this recipe: https://www.allrecipes.com/recipe/24002/easy-chicken-pot-pie/"

Or to preview without saving:

> "Show me this recipe in Thermomix format: https://www.750g.com/..."

## Available tools

| Tool | Description |
|------|-------------|
| `import_recipe` | Import a recipe from a link and save it to Cookidoo |
| `preview_recipe` | Preview the Thermomix conversion without saving |

## Stack

- Python 3.11+
- FastMCP
- Pydantic v2
- cookidoo-api (unofficial)
- recipe-scrapers
