"""
Interactive CLI setup wizard for mcp-cookidoo-thermomix.
Supports French and English UI.
"""

import getpass
import json
import platform
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# i18n — all user-facing strings
# ---------------------------------------------------------------------------
STRINGS = {
    "fr": {
        "title": "=== mcp-cookidoo-thermomix - Configuration ===",
        "lang_prompt": "  1) Francais\n  2) English\nChoisissez la langue / Choose language [1] : ",
        "binary_found": "Binaire trouve : {}",
        "binary_not_found": "Attention : 'mcp-cookidoo-thermomix' introuvable dans le PATH.",
        "binary_ask": "Entrez le chemin complet du binaire (ou Entree pour utiliser le nom tel quel) : ",
        "creds_header": "--- Identifiants Cookidoo ---",
        "email_prompt": "Email : ",
        "email_empty": "Erreur : l'email ne peut pas etre vide.",
        "password_prompt": "Mot de passe : ",
        "password_empty": "Erreur : le mot de passe ne peut pas etre vide.",
        "locale_header": "--- Langue / Pays ---",
        "locale_prompt": "Choisissez votre locale [1] : ",
        "locale_invalid": "Choix invalide '{}', FR par defaut.",
        "config_file": "Fichier de config : {}",
        "config_read_error": "Attention : impossible de lire la config existante ({}), on repart de zero.",
        "summary_header": "--- Resume ---",
        "summary_binary": "  Binaire      : {}",
        "summary_email": "  Email        : {}",
        "summary_password": "  Mot de passe : {}",
        "summary_country": "  Pays         : {}",
        "summary_language": "  Langue       : {}",
        "summary_config": "  Config       : {}",
        "other_servers": "  Autres serveurs MCP (conserves) : {}",
        "confirm": "Ecrire la config ? [O/n] ",
        "aborted": "Abandonne.",
        "done_written": "Config ecrite dans {}",
        "done_restart": "Redemarrez Claude Desktop pour utiliser le MCP !",
        "already_installed": "cookidoo-thermomix est deja configure (email: {}).",
        "already_menu": "  1) Changer de compte (identifiants uniquement)\n  2) Tout reconfigurer\n  3) Quitter",
        "already_prompt": "Votre choix [3] : ",
        "already_ok": "Rien a faire. Bonne cuisine !",
        "creds_updated": "Identifiants mis a jour !",
    },
    "en": {
        "title": "=== mcp-cookidoo-thermomix - Setup ===",
        "lang_prompt": "  1) Francais\n  2) English\nChoisissez la langue / Choose language [1] : ",
        "binary_found": "Binary found: {}",
        "binary_not_found": "Warning: 'mcp-cookidoo-thermomix' not found on PATH.",
        "binary_ask": "Enter the full path to the binary (or press Enter to use the name as-is): ",
        "creds_header": "--- Cookidoo Credentials ---",
        "email_prompt": "Email: ",
        "email_empty": "Error: email cannot be empty.",
        "password_prompt": "Password: ",
        "password_empty": "Error: password cannot be empty.",
        "locale_header": "--- Locale ---",
        "locale_prompt": "Choose your locale [1]: ",
        "locale_invalid": "Invalid choice '{}', defaulting to FR.",
        "config_file": "Config file: {}",
        "config_read_error": "Warning: could not read existing config ({}), starting fresh.",
        "summary_header": "--- Summary ---",
        "summary_binary": "  Binary:   {}",
        "summary_email": "  Email:    {}",
        "summary_password": "  Password: {}",
        "summary_country": "  Country:  {}",
        "summary_language": "  Language: {}",
        "summary_config": "  Config:   {}",
        "other_servers": "  Other MCP servers (preserved): {}",
        "confirm": "Write config? [Y/n] ",
        "aborted": "Aborted.",
        "done_written": "Config written to {}",
        "done_restart": "Restart Claude Desktop to use the MCP!",
        "already_installed": "cookidoo-thermomix is already configured (email: {}).",
        "already_menu": "  1) Switch account (credentials only)\n  2) Full reconfiguration\n  3) Quit",
        "already_prompt": "Your choice [3]: ",
        "already_ok": "Nothing to do. Happy cooking!",
        "creds_updated": "Credentials updated!",
    },
}

# Locale presets
LOCALE_OPTIONS = {
    "1": ("FR - France", "fr", "fr-FR"),
    "2": ("EN - United Kingdom", "gb", "en-GB"),
    "3": ("EN - United States", "us", "en-US"),
    "4": ("DE - Deutschland", "de", "de-DE"),
    "5": ("ES - Espana", "es", "es-ES"),
    "6": ("IT - Italia", "it", "it-IT"),
    "7": ("PT - Portugal", "pt", "pt-PT"),
}

SERVER_KEY = "cookidoo-thermomix"


def _get_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if system == "Windows":
        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _find_binary() -> str | None:
    return shutil.which("mcp-cookidoo-thermomix")


def _ask_language() -> str:
    """Ask the user for UI language. Returns 'fr' or 'en'."""
    print("\n=== mcp-cookidoo-thermomix ===\n")
    choice = input("  1) Francais\n  2) English\nChoisissez la langue / Choose language [1] : ").strip() or "1"
    return "en" if choice == "2" else "fr"


def _build_server_entry(
    binary_path: str,
    email: str,
    password: str,
    country: str,
    language: str,
) -> dict:
    return {
        "command": binary_path,
        "env": {
            "COOKIDOO_EMAIL": email,
            "COOKIDOO_PASSWORD": password,
            "COOKIDOO_COUNTRY": country,
            "COOKIDOO_LANGUAGE": language,
        },
    }


def main() -> None:
    # 0. Choose UI language
    lang = _ask_language()
    t = STRINGS[lang]

    print(f"\n{t['title']}")

    # Check if already configured
    config_path = _get_config_path()
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    srv = existing.get("mcpServers", {}).get(SERVER_KEY)
    if srv:
        current_email = srv.get("env", {}).get("COOKIDOO_EMAIL", "?")
        print(f"\n{t['already_installed'].format(current_email)}")
        print(t["already_menu"])
        choice = input(t["already_prompt"]).strip() or "3"

        if choice == "1":
            # Quick credentials swap
            print(f"\n{t['creds_header']}")
            email = input(t["email_prompt"]).strip()
            if not email:
                print(t["email_empty"])
                sys.exit(1)
            password = getpass.getpass(t["password_prompt"])
            if not password:
                print(t["password_empty"])
                sys.exit(1)
            srv["env"]["COOKIDOO_EMAIL"] = email
            srv["env"]["COOKIDOO_PASSWORD"] = password
            config_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"\n{t['creds_updated']}")
            print(t["done_restart"])
            sys.exit(0)
        elif choice == "2":
            pass  # continue to full setup below
        else:
            print(t["already_ok"])
            sys.exit(0)

    # 1. Detect binary
    binary = _find_binary()
    if binary:
        print(f"\n{t['binary_found'].format(binary)}")
    else:
        print(f"\n{t['binary_not_found']}")
        binary = input(t["binary_ask"]).strip()
        if not binary:
            binary = "mcp-cookidoo-thermomix"

    # 2. Credentials
    print(f"\n{t['creds_header']}")
    email = input(t["email_prompt"]).strip()
    if not email:
        print(t["email_empty"])
        sys.exit(1)
    password = getpass.getpass(t["password_prompt"])
    if not password:
        print(t["password_empty"])
        sys.exit(1)

    # 3. Locale
    print(f"\n{t['locale_header']}")
    for key, (label, _, _) in LOCALE_OPTIONS.items():
        print(f"  {key}) {label}")
    choice = input(t["locale_prompt"]).strip() or "1"
    if choice not in LOCALE_OPTIONS:
        print(t["locale_invalid"].format(choice))
        choice = "1"
    _, country, language = LOCALE_OPTIONS[choice]

    # 4. Config path
    print(f"\n{t['config_file'].format(config_path)}")

    # 5. Ensure mcpServers exists
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    # 6. Build entry
    entry = _build_server_entry(binary, email, password, country, language)
    existing["mcpServers"][SERVER_KEY] = entry

    # 7. Summary + confirm
    masked_pw = password[:2] + "*" * (len(password) - 2) if len(password) > 2 else "***"
    print(f"\n{t['summary_header']}")
    print(t["summary_binary"].format(binary))
    print(t["summary_email"].format(email))
    print(t["summary_password"].format(masked_pw))
    print(t["summary_country"].format(country))
    print(t["summary_language"].format(language))
    print(t["summary_config"].format(config_path))

    other_servers = [k for k in existing["mcpServers"] if k != SERVER_KEY]
    if other_servers:
        print(t["other_servers"].format(", ".join(other_servers)))

    confirm = input(f"\n{t['confirm']}").strip().lower()
    if confirm and confirm not in ("o", "y", ""):
        print(t["aborted"])
        sys.exit(0)

    # 8. Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\n{t['done_written'].format(config_path)}")
    print(t["done_restart"])


if __name__ == "__main__":
    main()
