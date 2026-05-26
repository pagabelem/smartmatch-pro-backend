import re
import json
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Dictionnaire maître — DOIT être identique au fichier data/skills_dictionary.json
# utilisé par le Membre 2 pour la cohérence du matching.
# ---------------------------------------------------------------------------
SKILLS_DICT: dict[str, list[str]] = {
    "languages": [
        "python", "javascript", "java", "c++", "c#", "go", "rust",
        "php", "ruby", "swift", "kotlin", "typescript", "scala",
        "r", "matlab", "perl", "bash", "shell", "powershell",
    ],
    "frameworks": [
        "fastapi", "django", "flask", "react", "vue", "angular",
        "spring", "laravel", "rails", "asp.net", "express", "nextjs",
        "nuxtjs", "nestjs", "symfony", "codeigniter", "svelte",
        "fastify", "starlette", "celery",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "cassandra", "sqlite", "oracle", "mariadb", "dynamodb",
        "neo4j", "couchdb", "influxdb", "clickhouse", "supabase",
    ],
    "cloud": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "gitlab ci", "github actions", "circleci",
        "helm", "prometheus", "grafana", "nginx", "traefik",
        "cloudflare", "heroku", "vercel", "netlify",
    ],
    "tools": [
        "git", "jira", "confluence", "figma", "photoshop", "illustrator",
        "office", "excel", "power bi", "tableau", "notion", "slack",
        "postman", "swagger", "sonarqube", "datadog", "sentry",
        "linux", "macos", "windows", "vscode", "intellij",
    ],
    "soft_skills": [
        "leadership", "teamwork", "communication", "problem solving",
        "adaptability", "creativity", "time management", "critical thinking",
        "emotional intelligence", "autonomy", "rigor", "curiosity",
        "mentoring", "coaching", "project management", "agile", "scrum",
        "kanban", "negotiation", "presentation",
    ],
}

# Table de normalisation : alias → nom canonique
# Permet de mapper "reactjs" → "react", "postgres" → "postgresql", etc.
SKILL_ALIASES: dict[str, str] = {
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "nodejs": "express",        # node.js seul = environnement runtime
    "node.js": "express",
    "node": "express",
    "postgres": "postgresql",
    "pg": "postgresql",
    "mongo": "mongodb",
    "es": "elasticsearch",
    "k8s": "kubernetes",
    "gke": "kubernetes",
    "eks": "kubernetes",
    "aks": "kubernetes",
    "tf": "terraform",
    "ci/cd": "gitlab ci",
    "cicd": "gitlab ci",
    "gh actions": "github actions",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "dotnet": "asp.net",
    ".net": "asp.net",
    "net": "asp.net",
    "ms sql": "oracle",         # SQL Server → catégorie databases
    "mssql": "oracle",
    "power-bi": "power bi",
    "powerbi": "power bi",
    "next.js": "nextjs",
    "nuxt.js": "nuxtjs",
    "nest.js": "nestjs",
    "scrum master": "scrum",
    "product owner": "scrum",
    "agile methodology": "agile",
    "team work": "teamwork",
    "time-management": "time management",
    "problem-solving": "problem solving",
}

# Index inversé : compétence → catégorie (construit une seule fois)
_SKILL_TO_CATEGORY: dict[str, str] = {}


def _build_index() -> None:
    global _SKILL_TO_CATEGORY
    for category, skills in SKILLS_DICT.items():
        for skill in skills:
            _SKILL_TO_CATEGORY[skill] = category


_build_index()


# ---------------------------------------------------------------------------
# Fonctions publiques
# ---------------------------------------------------------------------------

def load_skill_dictionary() -> dict[str, list[str]]:
    """
    Charge le dictionnaire de compétences.
    Tente d'abord data/skills_dictionary.json (source partagée avec Membre 2),
    puis retourne SKILLS_DICT comme fallback.
    """
    json_path = Path("data/skills_dictionary.json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return SKILLS_DICT


def normalize_skill_name(skill: str) -> str:
    """
    Normalise un nom de compétence :
    - lowercase
    - suppression des numéros de version (ex: "Python 3.11" → "python")
    - suppression des espaces superflus
    - résolution des alias (ex: "ReactJS" → "react")
    """
    # Lowercase et strip
    normalized = skill.lower().strip()

    # Suppression des versions : "python 3", "python 3.11", "node 18.x"
    normalized = re.sub(r"\s+\d+[\w.]*$", "", normalized)
    normalized = re.sub(r"\s+v\d+[\w.]*$", "", normalized)

    # Suppression des espaces multiples
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Résolution des alias
    if normalized in SKILL_ALIASES:
        normalized = SKILL_ALIASES[normalized]

    return normalized


def get_skill_category(skill: str) -> Optional[str]:
    """
    Retourne la catégorie d'une compétence normalisée,
    ou None si la compétence n'est pas dans le dictionnaire.
    """
    normalized = normalize_skill_name(skill)
    return _SKILL_TO_CATEGORY.get(normalized)


def get_all_skills_flat() -> list[str]:
    """Retourne toutes les compétences en liste plate (normalisées)."""
    return list(_SKILL_TO_CATEGORY.keys())