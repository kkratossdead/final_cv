# Analyseur de CV avec IA 🤖

Ce projet utilise GPT-4 pour analyser automatiquement des CV au format PDF par rapport à une offre d'emploi et générer des rapports détaillés avec scoring.

## ✨ Fonctionnalités

- 📄 **Analyse automatique** de CV PDF avec extraction de texte
- 🎯 **Scoring intelligent** sur 100 points avec critères détaillés
- 📊 **Rapport structuré** avec points forts/faibles, compétences matchées/manquantes
- 💾 **Sauvegarde automatique** des résultats avec horodatage
- ⚙️ **Configuration flexible** via fichier de config
- 🚀 **Interface simplifiée** avec script de lancement automatique

## 🚀 Installation rapide

1. **Cloner le repository**
   ```bash
   git clone https://github.com/kkratossdead/Cv_Ia.git
   cd Cv_Ia
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer la clé API**
   
   **Méthode 1 : Secrets Streamlit (recommandée)**
   - Copiez `.streamlit/secrets.example.toml` vers `.streamlit/secrets.toml`
   - Remplacez `"your_openai_api_key_here"` par votre vraie clé API OpenAI
   
   **Méthode 2 : Fichier local**
   - Copiez `config_local.example.py` vers `config_local.py`
   - Ajoutez votre clé API OpenAI

4. **Lancer l'analyse**
   - Double-cliquer sur `run_analysis.bat` (Windows)
   - Ou `python script.py`

## 📁 Structure du projet

```
Cv_Ia/
├── script.py             # Script principal d'analyse avec rapport détaillé
├── config.py             # Configuration (clé API, paramètres)
├── config.example.py     # Exemple de configuration
├── requirements.txt      # Dépendances Python
├── job_offer.txt         # Offre d'emploi par défaut
├── job_offer_python.txt  # Exemple d'offre Python
├── run_analysis.bat      # Script de lancement Windows
├── pdfs/                 # Dossier pour vos CV PDF
│   └── cv_ay.pdf        # Exemple de CV
└── README.md            # Ce fichier
```

## ⚙️ Configuration

### 1. Clé API OpenAI
1. Copiez `config.example.py` vers `config.py`
2. Remplacez `"your-openai-api-key-here"` par votre vraie clé API OpenAI
3. **⚠️ Important** : Ne commitez jamais votre vraie clé API sur GitHub !

### 2. Offre d'emploi
- Éditez `job_offer.txt` avec votre offre d'emploi
- Ou créez un nouveau fichier et modifiez `JOB_OFFER_FILE` dans `config.py`

### 3. Paramètres avancés
Dans `config.py`, vous pouvez modifier :
- `GPT_MODEL` : Modèle GPT à utiliser
- `TEMPERATURE` : Créativité de l'analyse (0-1)
- `PDFS_DIRECTORY` : Dossier des CV

## 🎯 Utilisation

### Méthode 1 : Script automatique (Recommandé)
```bash
# Double-cliquez sur run_analysis.bat
# Ou dans un terminal :
run_analysis.bat
```

### Méthode 2 : Ligne de commande
```bash
# Script principal
python script.py
```

## 📊 Résultats et scoring

### Critères de notation (sur 100 points)
- **Compétences techniques requises** : 40 points
- **Expérience pertinente** : 30 points  
- **Formation et qualifications** : 15 points
- **Compétences soft skills** : 15 points

### Informations fournies
- ✅ **Score global** avec codage couleur
- 🎯 **Recommandation** (Recommandé/À considérer/Non recommandé)
- 💪 **Points forts** du candidat
- ⚠️ **Points faibles** ou lacunes
- 🔍 **Compétences correspondantes** à l'offre
- ❌ **Compétences manquantes** importantes
- 💼 **Analyse de l'expérience** pertinente
- 💭 **Commentaires détaillés** personnalisés

### Fichiers de sortie
- **Affichage console** : Résultats formatés et colorés
- **Fichier rapport** : `analyse_cv_YYYYMMDD_HHMMSS.txt`

## 📋 Exemples d'offres d'emploi

Le projet inclut plusieurs exemples :
- `job_offer.txt` : Développeur Full Stack Senior
- `job_offer_python.txt` : Développeur Backend Python Senior

## 🔧 Personnalisation avancée

### Modifier le prompt d'analyse
Éditez la fonction `analyze_cv_with_gpt()` dans les scripts pour :
- Ajuster les critères de scoring
- Modifier le format des résultats
- Ajouter des analyses spécifiques

### Ajouter de nouveaux formats
Le projet peut être étendu pour supporter :
- Documents Word (.docx)
- Fichiers texte (.txt)
- CV en ligne (URL)

## ⚠️ Prérequis et dépendances

- **Python 3.8+** installé
- **Compte OpenAI** avec crédits API
- **Connexion Internet** pour l'API GPT
- **Fichiers PDF lisibles** (pas d'images scannées sans OCR)

### Dépendances Python
```bash
pip install PyPDF2 openai
```

## 🐛 Dépannage

### Problèmes courants

| Problème | Solution |
|----------|----------|
| 🔴 Erreur de lecture PDF | Vérifiez que le PDF n'est pas protégé ou corrompu |
| 🔴 Erreur API OpenAI | Vérifiez votre clé API et vos crédits |
| 🔴 Pas de résultats | Assurez-vous que le dossier `pdfs/` contient des fichiers PDF |
| � Import PyPDF2 échoue | Exécutez `pip install PyPDF2` |
| 🔴 Encodage de caractères | Vérifiez que vos fichiers sont en UTF-8 |

### Logs et debug
Les erreurs sont affichées avec des emojis pour faciliter l'identification :
- ❌ Erreurs critiques
- ⚠️ Avertissements
- ✅ Succès
- 💡 Conseils

## 📈 Améliorations futures

- [ ] Interface graphique (GUI)
- [ ] Support de formats additionnels (DOCX, TXT)
- [ ] Analyse comparative entre candidats
- [ ] Export Excel/CSV des résultats
- [ ] Intégration avec ATS (Applicant Tracking Systems)
- [ ] Analyse de sentiment et soft skills
- [ ] API REST pour intégration dans d'autres outils

## 📄 Licence

Ce projet est fourni à des fins éducatives et de démonstration. Assurez-vous de respecter les conditions d'utilisation de l'API OpenAI.

---

**🎉 Bon recrutement avec l'IA !**
