# app/modules/matching/cosine_matcher.py

"""
Calcul de similarité cosinus entre les compétences d'un profil
et les compétences requises par une offre d'emploi.

Approche : vecteurs binaires (présence/absence de chaque skill).
Simple, rapide, efficace pour des listes de compétences normalisées.
"""

from typing import List


def _vectorize(skills_a: List[str], skills_b: List[str]) -> tuple:
    """
    Construit deux vecteurs binaires à partir de deux listes de compétences.
    
    Exemple :
        skills_a = ["python", "sql"]
        skills_b = ["python", "docker"]
        vocabulary = {"python", "sql", "docker"}
        vec_a = [1, 1, 0]
        vec_b = [1, 0, 1]
    """
    vocabulary = list(set(skills_a) | set(skills_b))
    if not vocabulary:
        return [], []

    set_a = set(skills_a)
    set_b = set(skills_b)

    vec_a = [1 if skill in set_a else 0 for skill in vocabulary]
    vec_b = [1 if skill in set_b else 0 for skill in vocabulary]

    return vec_a, vec_b


def cosine_similarity(skills_a: List[str], skills_b: List[str]) -> float:
    """
    Calcule le score de similarité cosinus entre deux listes de compétences.

    Retourne un float entre 0.0 (aucune compétence en commun)
    et 1.0 (compétences identiques).

    Cas particuliers :
    - Si l'une des deux listes est vide → retourne 0.0
    - Si les deux listes sont identiques → retourne 1.0
    """
    if not skills_a or not skills_b:
        return 0.0

    # Normaliser en lowercase
    a = [s.lower().strip() for s in skills_a if s.strip()]
    b = [s.lower().strip() for s in skills_b if s.strip()]

    if not a or not b:
        return 0.0

    vec_a, vec_b = _vectorize(a, b)

    # Produit scalaire
    dot_product = sum(x * y for x, y in zip(vec_a, vec_b))

    # Normes
    norm_a = sum(x ** 2 for x in vec_a) ** 0.5
    norm_b = sum(x ** 2 for x in vec_b) ** 0.5

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return round(dot_product / (norm_a * norm_b), 4)