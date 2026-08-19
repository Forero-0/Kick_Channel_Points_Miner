import json
import os
from loguru import logger

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "es", "ru")

current_language = DEFAULT_LANGUAGE
language_data = {}
_fallback_data = {}


def _load_lang_file(lang_code):
    lang_file = f"lang/{lang_code}.lang"
    with open(lang_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_language(lang_code):
    """Load the language file for lang_code, always falling back to English on failure."""
    global current_language, language_data, _fallback_data

    # English is always kept as the ultimate fallback so partial/missing
    # translation files never leak raw keys or another language's text.
    if not _fallback_data:
        try:
            _fallback_data = _load_lang_file(DEFAULT_LANGUAGE)
        except Exception as e:
            logger.error(f"❌ Could not load default language file lang/{DEFAULT_LANGUAGE}.lang: {e}")
            _fallback_data = {}

    lang_code = (lang_code or DEFAULT_LANGUAGE).lower()
    lang_file = f"lang/{lang_code}.lang"

    if not os.path.exists(lang_file):
        logger.warning(f"🔤 Localization file not found: {lang_file}, falling back to '{DEFAULT_LANGUAGE}'")
        lang_code = DEFAULT_LANGUAGE
        lang_file = f"lang/{lang_code}.lang"

    try:
        language_data = _load_lang_file(lang_code)
        current_language = lang_code
        logger.info(f"🔤 Language set to: {lang_code}")
    except Exception as e:
        logger.error(f"❌ Error loading localization file {lang_file}: {str(e)}")
        language_data = dict(_fallback_data)
        current_language = DEFAULT_LANGUAGE


def t(key, **kwargs):
    global language_data, _fallback_data

    # Prefer the active language, fall back to English, then finally show
    # the missing key instead of mixing in another language's placeholder text.
    text = language_data.get(key)
    if text is None:
        text = _fallback_data.get(key, f"MISSING_KEY:{key}")

    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", str(v))

    return text


def t_rarity(rarity):
    """
    Translate a raw Kick API card rarity value (e.g. "common", "epic")
    into the active language, using the "rarity_<value>" keys.

    Falls back to "rarity_unknown" for missing/unrecognized values so a
    raw, untranslated API string is never shown to the user.
    """
    key = f"rarity_{str(rarity).strip().lower()}" if rarity else "rarity_unknown"
    text = language_data.get(key) or _fallback_data.get(key)
    if text is None:
        text = language_data.get("rarity_unknown") or _fallback_data.get("rarity_unknown", "Unknown")
    return text
