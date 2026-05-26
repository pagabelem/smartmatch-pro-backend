import re
from typing import Optional

import spacy

from app.modules.nlp.skill_dictionary import (
    SKILLS_DICT,
    get_all_skills_flat,
    normalize_skill_name,
    get_skill_category,
)

# ---------------------------------------------------------------------------
# Chargement unique du modèle spaCy
# ---------------------------------------------------------------------------
_nlp: Optional[spacy.language.Language] = None


def get_nlp_model() -> spacy.language.Language:
    """
    Retourne le modèle spaCy chargé (singleton).
    Appelé depuis nlp_service.py au démarrage de l'application.
    """
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            _nlp = spacy.blank("en")
    return _nlp


# ---------------------------------------------------------------------------
# Patterns regex pour l'extraction contextuelle
# ---------------------------------------------------------------------------
REGEX_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+\+?\s*years?\s+of\s+([\w\s+#./]+?)(?:\s*[,.\n]|$)", re.IGNORECASE),
    re.compile(r"experienced?\s+in\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"knowledge\s+of\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"proficient\s+(?:in|with)\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"skilled?\s+in\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"expertise\s+in\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"working\s+with\s+([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"using\s+([\w\s+#./,]+?)(?:\s+(?:for|to|in|at)|[.\n]|$)", re.IGNORECASE),
    re.compile(r"certifi(?:ed|cation)\s+(?:in\s+)?([\w\s+#./]+?)(?:\s*[,.\n]|$)", re.IGNORECASE),
    re.compile(r"stack\s*:\s*([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"technologies?\s*:\s*([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"outils?\s*:\s*([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
    re.compile(r"compétences?\s*:\s*([\w\s+#./,]+?)(?:\s*[.\n]|$)", re.IGNORECASE),
]

# Entités spaCy pertinentes pour les compétences tech
SPACY_RELEVANT_LABELS = {"PRODUCT", "ORG", "WORK_OF_ART"}

# Longueur max d'un token issu de regex (évite les faux positifs trop longs)
MAX_SKILL_TOKEN_LENGTH = 40


# ---------------------------------------------------------------------------
# Fonctions internes
# ---------------------------------------------------------------------------

def _match_against_dictionary(text: str) -> set[str]:
    """
    Étape 1 : matching exact sur le dictionnaire.
    Recherche chaque compétence connue dans le texte normalisé.
    """
    found: set[str] = set()
    all_skills = get_all_skills_flat()

    for skill in all_skills:
        # Échappement pour les compétences avec caractères spéciaux (c++, c#)
        pattern = re.escape(skill)
        # Frontière de mot adaptée (pas \b car c++ contient '+')
        regex = re.compile(r"(?<!\w)" + pattern + r"(?!\w)", re.IGNORECASE)
        if regex.search(text):
            found.add(skill)

    return found


def _extract_via_spacy_ner(text: str) -> set[str]:
    """
    Étape 2 : extraction via NER spaCy.
    Filtre les entités de type PRODUCT, ORG, WORK_OF_ART et vérifie
    si elles correspondent à une compétence connue.
    """
    found: set[str] = set()
    nlp = get_nlp_model()
    doc = nlp(text[:100_000])  # limite pour éviter les timeouts

    for ent in doc.ents:
        if ent.label_ not in SPACY_RELEVANT_LABELS:
            continue
        normalized = normalize_skill_name(ent.text)
        if get_skill_category(normalized) is not None:
            found.add(normalized)

    return found


def _extract_via_regex(text: str) -> set[str]:
    """
    Étape 3 : extraction par patterns contextuels (regex).
    Extrait les termes qui suivent des expressions comme
    "experienced in", "knowledge of", "X years of", etc.
    """
    found: set[str] = set()

    for pattern in REGEX_PATTERNS:
        for match in pattern.finditer(text):
            raw_group = match.group(1)
            # Sépare les listes potentielles : "python, django, postgresql"
            tokens = re.split(r"[,/&|]+", raw_group)
            for token in tokens:
                token = token.strip()
                if not token or len(token) > MAX_SKILL_TOKEN_LENGTH:
                    continue
                normalized = normalize_skill_name(token)
                if get_skill_category(normalized) is not None:
                    found.add(normalized)

    return found


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------

def extract_skills_from_text(text: str) -> list[str]:
    """
    Extraction hybride des compétences depuis un texte nettoyé.

    Stratégie (dans l'ordre de priorité) :
    1. Matching exact sur le dictionnaire de compétences
    2. NER spaCy (entités PRODUCT / ORG filtrées)
    3. Patterns regex contextuels

    Retourne une liste dédoublonnée de compétences normalisées,
    triées par catégorie puis alphabétiquement.
    """
    if not text or not text.strip():
        return []

    # Étape 1 : dictionnaire
    dict_skills = _match_against_dictionary(text)

    # Étape 2 : NER spaCy
    ner_skills = _extract_via_spacy_ner(text)

    # Étape 3 : regex
    regex_skills = _extract_via_regex(text)

    # Union et dédoublonnage
    all_skills: set[str] = dict_skills | ner_skills | regex_skills

    # Tri : par catégorie puis alphabétique pour une sortie déterministe
    category_order = list(SKILLS_DICT.keys())

    def sort_key(skill: str) -> tuple[int, str]:
        cat = get_skill_category(skill)
        cat_index = category_order.index(cat) if cat in category_order else len(category_order)
        return (cat_index, skill)

    return sorted(all_skills, key=sort_key)