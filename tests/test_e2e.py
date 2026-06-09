"""
SmartMatch Pro — Test End-to-End Automatisé
============================================

Flow testé :
1. Register (créer un compte)
2. Login (obtenir JWT)
3. Upload CV (PDF)
4. NLP Process (extraire skills)
5. Vérifier skills du profil
6. Lister les CVs du profil

Usage :
    python tests/test_e2e.py

Requirements :
    pip install httpx
"""

import httpx
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
TEST_EMAIL = f"e2e_test_{int(time.time())}@example.com"
TEST_PASSWORD = "Test123!@#"
TEST_CV_PATH = "Tchiwa_Innocent_CV_top.pdf"  # Ton CV

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

def log_step(step_num, description):
    print(f"\n{Colors.BLUE}=== Étape {step_num}: {description} ==={Colors.RESET}")

def log_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def log_error(msg, details=None):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")
    if details:
        print(f"   Détails: {details}")

def log_info(msg):
    print(f"{Colors.YELLOW}ℹ️  {msg}{Colors.RESET}")

class SmartMatchE2E:
    def __init__(self):
        self.client = httpx.Client(base_url=f"{BASE_URL}{API_PREFIX}", timeout=30.0)
        self.access_token = None
        self.user_id = None
        self.profile_id = None
        self.resume_id = None
        self.skills = None
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def step_1_register(self):
        """Étape 1: Créer un compte utilisateur"""
        log_step(1, "Register — Création du compte")
        
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "first_name": "E2E",
            "last_name": "Test"
        }
        
        response = self.client.post("/auth/register", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            self.access_token = data["data"]["access_token"]
            self.user_id = data["data"]["user"]["id"]
            log_success(f"Compte créé — User ID: {self.user_id}")
            log_info(f"Email: {TEST_EMAIL}")
            return True
        elif response.status_code == 409:
            log_info("Compte déjà existant, passage au login...")
            return self.step_2_login()
        else:
            log_error(f"Register échoué — {response.status_code}", response.text)
            return False
    
    def step_2_login(self):
        """Étape 2: Connexion (si register déjà fait)"""
        log_step(2, "Login — Authentification")
        
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = self.client.post("/auth/login", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["data"]["access_token"]
            self.user_id = data["data"]["user"]["id"]
            log_success(f"Login réussi — User ID: {self.user_id}")
            return True
        else:
            log_error(f"Login échoué — {response.status_code}", response.text)
            return False
    
    def step_3_get_profile(self):
        """Étape 3: Récupérer le profil (auto-créé au register)"""
        log_step(3, "Get Profile — Récupération du profil")
        
        response = self.client.get("/profiles/me", headers=self._headers())
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                profile = data.get("data", data)
            else:
                profile = data
            self.profile_id = profile.get("id")
            log_success(f"Profil récupéré — Profile ID: {self.profile_id}")
            return True
        else:
            log_error(f"Get profile échoué — {response.status_code}", response.text)
            return False
    
    def step_4_upload_cv(self, cv_path=None):
        """Étape 4: Upload un CV PDF"""
        log_step(4, "Upload CV — Envoi du fichier")
        
        # Si pas de fichier spécifié, créer un faux PDF minimal
        if not cv_path or not Path(cv_path).exists():
            log_info("Aucun fichier PDF trouvé, création d'un faux CV...")
            cv_path = "fake_cv.pdf"
            with open(cv_path, "wb") as f:
                f.write(b"%PDF-1.4\n")
                f.write(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
                f.write(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
                f.write(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>endobj\n")
                f.write(b"4 0 obj<< /Length 100 >>stream\n")
                f.write(b"BT /F1 12 Tf 100 700 Td (Python Django FastAPI PostgreSQL Docker) Tj ET\n")
                f.write(b"endstream endobj\n")
                f.write(b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n")
                f.write(b"trailer<< /Size 5 /Root 1 0 R >>\n")
                f.write(b"startxref\n314\n")
                f.write(b"%%EOF\n")
        
        with open(cv_path, "rb") as f:
            files = {"file": (Path(cv_path).name, f, "application/pdf")}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.client.post("/resumes/upload", files=files, headers=headers)
        
        if response.status_code in (200, 201):
            data = response.json()
            resume_data = data.get("data", data)
            self.resume_id = resume_data.get("id")
            log_success(f"CV uploadé — Resume ID: {self.resume_id}")
            log_info(f"Fichier: {resume_data.get('filename')}")
            log_info(f"Taille: {resume_data.get('file_size')} bytes")
            return True
        else:
            log_error(f"Upload échoué — {response.status_code}", response.text)
            return False
    
    def step_5_nlp_process(self):
        """Étape 5: Lancer l'extraction NLP"""
        log_step(5, "NLP Process — Extraction des compétences")
        
        response = self.client.post(
            f"/nlp/process/{self.resume_id}",
            headers=self._headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            nlp_data = data.get("data", data)
            self.skills = nlp_data.get("skills_extracted", [])
            processing_time = nlp_data.get("processing_time_ms", 0)
            
            log_success(f"NLP terminé en {processing_time}ms")
            log_info(f"Compétences extraites: {len(self.skills)}")
            for skill in self.skills:
                print(f"   • {skill}")
            return True
        else:
            log_error(f"NLP échoué — {response.status_code}", response.text)
            return False
    
    def step_6_verify_profile_skills(self):
        """Étape 6: Vérifier les skills agrégées sur le profil"""
        log_step(6, "Verify Skills — Vérification du profil")
        
        response = self.client.get(
            f"/nlp/skills/{self.profile_id}",
            headers=self._headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            skills_data = data.get("data", data)
            all_skills = skills_data.get("skills", [])
            total = skills_data.get("total", 0)
            
            log_success(f"Profil contient {total} compétences agrégées")
            for skill in all_skills:
                print(f"   • {skill}")
            return True
        else:
            log_error(f"Vérification échouée — {response.status_code}", response.text)
            return False
    
    def step_7_list_resumes(self):
        """Étape 7: Lister les CVs du profil"""
        log_step(7, "List Resumes — Liste des CVs")
        
        response = self.client.get(
            f"/resumes/profile/{self.profile_id}?page=1&limit=10",
            headers=self._headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            resumes_data = data.get("data", data)
            items = resumes_data.get("items", [])
            total = resumes_data.get("total", 0)
            
            log_success(f"{total} CV(s) trouvé(s) dans le profil")
            for item in items:
                print(f"   • ID {item['id']}: {item['filename']} ({item['file_size']} bytes)")
            return True
        else:
            log_error(f"Liste échouée — {response.status_code}", response.text)
            return False
    
    def run(self):
        """Exécuter le flow E2E complet"""
        print(f"{Colors.BLUE}\n{'='*60}")
        print("  SmartMatch Pro — Test End-to-End")
        print(f"{'='*60}{Colors.RESET}")
        print(f"URL: {BASE_URL}")
        print(f"Email de test: {TEST_EMAIL}")
        
        start_time = time.time()
        results = []
        
        try:
            results.append(("Register", self.step_1_register()))
            
            if not results[-1][1]:
                results.append(("Login (fallback)", self.step_2_login()))
            
            results.append(("Get Profile", self.step_3_get_profile()))
            results.append(("Upload CV", self.step_4_upload_cv()))
            
            if self.resume_id:
                results.append(("NLP Process", self.step_5_nlp_process()))
            
            if self.profile_id:
                results.append(("Verify Skills", self.step_6_verify_profile_skills()))
                results.append(("List Resumes", self.step_7_list_resumes()))
            
            elapsed = time.time() - start_time
            print(f"\n{Colors.BLUE}{'='*60}")
            print("  RÉSULTATS")
            print(f"{'='*60}{Colors.RESET}")
            
            passed = sum(1 for _, r in results if r)
            total = len(results)
            
            for name, result in results:
                status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
                print(f"  {status} — {name}")
            
            print(f"\n{Colors.BLUE}Total: {passed}/{total} étapes réussies{Colors.RESET}")
            print(f"Temps total: {elapsed:.2f}s")
            
            if passed == total:
                print(f"\n{Colors.GREEN}🎉 FLOW E2E COMPLET RÉUSSI !{Colors.RESET}")
                return 0
            else:
                print(f"\n{Colors.RED}⚠️  {total - passed} étape(s) en échec{Colors.RESET}")
                return 1
                
        except Exception as e:
            log_error(f"Erreur inattendue: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.client.close()

if __name__ == "__main__":
    import sys
    e2e = SmartMatchE2E()
    sys.exit(e2e.run())