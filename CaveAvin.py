# CaveAvin.py
import sqlite3

class DB:
    def __init__(self, db_name="cave_a_vin.db"):
        print(f"Connexion à la base de données {db_name}...")
        try:
            self.conn = sqlite3.connect(db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.init_db()
            print("Connexion réussie !")
        except sqlite3.Error as e:
            print(f"Erreur de connexion à la base de données: {e}")
            self.conn = None

    def init_db(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mot_de_passe TEXT NOT NULL
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS etageres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            emplacement TEXT,
            places_totales INTEGER NOT NULL,
            places_disponibles INTEGER NOT NULL,
            utilisateur_id INTEGER NOT NULL,
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bouteilles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            annee INTEGER,
            type TEXT,
            domaine TEXT,
            quantite INTEGER DEFAULT 1,
            note REAL,
            commentaire TEXT,
            statut TEXT CHECK(statut IN ('en stock','archivé')) DEFAULT 'en stock',
            etiquette TEXT,
            supprime INTEGER DEFAULT 0,
            etagere_id INTEGER,
            utilisateur_id INTEGER,
            FOREIGN KEY (etagere_id) REFERENCES etageres(id),
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bouteille_nom TEXT NOT NULL,
            bouteille_type TEXT NOT NULL,
            bouteille_annee INTEGER NOT NULL,
            bouteille_domaine TEXT,
            utilisateur_id INTEGER NOT NULL,
            note REAL,
            commentaire TEXT,
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        )""")

        self.conn.commit()


# Classes métier (inchangées)
class Bouteille:
    def __init__(self, nom, annee, type_vin, domaine=None, quantite=1, note=None,
                 commentaire=None, statut='en stock', etiquette=None,
                 id=None, etagere_id=None, utilisateur_id=None):
        self.id = id
        self.nom = nom
        self.annee = annee
        self.type_vin = type_vin
        self.domaine = domaine
        self.quantite = quantite
        self.note = note
        self.commentaire = commentaire
        self.statut = statut
        self.etiquette = etiquette
        self.etagere_id = etagere_id
        self.utilisateur_id = utilisateur_id

class Etagere:
    def __init__(self, nom, emplacement=None, places_totales=0, places_disponibles=0, id=None, utilisateur_id=None):
        self.id = id
        self.nom = nom
        self.emplacement = emplacement
        self.places_totales = places_totales
        self.places_disponibles = places_disponibles
        self.utilisateur_id = utilisateur_id
        self.bouteilles = []

class Utilisateur:
    def __init__(self, nom, email, mot_de_passe, utilisateur_id=None, conn=None):
        self.utilisateur_id = utilisateur_id
        self.nom = nom
        self.email = email
        self.mot_de_passe = mot_de_passe
        self.conn = conn

    def sauvegarder(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO utilisateurs (nom, email, mot_de_passe) VALUES (?,?,?)",
                       (self.nom, self.email, self.mot_de_passe))
        self.conn.commit()
        self.utilisateur_id = cursor.lastrowid

    def obtenir_par_email(self, email):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM utilisateurs WHERE email=?", (email,))
        row = cursor.fetchone()
        if row:
            return Utilisateur(row['nom'], row['email'], row['mot_de_passe'], row['id'], self.conn)
        return None


class Cave_a_vin:
    def __init__(self):
        self.db = DB()
        self.conn = self.db.conn

    # Étagères
    def lister_etageres(self, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM etageres WHERE utilisateur_id=?", (utilisateur_id,))
        rows = cursor.fetchall()
        etageres = []
        for row in rows:
            if row['nom'] == 'Consommées':
                continue
            
            etag = dict(row)

            cursor.execute("SELECT * FROM bouteilles WHERE etagere_id=? AND utilisateur_id=? AND supprime=0", (etag['id'], utilisateur_id))
            br = cursor.fetchall()
            
            etag['bouteilles'] = [dict(b) for b in br if b['statut'] == 'en stock']
            etag['nb_bouteilles'] = len(etag['bouteilles'])
            etageres.append(etag)
            
        return etageres

    def ajouter_etagere(self, nom, emplacement, places_totales, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO etageres (nom, emplacement, places_totales, places_disponibles, utilisateur_id)
            VALUES (?,?,?,?,?)
        """, (nom, emplacement, places_totales, places_totales, utilisateur_id))
        self.conn.commit()

    def obtenir_etagere(self, etagere_id, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM etageres WHERE id=? AND utilisateur_id=?", (etagere_id, utilisateur_id))
        return cursor.fetchone()

    def modifier_etagere(self, etagere_id, nom, emplacement, places_totales, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE etageres SET nom=?, emplacement=?, places_totales=? 
            WHERE id=? AND utilisateur_id=?
        """, (nom, emplacement, places_totales, etagere_id, utilisateur_id))
        self.conn.commit()

    def supprimer_etagere(self, etagere_id, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bouteilles WHERE etagere_id=? AND utilisateur_id=?", (etagere_id, utilisateur_id))
        count = cursor.fetchone()[0]
        if count > 0:
            raise Exception("Impossible de supprimer une étagère contenant des bouteilles.")
        
        cursor.execute("DELETE FROM etageres WHERE id=? AND utilisateur_id=?", (etagere_id, utilisateur_id))
        self.conn.commit()

    # Bouteilles
    def ajouter_bouteille(self, nom, annee, type_vin, domaine=None, quantite=1, note=None,
                          commentaire=None, statut='en stock', etagere_id=None, utilisateur_id=None, etiquette=None):
        cursor = self.conn.cursor()
        if etagere_id:
            cursor.execute("SELECT places_disponibles FROM etageres WHERE id=? AND utilisateur_id=?", (etagere_id, utilisateur_id))
            places = cursor.fetchone()
            if places is None or places['places_disponibles'] < quantite:
                raise Exception("Pas assez de place sur l'étagère ou étagère invalide.")
            cursor.execute("UPDATE etageres SET places_disponibles = places_disponibles - ? WHERE id=?", (quantite, etagere_id))

        cursor.execute("""
            INSERT INTO bouteilles (nom, annee, type, domaine, quantite, note, commentaire, statut, etagere_id, utilisateur_id, etiquette)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (nom, annee, type_vin, domaine, quantite, note, commentaire, statut, etagere_id, utilisateur_id, etiquette))
        self.conn.commit()

    def obtenir_bouteille(self, bouteille_id, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bouteilles WHERE id=? AND utilisateur_id=?", (bouteille_id, utilisateur_id))
        row = cursor.fetchone()
        return row

    def modifier_bouteille(self, bouteille_id, nom, annee, type_vin, domaine, quantite, note, commentaire, statut, etagere_id, utilisateur_id, etiquette=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE bouteilles SET nom=?, annee=?, type=?, domaine=?, quantite=?, note=?, commentaire=?, statut=?, etagere_id=?, etiquette=?
            WHERE id=? AND utilisateur_id=?
        """, (nom, annee, type_vin, domaine, quantite, note, commentaire, statut, etagere_id, etiquette, bouteille_id, utilisateur_id))
        self.conn.commit()

    def marquer_bouteille_supprimee(self, bouteille_id, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE bouteilles SET supprime=1 WHERE id=? AND utilisateur_id=?", (bouteille_id, utilisateur_id))
        self.conn.commit()

    def consommer_bouteille(self, bouteille_id, quantite_consomme, note=None, commentaire=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bouteilles WHERE id=?", (bouteille_id,))
        b = cursor.fetchone()
        if not b:
            raise Exception("Bouteille introuvable")
        
        # trouver ou créer étagère "Consommées"
        cursor.execute("SELECT id FROM etageres WHERE nom='Consommées' AND utilisateur_id=?", (b['utilisateur_id'],))
        consommee = cursor.fetchone()
        if not consommee:
            cursor.execute("INSERT INTO etageres (nom, emplacement, places_totales, places_disponibles, utilisateur_id) VALUES (?,?,?,?,?)",
                           ('Consommées', '', 1000, 1000, b['utilisateur_id']))
            etagere_id_cons = cursor.lastrowid
        else:
            etagere_id_cons = consommee['id']

        nouvelle_quantite = b['quantite'] - quantite_consomme
        if nouvelle_quantite <= 0:
            cursor.execute("UPDATE bouteilles SET statut='archivé', etagere_id=? WHERE id=?", (etagere_id_cons, b['id']))
        else:
            cursor.execute("UPDATE bouteilles SET quantite=? WHERE id=?", (nouvelle_quantite, b['id']))
            cursor.execute("""
                INSERT INTO bouteilles (nom, annee, type, domaine, quantite, statut, etagere_id, utilisateur_id, etiquette)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (b['nom'], b['annee'], b['type'], b['domaine'], quantite_consomme, 'archivé', etagere_id_cons, b['utilisateur_id'], b['etiquette']))

        # libérer la place
        if b['etagere_id']:
            cursor.execute("UPDATE etageres SET places_disponibles = places_disponibles + ? WHERE id=?", (quantite_consomme, b['etagere_id']))

        # enregistrer note ou commentaire si fourni
        if note is not None or (commentaire and commentaire.strip()):
            cursor.execute("""
                INSERT INTO notes (bouteille_nom, bouteille_type, bouteille_annee, bouteille_domaine, utilisateur_id, note, commentaire)
                VALUES (?,?,?,?,?,?,?)
            """, (b['nom'], b['type'], b['annee'], b['domaine'], b['utilisateur_id'], note, commentaire))

        self.conn.commit()

    def obtenir_historique_degustation(self, utilisateur_id):
        """
        Version finale: Récupère TOUTES les bouteilles consommées
        et y joint les notes/moyennes si elles existent,
        en gérant correctement les domaines NULL.
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                b.id, b.nom, b.annee, b.domaine, b.type, b.quantite,
                n.note as note_degustation, 
                n.commentaire as commentaire_degustation,
                
                (SELECT AVG(note) FROM notes n_avg 
                 WHERE n_avg.bouteille_nom = b.nom 
                   AND n_avg.bouteille_annee = b.annee
                   AND (n_avg.bouteille_domaine = b.domaine OR (n_avg.bouteille_domaine IS NULL AND b.domaine IS NULL))
                   AND n_avg.utilisateur_id = b.utilisateur_id) as moyenne_notes
                   
            FROM bouteilles b
            
            LEFT JOIN notes n ON b.nom = n.bouteille_nom 
                             AND b.annee = n.bouteille_annee 
                             AND b.utilisateur_id = n.utilisateur_id
                             AND (b.domaine = n.bouteille_domaine OR (b.domaine IS NULL AND n.bouteille_domaine IS NULL))

            WHERE b.utilisateur_id = ? AND b.statut = 'archivé'
            GROUP BY b.id
            ORDER BY b.id DESC
        """, (utilisateur_id,))
        
        return cursor.fetchall()


    # Ancienne fonction (non utilisée par la route /historique)
    def obtenir_bouteilles_consommees(self, utilisateur_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bouteilles WHERE utilisateur_id=? AND statut='archivé' ORDER BY id DESC", (utilisateur_id,))
        rows = cursor.fetchall()
        consomm = []
        for r in rows:
            consomm.append({
                'bouteille_nom': r['nom'],
                'bouteille_type': r['type'],
                'bouteille_annee': r['annee'],
                'bouteille_domaine': r['domaine'],
                'quantite': r['quantite'],
                'etiquette': r['etiquette'],
                'commentaire': r['commentaire'],
                'note': r['note']
            })
        return consomm

    # Notes
    def ajouter_ou_modifier_note(self, bouteille_nom, bouteille_annee, bouteille_type, bouteille_domaine,
                                 utilisateur_id, note, commentaire=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM notes
            WHERE bouteille_nom=? AND bouteille_annee=? AND bouteille_type=? AND bouteille_domaine=? AND utilisateur_id=?
        """, (bouteille_nom, bouteille_annee, bouteille_type, bouteille_domaine, utilisateur_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE notes SET note=?, commentaire=? WHERE id=?", (note, commentaire, row['id']))
        else:
            cursor.execute("""
                INSERT INTO notes (bouteille_nom, bouteille_annee, bouteille_type, bouteille_domaine,
                                  utilisateur_id, note, commentaire)
                VALUES (?,?,?,?,?,?,?)
            """, (bouteille_nom, bouteille_annee, bouteille_type, bouteille_domaine,
                  utilisateur_id, note, commentaire))
        self.conn.commit()
