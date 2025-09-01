import sqlite3
from datetime import datetime
import hashlib
import json

DB_PATH = "new.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table pour les offres d'emploi
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_offers (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            created_date TEXT
        )
    ''')
    
    # Table pour les analyses de CV
    c.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_offer_id TEXT,
            nom_prenom TEXT,
            filename TEXT,
            score_global INTEGER,
            score_technique INTEGER,
            score_experience INTEGER,
            score_formation INTEGER,
            score_soft_skills INTEGER,
            commentaire TEXT,
            date TEXT,
            FOREIGN KEY (job_offer_id) REFERENCES job_offers (id)
        )
    ''')
    # Index utiles
    c.execute("CREATE INDEX IF NOT EXISTS idx_job_offers_created_date ON job_offers(created_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_analyses_job_offer_id ON analyses(job_offer_id)")

    # Vérifier si la colonne job_offer_id existe, sinon l'ajouter (migration)
    try:
        c.execute("PRAGMA table_info(analyses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'job_offer_id' not in columns:
            print("🔄 Migration: Ajout de la colonne job_offer_id...")
            c.execute('ALTER TABLE analyses ADD COLUMN job_offer_id TEXT')
            
            # Créer une offre par défaut pour les analyses existantes
            default_job_id = "default_legacy"
            c.execute('''
                INSERT OR IGNORE INTO job_offers (id, title, content, created_date)
                VALUES (?, ?, ?, ?)
            ''', (
                default_job_id,
                "Offre héritée (analyses antérieures)",
                "Analyses réalisées avant l'implémentation du système d'offres d'emploi",
                datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            ))
            
            # Mettre à jour les analyses existantes
            c.execute('UPDATE analyses SET job_offer_id = ? WHERE job_offer_id IS NULL', (default_job_id,))
            print("✅ Migration terminée")
    except Exception as e:
        print(f"⚠️ Erreur de migration : {e}")
    
    conn.commit()
    conn.close()

def create_job_offer_id(job_offer_text):
    """Crée un ID unique basé sur le contenu de l'offre d'emploi"""
    return hashlib.md5(job_offer_text.encode()).hexdigest()[:12]

def save_job_offer(title, content):
    """Sauvegarde une offre d'emploi et retourne son ID"""
    job_id = create_job_offer_id(content)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Vérifier si l'offre existe déjà
    c.execute('SELECT id FROM job_offers WHERE id = ?', (job_id,))
    if not c.fetchone():
        c.execute('''
            INSERT INTO job_offers (id, title, content, created_date)
            VALUES (?, ?, ?, ?)
        ''', (job_id, title, content, datetime.now().strftime('%d/%m/%Y %H:%M:%S')))
        conn.commit()
    
    conn.close()
    return job_id

def insert_analysis(filename, analysis, job_offer_id):
    """Insère une analyse de CV liée à une offre d'emploi"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    nom_prenom = analysis.get("nom_prenom", "")
    c.execute('''
        INSERT INTO analyses (
            job_offer_id, nom_prenom, filename, score_global, score_technique, 
            score_experience, score_formation, score_soft_skills, commentaire, date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_offer_id,
        nom_prenom,
        filename,
        analysis.get("score_global", 0),
        analysis.get("score_technique", 0),
        analysis.get("score_experience", 0),
        analysis.get("score_formation", 0),
        analysis.get("score_soft_skills", 0),
        analysis.get("commentaires", ""),
        datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    ))
    conn.commit()
    conn.close()

def get_all_analyses():
    """Récupère toutes les analyses avec les informations de l'offre d'emploi"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Vérifier la structure de la table
        c.execute("PRAGMA table_info(analyses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'job_offer_id' in columns:
            # Nouvelle structure avec job_offer_id
            c.execute('''
                SELECT a.nom_prenom, a.score_global, a.score_technique, a.score_experience, 
                       a.score_formation, a.score_soft_skills, a.commentaire, a.date,
                       j.title as job_title, a.job_offer_id
                FROM analyses a
                LEFT JOIN job_offers j ON a.job_offer_id = j.id
                ORDER BY a.id DESC
            ''')
        else:
            # Ancienne structure sans job_offer_id
            c.execute('''
                SELECT nom_prenom, score_global, score_technique, score_experience, 
                       score_formation, score_soft_skills, commentaire, date,
                       'Non spécifiée' as job_title, NULL as job_offer_id
                FROM analyses 
                ORDER BY id DESC
            ''')
        
        rows = c.fetchall()
        conn.close()
        return rows
        
    except Exception as e:
        print(f"Erreur dans get_all_analyses: {e}")
        conn.close()
        return []

def get_analyses_by_job_offer(job_offer_id):
    """Récupère toutes les analyses pour une offre d'emploi spécifique"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT a.nom_prenom, a.score_global, a.score_technique, a.score_experience, 
               a.score_formation, a.score_soft_skills, a.commentaire, a.date, a.filename
        FROM analyses a
        WHERE a.job_offer_id = ?
        ORDER BY a.score_global DESC
    ''', (job_offer_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_job_offers():
    """Récupère toutes les offres d'emploi avec le nombre d'analyses"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Vérifier si la table job_offers existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_offers'")
        if not c.fetchone():
            conn.close()
            return []
        
        c.execute('''
            SELECT j.id, j.title, j.created_date, COUNT(a.id) as nb_analyses
            FROM job_offers j
            LEFT JOIN analyses a ON j.id = a.job_offer_id
            GROUP BY j.id, j.title, j.created_date
            ORDER BY j.created_date DESC
        ''')
        rows = c.fetchall()
        conn.close()
        return rows
        
    except Exception as e:
        print(f"Erreur dans get_all_job_offers: {e}")
        conn.close()
        return []

def get_job_offer_stats(job_offer_id):
    """Récupère les statistiques d'une offre d'emploi"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT 
            COUNT(*) as total_cv,
            AVG(score_global) as score_moyen,
            MAX(score_global) as meilleur_score,
            MIN(score_global) as score_min
        FROM analyses
        WHERE job_offer_id = ?
    ''', (job_offer_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_job_offer_by_id(job_offer_id: str):
    """Retourne une offre d'emploi par ID.
    Renvoie un tuple (id, title, content, created_date) ou None si introuvable.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, title, content, created_date
        FROM job_offers
        WHERE id = ?
        LIMIT 1
    ''', (job_offer_id,))
    row = c.fetchone()
    conn.close()
    return row
