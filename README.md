# CV Gemini - Installation sur un PC vierge (Windows)

Ce projet permet d'analyser des CV PDF par rapport à une offre d'emploi grâce à l'IA Gemini de Google.

## Prérequis
- Un PC sous Windows
- Connexion Internet

## 1. Installer Python
1. Va sur https://www.python.org/downloads/
2. Télécharge la dernière version stable de Python 3 (ex: Python 3.11 ou plus).
3. Lance l'installateur et coche **"Add Python to PATH"** avant de cliquer sur "Install Now".

## 2. Installer Git (optionnel mais recommandé)
1. Va sur https://git-scm.com/download/win
2. Installe Git (laisser les options par défaut)

## 3. Télécharger le projet
- Clique sur "Code" > "Download ZIP" sur GitHub, ou clone le repo avec Git :

```powershell
git clone <url-du-repo>
```

Décompresse le dossier si besoin.

## 4. Ouvrir un terminal dans le dossier du projet
- Clique droit dans le dossier `cv_gemini` > "Ouvrir dans le terminal PowerShell".

## 5. Créer un environnement virtuel (recommandé)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 6. Installer les dépendances
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Configurer la clé API Gemini
- Obtiens une clé API Gemini sur https://aistudio.google.com/app/apikey
- Ajoute-la dans tes variables d'environnement :

```powershell
$env:GEMINI_API_KEY="sk-..."
```

Ou crée un fichier `.env` dans le dossier du projet avec :
```
GEMINI_API_KEY=sk-...
```

## 8. Lancer l'application
```powershell
streamlit run app.py
```

L'application s'ouvre dans ton navigateur.

---

**Remarque** :
- Si tu as une erreur "module not found", vérifie que l'environnement virtuel est bien activé.
- Pour Linux/Mac, adapte les commandes d'environnement.
