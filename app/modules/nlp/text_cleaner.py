import re
import html
from typing import Optional

import spacy

# Chargement unique du modèle spaCy (réutilisé par skill_extractor aussi)
_nlp_model: Optional[spacy.language.Language] = None


def _get_nlp() -> spacy.language.Language:
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback : modèle vide si en_core_web_sm non installé
            _nlp_model = spacy.blank("en")
    return _nlp_model


def remove_html_tags(text: str) -> str:
    """Supprime les balises HTML et décode les entités HTML."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Normalise les espaces, tabulations et retours à la ligne."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def remove_special_chars(text: str) -> str:
    """
    Supprime les caractères non alphanumériques superflus.
    Conserve : lettres, chiffres, espaces, points, virgules,
    tirets, slashes (C++, C#, .NET), parenthèses et @.
    """
    text = re.sub(r"[^\w\s.,\-/#+@()\n]", " ", text)
    return text


def lowercase_and_strip(text: str) -> str:
    """Met en minuscules et supprime les espaces en début/fin."""
    return text.lower().strip()


def remove_stopwords(text: str, lang: str = "en") -> str:
    """
    Supprime les stopwords via spaCy.
    Conserve les tokens qui sont potentiellement des compétences.
    """
    nlp = _get_nlp()
    doc = nlp(text)
    tokens = [
        token.text
        for token in doc
        if not token.is_stop or token.text in {"+", "#", "."}
    ]
    return " ".join(tokens)


def lemmatize_text(text: str, lang: str = "en") -> str:
    """Lemmatise le texte via spaCy (utile pour les soft skills)."""
    nlp = _get_nlp()
    doc = nlp(text)
    lemmas = [
        token.lemma_ if not token.is_punct else token.text
        for token in doc
    ]
    return " ".join(lemmas)


def clean_text(raw_text: str) -> str:
    """
    Pipeline complet de nettoyage :
    1. Suppression HTML
    2. Normalisation whitespace
    3. Suppression caractères spéciaux
    4. Lowercase + strip
    Le texte résultant est prêt pour l'extraction de compétences.

    Note : on n'applique PAS remove_stopwords ni lemmatize ici
    pour conserver les termes techniques exacts nécessaires au
    matching dictionnaire (ex: "redis", "docker").
    """
    text = remove_html_tags(raw_text)
    text = normalize_whitespace(text)
    text = remove_special_chars(text)
    text = lowercase_and_strip(text)
    text = normalize_whitespace(text)  # second passage après suppression
    return text