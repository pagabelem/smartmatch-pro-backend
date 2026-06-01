# app/modules/ai/ai_service.py

from typing import List
from sqlalchemy.orm import Session

from app.modules.jobs.job_model import Job
from app.modules.skill_gap.skill_gap_service import SkillGapService
from app.modules.users.user_model import Profile


class AIService:

    # ── CHATBOT ───────────────────────────────────────────────────────────────
    @staticmethod
    def chat(db: Session, user_id: int, message: str, history: list) -> dict:
        """
        Chatbot contextuel basé sur le profil et les offres de l'utilisateur.
        V1 : réponses basées sur des règles simples.
        """
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        msg_lower = message.lower().strip()

        # Réponses contextuelles
        if any(w in msg_lower for w in ["bonjour", "salut", "hello"]):
            reply = (
                f"Bonjour ! Je suis votre assistant SmartMatch Pro. "
                f"Je peux vous aider à trouver des offres, analyser "
                f"votre profil ou générer une lettre de motivation. "
                f"Comment puis-je vous aider ?"
            )

        elif any(w in msg_lower for w in ["compétence", "skill", "skill gap"]):
            if profile and profile.all_skills:
                skills = ", ".join(profile.all_skills[:5])
                reply = (
                    f"Vos compétences principales sont : {skills}. "
                    f"Utilisez l'endpoint /skill-gap pour analyser "
                    f"les compétences manquantes par rapport aux offres."
                )
            else:
                reply = (
                    "Votre profil ne contient pas encore de compétences. "
                    "Ajoutez-en manuellement ou uploadez votre CV."
                )

        elif any(w in msg_lower for w in ["offre", "job", "emploi", "poste"]):
            from app.modules.jobs.job_model import Job
            total = db.query(Job).filter(Job.status == "active").count()
            reply = (
                f"Il y a actuellement {total} offre(s) active(s). "
                f"Utilisez /matching/run/{user_id} pour obtenir "
                f"vos recommandations personnalisées."
            )

        elif any(w in msg_lower for w in ["lettre", "motivation", "cover"]):
            reply = (
                "Je peux générer une lettre de motivation personnalisée. "
                "Utilisez l'endpoint POST /ai/letter avec votre user_id "
                "et le job_id de l'offre qui vous intéresse."
            )

        elif any(w in msg_lower for w in ["entretien", "interview", "question"]):
            reply = (
                "Je peux simuler un entretien d'embauche avec des questions "
                "adaptées au poste. Utilisez POST /ai/interview avec "
                "votre user_id et le job_id."
            )

        elif any(w in msg_lower for w in ["formation", "roadmap", "apprendre"]):
            reply = (
                "Je peux générer un plan de formation personnalisé basé sur "
                "vos compétences manquantes. Utilisez POST /ai/roadmap "
                "avec votre user_id et le job_id cible."
            )

        else:
            reply = (
                "Je suis là pour vous aider avec : les offres d'emploi, "
                "l'analyse de votre profil, la génération de lettres de "
                "motivation, les roadmaps de formation et la simulation "
                "d'entretiens. Que souhaitez-vous faire ?"
            )

        new_history = list(history) + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]

        return {"reply": reply, "history": new_history}

    # ── LETTRE DE MOTIVATION ──────────────────────────────────────────────────
    @staticmethod
    def generate_letter(
        db: Session, user_id: int, job_id: int, tone: str = "professional"
    ) -> dict:
        """
        Génère une lettre de motivation personnalisée.
        """
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        job = db.query(Job).filter(Job.id == job_id).first()

        if not profile:
            raise ValueError(
                f"Profil introuvable pour l'utilisateur {user_id}."
            )
        if not job:
            raise ValueError(f"Offre {job_id} introuvable.")

        name = profile.full_name or "le candidat"
        skills = profile.all_skills[:5]
        skills_str = ", ".join(skills) if skills else "diverses compétences"

        tones = {
            "professional": "Je me permets de vous adresser ma candidature",
            "enthusiastic": "C'est avec enthousiasme que je vous soumets ma candidature",
            "formal": "J'ai l'honneur de vous présenter ma candidature",
        }
        opening = tones.get(tone, tones["professional"])

        letter = f"""Madame, Monsieur,

{opening} au poste de {job.title} au sein de {job.company}.

Fort(e) de mes compétences en {skills_str}, je suis convaincu(e) de pouvoir 
apporter une contribution significative à votre équipe.

{"Ce poste m'attire particulièrement car il correspond parfaitement à mon profil et mes aspirations professionnelles." if job.description else "Ce poste représente une opportunité idéale pour mettre en valeur mes compétences."}

Je serais ravi(e) de vous rencontrer pour vous exposer ma motivation.

Dans l'attente de votre retour, je vous adresse mes cordiales salutations.

{name}"""

        return {
            "letter": letter,
            "job_title": job.title,
            "company": job.company,
        }

    # ── ROADMAP DE FORMATION ──────────────────────────────────────────────────
    @staticmethod
    def generate_roadmap(db: Session, user_id: int, job_id: int) -> dict:
        """
        Génère un plan de formation basé sur les compétences manquantes.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Offre {job_id} introuvable.")

        # Calculer le skill gap
        skill_gap = SkillGapService.analyze_for_job(db, user_id, job_id)
        missing = skill_gap.missing_skills

        if not missing:
            return {
                "user_id": user_id,
                "job_id": job_id,
                "job_title": job.title,
                "missing_skills": [],
                "roadmap": [],
                "total_weeks": 0,
            }

        # Ressources par défaut par compétence
        default_resources = {
            "python": ["Python.org", "Real Python", "Coursera Python"],
            "sql": ["SQLZoo", "Mode Analytics SQL", "W3Schools SQL"],
            "fastapi": ["FastAPI docs", "TestDriven.io FastAPI"],
            "docker": ["Docker docs", "Play with Docker"],
            "machine learning": ["Coursera ML", "fast.ai", "Kaggle"],
            "react": ["React docs", "Scrimba React", "Frontend Masters"],
            "javascript": ["MDN Web Docs", "javascript.info", "freeCodeCamp"],
        }

        roadmap = []
        total_weeks = 0

        for i, skill in enumerate(missing[:8], start=1):
            skill_lower = skill.lower()
            resources = default_resources.get(
                skill_lower,
                [f"Documentation officielle {skill}", f"Udemy {skill}", f"YouTube {skill}"]
            )
            weeks = 2 if skill_lower in ["python", "sql", "javascript"] else 3

            roadmap.append({
                "step": i,
                "skill": skill,
                "resources": resources,
                "estimated_weeks": weeks,
            })
            total_weeks += weeks

        return {
            "user_id": user_id,
            "job_id": job_id,
            "job_title": job.title,
            "missing_skills": missing,
            "roadmap": roadmap,
            "total_weeks": total_weeks,
        }

    # ── SIMULATEUR D'ENTRETIEN ────────────────────────────────────────────────
    @staticmethod
    def generate_interview(
        db: Session, user_id: int, job_id: int, num_questions: int = 5
    ) -> dict:
        """
        Génère des questions d'entretien adaptées au poste.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Offre {job_id} introuvable.")

        skills = job.required_skills or []

        question_bank = [
            {
                "question": f"Décrivez votre expérience avec {skills[0] if skills else 'la technologie principale'}.",
                "category": "Technique"
            },
            {
                "question": "Parlez-moi d'un projet dont vous êtes particulièrement fier(e).",
                "category": "Expérience"
            },
            {
                "question": "Comment gérez-vous les situations de pression ou les délais serrés ?",
                "category": "Comportemental"
            },
            {
                "question": f"Pourquoi souhaitez-vous rejoindre {job.company} ?",
                "category": "Motivation"
            },
            {
                "question": "Comment restez-vous à jour avec les nouvelles technologies de votre domaine ?",
                "category": "Veille technologique"
            },
            {
                "question": "Décrivez votre méthode de travail en équipe.",
                "category": "Soft skills"
            },
            {
                "question": f"Quelle est votre approche pour résoudre un problème complexe en {skills[1] if len(skills) > 1 else 'programmation'} ?",
                "category": "Technique"
            },
            {
                "question": "Où vous voyez-vous dans 3 ans ?",
                "category": "Projection"
            },
            {
                "question": "Avez-vous des questions concernant le poste ou l'entreprise ?",
                "category": "Final"
            },
            {
                "question": "Quelle est votre plus grande force et votre principal axe d'amélioration ?",
                "category": "Auto-évaluation"
            },
        ]

        selected = question_bank[:num_questions]
        questions = [
            {
                "question_number": i + 1,
                "question": q["question"],
                "category": q["category"],
            }
            for i, q in enumerate(selected)
        ]

        return {
            "job_title": job.title,
            "company": job.company,
            "questions": questions,
        }

    # ── DÉTECTION DE FRAUDE ───────────────────────────────────────────────────
    @staticmethod
    def check_fraud(db: Session, job_id: int) -> dict:
        """
        Analyse une offre d'emploi pour détecter des indicateurs de fraude.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Offre {job_id} introuvable.")

        flags = []

        # Indicateurs de fraude
        if job.salary_max and job.salary_max > 100000:
            flags.append("Salaire anormalement élevé")

        if not job.description or len(job.description) < 50:
            flags.append("Description très courte ou absente")

        if not job.url:
            flags.append("Aucun lien vers l'offre originale")

        suspicious_words = [
            "urgent", "immédiat", "facile", "sans expérience",
            "travail à domicile", "revenus garantis", "commission élevée"
        ]
        if job.description:
            desc_lower = job.description.lower()
            found = [w for w in suspicious_words if w in desc_lower]
            if found:
                flags.append(f"Mots suspects détectés : {', '.join(found)}")

        if job.salary_min and job.salary_max:
            if job.salary_max > job.salary_min * 5:
                flags.append("Fourchette salariale anormalement large")

        is_suspicious = len(flags) >= 2

        if len(flags) == 0:
            risk_level = "Faible"
            recommendation = "Cette offre semble légitime."
        elif len(flags) == 1:
            risk_level = "Moyen"
            recommendation = "Vérifiez l'entreprise avant de postuler."
        else:
            risk_level = "Élevé"
            recommendation = "Soyez très prudent. Vérifiez l'entreprise sur LinkedIn et ne communiquez pas d'informations sensibles."

        return {
            "job_id": job_id,
            "job_title": job.title,
            "is_suspicious": is_suspicious,
            "risk_level": risk_level,
            "flags": flags,
            "recommendation": recommendation,
        }