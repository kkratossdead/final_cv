import os
import json
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
import streamlit as st

# ADD get_job_offer_by_id to your imports from db
from db import (
    init_db, insert_analysis, get_all_analyses,
    save_job_offer, get_analyses_by_job_offer,
    get_all_job_offers, get_job_offer_stats,
    get_job_offer_by_id,   # <-- add this
)


# === Gemini SDK ===
from google import genai
from google.genai import types

# ---------------------------
# Tarifs Gemini 2.5 Flash-Lite
# ---------------------------
# Prix par 1 MILLION de tokens
PRICE_INPUT_PER_M  = 0.10   # $ / 1e6 tokens input
PRICE_OUTPUT_PER_M = 0.40   # $ / 1e6 tokens output

MODEL = "gemini-2.5-flash-lite"

PROMPT_SYSTEM = """
Vous êtes un expert RH très exigeant.
Votre mission : analyser le CV (fourni en PDF) en fonction de l’offre d’emploi fournie (texte).

──────────────────────────────
⚠️ Règles strictes de sortie :
- Répondez UNIQUEMENT avec un JSON valide (UTF-8), sans aucun texte avant/après.
- Le JSON doit contenir exactement et uniquement les champs suivants (pas d’ajout, pas de suppression).
- Les champs numériques doivent rester des nombres (pas de texte).
- N'utilisez pas de sous-objets ou de champs imbriqués (flat JSON).
- Comptez le nombre de pages traitées du PDF et placez ce nombre (entier) dans "pages_analysees".
- Mettez la valeur LITTÉRALE "GEMINI " (avec un espace final) dans "methode_analyse".
- Ne retournez AUCUN autre champ, objet ou commentaire hors JSON.

──────────────────────────────
📋 Champs attendus dans le JSON final :
{
  "nom_prenom": "Nom et prénom du candidat (extrait du CV)",
  "score_technique": 0,
  "score_experience": 0,
  "score_formation": 0,
  "score_soft_skills": 0,
  "score_global": 0,
  "points_forts": [],
  "points_faibles": [],
  "competences_matchees": [],
  "competences_manquantes": [],
  "competences_deduites": [],
  "experience_pertinente": "",
  "recommandation": "",
  "commentaires": "",
  "pages_analysees": 0,
  "methode_analyse": "GEMINI "
}

──────────────────────────────
🔢 Critères de notation (base 100) :
- Compétences techniques requises : 40 points max
- Expérience pertinente : 30 points max
- Formation et qualifications : 15 points max
- Soft skills : 15 points max
- "score_global" = somme des 4 sous-scores (max 100).
- "recommandation" ∈ { "Recommandé", "À considérer", "Non recommandé" }

──────────────────────────────
📌 Règles de pondération :
- L’expérience supérieure au minimum requis est toujours positive (jamais négative).
- Si une compétence ou une dimension est mal détaillée, attribuez un score partiel, mais ne réduisez pas à zéro si l’expérience est proche.
- Formation :
  • Formation directement liée au poste → score élevé.
  • Formation partiellement liée → score moyen.
  • Formation hors domaine → score 0.
- Expérience :
  • Alignée avec le poste → score élevé.
  • Partielle (liée à une partie des missions/technos) → score intermédiaire.
  • Totalement hors domaine (ex : commercial, événementiel, communication, vente, etc.) → score 0.
  ⚠️ Ne jamais attribuer de points si le domaine n’est pas lié au poste.
- Soft skills :
  • Comptabiliser uniquement les soft skills en rapport direct avec le poste.
  • Ne pas accorder de points pour des compétences génériques (vente, management, communication non technique).

──────────────────────────────
🚨 Conditions bloquantes :
- Si le CV n’a AUCUN RAPPORT direct avec le poste demandé,
- Ou si le poste est TECHNIQUE et que le CV est clairement NON TECHNIQUE,
  → mettre tous les sous-scores à 0,
  → "score_global": 0,
  → "recommandation": "Non recommandé",
  → "commentaires": "Profil hors filière, sans lien avec le poste".

──────────────────────────────
📌 Règles de cohérence :
- Les "compétences manquantes" doivent venir UNIQUEMENT des exigences de l’offre donnée.
- Les "competences_deduites" doivent inclure les compétences implicites (ex : projet en React → déduire "React", "JavaScript", "Front-end Development").
- Toujours se baser UNIQUEMENT sur l’offre d’emploi fournie (ne pas réutiliser d’infos d’analyses précédentes).
- Ne jamais insérer de compétences hors domaine (ex : CRM/marketing/commerce si l’offre est Full Stack Developer).
"""


EXPECTED_KEYS = [
    "nom_prenom", "score_technique", "score_experience", "score_formation",
    "score_soft_skills", "score_global", "points_forts", "points_faibles",
    "competences_matchees", "competences_manquantes", "experience_pertinente",
    "recommandation", "commentaires", "pages_analysees", "methode_analyse"
]

load_dotenv()

st.set_page_config(
    page_title="Analyseur de CV avec IA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_gemini():
    # Pour initialiser la clé API dans l'environnement (Windows) :
    # set GEMINI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # Pour Linux/Mac :
    # export GEMINI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Clé API GEMINI_API_KEY non configurée.")
        st.stop()
        # Client Gemini (lit GEMINI_API_KEY depuis l'env)
        # Exemple de clé API insérée manuellement (à ne pas faire en production)
        # api_key = "sk-ect"
    return genai.Client()

def analyze_cv_with_gemini(pdf_bytes: bytes, job_offer_text: str, client: genai.Client):
    """
    Envoie le PDF directement au modèle (pas d'OCR local).
    Demande une réponse JSON stricte (response_mime_type='application/json').
    """
    try:
        contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            types.Part.from_text(text=f"Voici l'offre d'emploi à analyser :\n{job_offer_text}"),
            types.Part.from_text(text=PROMPT_SYSTEM),
        ]

        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                # max_output_tokens=4096,
            ),
        )

        # Texte attendu = JSON pur
        output_text = resp.text or ""

        # Usage tokens (si dispo)
        um = getattr(resp, "usage_metadata", None)
        tokens = {
            "prompt": getattr(um, "input_token_count", None),
            "completion": getattr(um, "output_token_count", None),
            "total": getattr(um, "total_token_count", None),
        }

        return {"content": output_text, "tokens": tokens}

    except Exception as e:
        st.error(f"❌ Erreur Gemini : {e}")
        return None

def display_analysis(analysis_text, filename):
    """Affiche l'analyse structurée (scores, listes, etc.)."""
    try:
        clean = analysis_text.strip()
        if clean.startswith("```json"):
            clean = clean[len("```json"):].strip()
        if clean.endswith("```"):
            clean = clean[:-3].strip()

        analysis = json.loads(clean)

        st.header(f"📊 Analyse de {filename}")

        score_global    = analysis.get("score_global", 0)
        score_technique = analysis.get("score_technique")
        score_experience= analysis.get("score_experience")
        score_formation = analysis.get("score_formation")
        score_soft      = analysis.get("score_soft_skills")

        st.subheader(f"🎯 Score Global : {score_global}/100")
        if score_global is not None:
            if score_global >= 80:
                st.success(f"Excellent candidat ({score_global}/100)")
            elif score_global >= 60:
                st.warning(f"Bon candidat ({score_global}/100)")
            else:
                st.error(f"Candidat à améliorer ({score_global}/100)")
            st.progress(min(max(score_global, 0), 100) / 100)

        st.subheader("🔢 Détails des sous-scores")
        cols = st.columns(4)
        cols[0].metric("Technique", f"{score_technique}/40" if score_technique is not None else "N/A")
        cols[1].metric("Expérience", f"{score_experience}/30" if score_experience is not None else "N/A")
        cols[2].metric("Formation", f"{score_formation}/15" if score_formation is not None else "N/A")
        cols[3].metric("Soft skills", f"{score_soft}/15" if score_soft is not None else "N/A")

        recommandation = analysis.get("recommandation", "Non spécifiée")
        st.subheader("✅ Recommandation")
        if isinstance(recommandation, str) and "Recommandé" in recommandation:
            st.success(f"✅ **{recommandation}**")
        elif isinstance(recommandation, str) and "considérer" in recommandation.lower():
            st.warning(f"⚠️ **{recommandation}**")
        else:
            st.error(f"❌ **{recommandation}**")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💪 Points Forts")
            for pt in analysis.get("points_forts", []) or []:
                st.write(f"• {pt}")
            st.subheader("✅ Compétences Matchées")
            for comp in analysis.get("competences_matchees", []) or []:
                st.write(f"• {comp}")
        with col2:
            st.subheader("⚠️ Points Faibles")
            for pt in analysis.get("points_faibles", []) or []:
                st.write(f"• {pt}")
            st.subheader("❌ Compétences Manquantes")
            for comp in analysis.get("competences_manquantes", []) or []:
                st.write(f"• {comp}")

        st.subheader("💼 Expérience Pertinente")
        st.write(analysis.get("experience_pertinente", "Non spécifiée"))
        st.subheader("📝 Commentaires Détaillés")
        st.write(analysis.get("commentaires", "Aucun commentaire"))

        st.subheader("📋 Informations Techniques")
        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("Pages analysées", analysis.get("pages_analysees", "N/A"))
        with col4:
            st.metric("Méthode", analysis.get("methode_analyse", "N/A"))
        with col5:
            st.metric("Date", datetime.now().strftime("%d/%m/%Y %H:%M"))

        return analysis

    except json.JSONDecodeError:
        st.error("❌ Erreur lors du parsing de l'analyse JSON")
        st.text_area("Analyse brute :", analysis_text, height=300)
        return None


def _parse_dt_any(s: str):
    # Try common formats; fall back to raw string for stable ordering
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        # ISO 8601 tolerant
        return datetime.fromisoformat(s)
    except Exception:
        return s  # last resort: compare as string

def sort_job_offers_newest_first(job_offers):
    # Expected tuple shape from your code: (ID, Titre, DateCreation, NbAnalyses)
    # If your get_all_job_offers returns a different shape, adjust the index for date.
    return sorted(job_offers, key=lambda r: _parse_dt_any(r[2]), reverse=True)


def main():
    """Application Streamlit — version Gemini 2.5 Flash-Lite"""
    init_db()

    page = st.sidebar.radio(
        "Navigation",
        ["Analyse de CV", "Gestion des offres", "Historique des analyses"]
    )

    if page == "Analyse de CV":
        st.title("🚀 Analyseur de CV — Gemini 2.5 Flash-Lite")
        st.markdown("---")
        st.markdown("**Analysez des CV (PDF) par rapport à une offre d'emploi**")

        with st.sidebar:
            st.header("⚙️ Configuration")
            if os.getenv("GEMINI_API_KEY"):
                st.success("✅ Clé API Gemini configurée")
            else:
                st.error("❌ GEMINI_API_KEY non configurée")
                st.info("Ajoutez GEMINI_API_KEY dans vos variables d'environnement")
            st.subheader("🎛️ Paramètres")
            st.markdown("---")
            st.markdown("**💡 Instructions:**")
            st.markdown("1. Choisissez une offre d'emploi existante (onglet « Gestion des offres » pour en créer)")
            st.markdown("2. Uploadez un ou plusieurs CV (PDF)")
            st.markdown("3. Cliquez sur 'Analyser'")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("📋 Choisir une offre existante")

            job_offers = get_all_job_offers()  # [(id, title, created_at, nb_analyses), ...]
            if job_offers:
                job_offers_sorted = sort_job_offers_newest_first(job_offers)
                label_map = {
                    f"{row[1]} — {row[2]}  ({row[0][:8]}…)": row[0] for row in job_offers_sorted
                }
                selected_label = st.selectbox(
                    "Sélectionnez une offre d'emploi (la plus récente apparaît en premier) :",
                    options=list(label_map.keys()),
                )
                selected_job_offer_id = label_map[selected_label]
                st.info(f"Offre sélectionnée: {selected_label}")
            else:
                selected_job_offer_id = None
                st.warning("Aucune offre disponible. Créez-en d’abord dans l’onglet « Gestion des offres ».")


        with col_right:
            st.subheader("📄 Upload de CV")
            uploaded_files = st.file_uploader(
                "Choisissez un ou plusieurs CV (PDF)",
                type=['pdf'],
                accept_multiple_files=True
            )
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} fichier(s) sélectionné(s)")
                for file in uploaded_files:
                    st.write(f"• {file.name}")
        # --- éviter UnboundLocalError sur les reruns Streamlit ---
        analyses = []
        job_offer_id = None
        job_title = ""
        job_offer_text = ""

        if st.button("🔍 Analyser les CV", type="primary", use_container_width=True):
            if not selected_job_offer_id:
                st.error("⚠️ Aucune offre sélectionnée. Rendez-vous dans « Gestion des offres » pour en créer ou en choisir une.")
                return
            if not uploaded_files:
                st.error("⚠️ Veuillez uploader au moins un CV")
                return

            # Fetch the full job offer (title + content) by ID
            job_row = get_job_offer_by_id(selected_job_offer_id)
            # Accept either dict or tuple return shapes
            if isinstance(job_row, dict):
                job_title = job_row.get("title") or job_row.get("titre") or ""
                job_offer_text = job_row.get("content") or job_row.get("texte") or ""
            else:
                # Common tuple: (ID, Title, Content, CreatedAt) -> adjust if your DB differs
                job_title = job_row[1] if len(job_row) > 1 else ""
                job_offer_text = job_row[2] if len(job_row) > 2 else ""

            if not job_offer_text.strip():
                st.error("⚠️ Contenu de l’offre introuvable. Vérifiez votre base de données et la fonction get_job_offer_by_id.")
                return

            job_offer_id = selected_job_offer_id  # we reuse the existing ID
            st.info(f"🧾 Offre utilisée : {job_title} ({job_offer_id[:8]}…)")

            st.markdown("---")

            client = initialize_gemini()

            st.markdown("---")
            st.header("📊 Résultats de l'analyse")

            progress_bar = st.progress(0)
            status_text = st.empty()
            analyses = []

            for i, uploaded_file in enumerate(uploaded_files, start=1):
                status_text.text(f"Analyse en cours : {uploaded_file.name} ({i}/{len(uploaded_files)})")
                progress_bar.progress((i - 1) / len(uploaded_files))

                pdf_bytes = uploaded_file.read()
                result = analyze_cv_with_gemini(pdf_bytes, job_offer_text, client)

                if result:
                    analysis_text = result["content"]
                    tokens_used   = result["tokens"]

                    # Coût estimé (si usage connu)
                    in_tok  = tokens_used.get("prompt") or 0
                    out_tok = tokens_used.get("completion") or 0
                    total_tok = tokens_used.get("total") or (in_tok + out_tok)
                    cost_cv = (in_tok / 1_000_000) * PRICE_INPUT_PER_M + (out_tok / 1_000_000) * PRICE_OUTPUT_PER_M

                    st.success(f"✅ Analyse terminée pour {uploaded_file.name}")
                    parsed = display_analysis(analysis_text, uploaded_file.name)

                    if parsed:
                        insert_analysis(uploaded_file.name, parsed, job_offer_id)

                    # st.info(
                    #     # f"🧮 **Tokens** : {total_tok}  "
                    #     # f"(prompt {in_tok} / completion {out_tok})  "
                    #     # f"— **Coût estimé : ${cost_cv:.6f}**"
                    # )

                    analyses.append({
                        "filename": uploaded_file.name,
                        "analysis": parsed if parsed else analysis_text,
                        "tokens":   {"prompt": in_tok, "completion": out_tok, "total": total_tok},
                        "cost_usd": cost_cv
                    })
                    st.markdown("---")
                else:
                    st.error(f"❌ Échec de l'analyse pour {uploaded_file.name}")

            progress_bar.progress(1.0)
            status_text.text("✅ Analyse terminée !")
            if len(analyses) > 0:
                st.success(f"🎉 {len(analyses)}/{len(uploaded_files)} CV(s) analysé(s) avec succès")

                results_json = {
                    "metadata": {
                        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "nombre_cv_analyses": len(analyses),
                        "modele_utilise": MODEL,
                    },
                    "job_offer": {
                        "id": job_offer_id,
                        "title": job_title,
                        "content": job_offer_text,
                    },
                    "analyses": analyses
                }

                st.download_button(
                    label="📥 Télécharger résultats (JSON)",
                    data=json.dumps(results_json, ensure_ascii=False, indent=2),
                    file_name=f"analyse_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

                          

    elif page == "Gestion des offres":
        st.title("📋 Gestion des offres d'emploi")
        st.markdown("---")

        st.subheader("➕ Ajouter une nouvelle offre d'emploi")
        with st.form("create_job_offer_form", clear_on_submit=True):
            new_job_title = st.text_input("Titre de l'offre", placeholder="Ex: Développeur Python Senior - Tech Corp")
            new_job_content = st.text_area("Contenu de l'offre", height=200, placeholder="Description, missions, compétences requises…")
            submitted = st.form_submit_button("Enregistrer l'offre", type="primary", use_container_width=False)

        if submitted:
            if not new_job_title.strip() or not new_job_content.strip():
                st.error("Veuillez renseigner le titre et le contenu de l'offre.")
            else:
                new_id = save_job_offer(new_job_title.strip(), new_job_content.strip())
                st.success(f"✅ Offre créée (ID: {new_id[:8]}…). Elle est maintenant disponible dans « Analyse de CV ».")
                st.toast("Offre ajoutée !", icon="✅")

        tab1, tab2 = st.tabs(["📊 Vue d'ensemble", "🔍 Détails par offre"])

        with tab1:
            st.subheader("📈 Statistiques des offres d'emploi")
            job_offers = get_all_job_offers()
            if job_offers:
                job_offers = sort_job_offers_newest_first(job_offers)  # <-- ajout
                import pandas as pd
                df = pd.DataFrame(job_offers, columns=["ID", "Titre", "Date de création", "Nb CV analysés"])
                df["ID court"] = df["ID"].apply(lambda x: x[:8] + "...")
                df_display = df[["ID court", "Titre", "Date de création", "Nb CV analysés"]]
                st.dataframe(df_display, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total offres", len(job_offers))
                with col2:
                    total_cv = sum([job[3] for job in job_offers])
                    st.metric("Total CV analysés", total_cv)
                with col3:
                    if len(job_offers) > 0:
                        avg_cv_per_job = (total_cv / len(job_offers)) if total_cv else 0
                        st.metric("Moyenne CV/offre", f"{avg_cv_per_job:.1f}")
            else:
                st.info("Aucune offre d'emploi trouvée. Analysez des CV pour commencer !")

        with tab2:
            st.subheader("🔍 Analyses par offre d'emploi")
            job_offers = get_all_job_offers()
            if job_offers:
                job_offers = sort_job_offers_newest_first(job_offers)  # <-- ajout
                job_titles = {f"{job[1]} ({job[0][:8]}...)": job[0] for job in job_offers}
                selected_job_title = st.selectbox("Choisissez une offre d'emploi:", options=list(job_titles.keys()))
                if selected_job_title:
                    job_offer_id = job_titles[selected_job_title]
                    stats = get_job_offer_stats(job_offer_id)
                    if stats and stats[0] > 0:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1: st.metric("CV analysés", int(stats[0]))
                        with col2: st.metric("Score moyen", f"{stats[1]:.1f}/100")
                        with col3: st.metric("Meilleur score", f"{stats[2]}/100")
                        with col4: st.metric("Score minimum", f"{stats[3]}/100")
                        st.markdown("---")

                        analyses = get_analyses_by_job_offer(job_offer_id)
                        st.subheader("📄 CV analysés pour cette offre")
                        for i, analysis in enumerate(analyses):
                            with st.expander(f"🏆 {analysis[0]} - Score: {analysis[1]}/100 ({analysis[8]})", expanded=(i==0)):
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    st.write("**Commentaire:**")
                                    st.write(analysis[6])
                                with col2:
                                    st.write("**Scores détaillés:**")
                                    st.write(f"🎯 Global: {analysis[1]}/100")
                                    st.write(f"⚙️ Technique: {analysis[2]}/40")
                                    st.write(f"📈 Expérience: {analysis[3]}/30")
                                    st.write(f"🎓 Formation: {analysis[4]}/15")
                                    st.write(f"🤝 Soft Skills: {analysis[5]}/15")
                                    st.write(f"📅 Date: {analysis[7]}")
                    else:
                        st.info("Aucune analyse trouvée pour cette offre d'emploi.")
            else:
                st.info("Aucune offre d'emploi trouvée.")

    elif page == "Historique des analyses":
        st.title("📑 Historique des analyses (BDD)")
        st.markdown("---")
        rows = get_all_analyses()
        if rows:
            job_offers = get_all_job_offers()
            if job_offers and len(job_offers) > 1:
                job_filter_options = ["Toutes les offres"] + [f"{job[1]} ({job[0][:8]}...)" for job in job_offers]
                selected_filter = st.selectbox("Filtrer par offre d'emploi:", job_filter_options)
                if selected_filter != "Toutes les offres":
                    selected_job_id = None
                    for job in job_offers:
                        if f"{job[1]} ({job[0][:8]}...)" == selected_filter:
                            selected_job_id = job[0]
                            break
                    rows = [r for r in rows if r[9] == selected_job_id]

            if rows:
                st.dataframe(
                    [{
                        "Nom/Prénom": r[0],
                        "Score global /100": r[1],
                        "Technique /40": r[2],
                        "Expérience /30": r[3],
                        "Formation /15": r[4],
                        "Soft skills /15": r[5],
                        "Offre d'emploi": r[8] if r[8] else "Non spécifiée",
                        "Commentaire": (r[6][:100] + "...") if len(str(r[6])) > 100 else r[6],
                        "Date": r[7]
                    } for r in rows],
                    use_container_width=True
                )
                col1, col2, col3 = st.columns(3)
                scores = [r[1] for r in rows if r[1] is not None]
                if scores:
                    with col1: st.metric("Analyses totales", len(rows))
                    with col2: st.metric("Score moyen", f"{sum(scores)/len(scores):.1f}/100")
                    with col3: st.metric("Meilleur score", f"{max(scores)}/100")
            else:
                st.info("Aucune analyse trouvée pour le filtre sélectionné.")
        else:
            st.info("Aucune analyse enregistrée dans la base de données.")

if __name__ == "__main__":
    main()
