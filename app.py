import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from CaveAvin import * # Importe la classe Cave_a_vin
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecret"

# Dossier pour les étiquettes
UPLOAD_FOLDER = os.path.join('static', 'etiquettes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Instance unique de la classe métier ---
try:
    cave = Cave_a_vin()
    print("Instance Cave_a_vin créée et DB initialisée.")
except Exception as e:
    print(f"Erreur critique lors de l'instanciation de Cave_a_vin: {e}")
    cave = None

# --- Connexion DB (uniquement pour login/register) ---
def get_db_connection():
    conn = sqlite3.connect("cave_a_vin.db")
    conn.row_factory = sqlite3.Row  # pour accéder aux colonnes par nom
    return conn

# ------------------- UTILISATEURS -------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO utilisateurs (nom, email, mot_de_passe) VALUES (?, ?, ?)",
                         (nom, email, mot_de_passe))
            conn.commit()
            flash("Compte créé avec succès !", "success")
            return redirect(url_for('login'))
        except:
            flash("Erreur : l'email existe déjà.", "danger")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM utilisateurs WHERE email = ? AND mot_de_passe = ?",
                            (email, mot_de_passe)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_nom'] = user['nom']
            return redirect(url_for('home'))
        else:
            flash("Email ou mot de passe incorrect.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté avec succès.", "info")
    return redirect(url_for('login'))

# ------------------- ETAGERES -------------------

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not cave:
         flash("Erreur critique du système de cave.", "danger")
         return render_template('home.html', etageres=[])

    try:
        etageres = cave.lister_etageres(session['user_id'])
        return render_template('home.html', etageres=etageres)
    except Exception as e:
        flash(f"Erreur lors de la récupération de vos étagères: {e}", "danger")
        return render_template('home.html', etageres=[])

@app.route('/ajouter_etagere', methods=['GET', 'POST'])
def ajouter_etagere():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nom = request.form['nom']
        emplacement = request.form.get('emplacement', '')
        places_totales = request.form['places_totales']

        try:
            cave.ajouter_etagere(
                nom=nom,
                emplacement=emplacement,
                places_totales=places_totales,
                utilisateur_id=session['user_id']
            )
            flash("Étagère ajoutée !", "success")
        except Exception as e:
            flash(f"Erreur lors de l'ajout de l'étagère: {e}", "danger")
        
        return redirect(url_for('home'))

    return render_template('ajouter_etagere.html')

@app.route('/modifier_etagere/<int:etagere_id>', methods=['GET', 'POST'])
def modifier_etagere(etagere_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nom = request.form['nom']
        emplacement = request.form.get('emplacement', '')
        places_totales = request.form['places_totales']

        try:
            cave.modifier_etagere(
                etagere_id=etagere_id,
                nom=nom,
                emplacement=emplacement,
                places_totales=places_totales,
                utilisateur_id=session['user_id']
            )
            flash("Étagère modifiée !", "success")
            return redirect(url_for('home'))
        except Exception as e:
            flash(f"Erreur lors de la modification: {e}", "danger")
            return redirect(url_for('home'))

    etagere = cave.obtenir_etagere(etagere_id, session['user_id'])
    if not etagere:
        flash("Étagère non trouvée.", "danger")
        return redirect(url_for('home'))
        
    return render_template('modifier_etagere.html', etagere=etagere)

@app.route('/supprimer_etagere/<int:etagere_id>', methods=['POST'])
def supprimer_etagere(etagere_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        cave.supprimer_etagere(etagere_id, session['user_id'])
        flash("Étagère supprimée.", "info")
    except Exception as e:
        flash(f"{e}", "danger")
    
    return redirect(url_for('home'))

# ------------------- BOUTEILLES -------------------

@app.route('/ajouter_bouteille', methods=['GET', 'POST'])
def ajouter_bouteille():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    etageres = cave.lister_etageres(session['user_id'])

    if request.method == 'POST':
        nom = request.form['nom']
        domaine = request.form.get('domaine', '')
        annee = request.form['annee']
        type_vin = request.form.get('type', '')
        quantite = request.form.get('quantite', 1)
        note = request.form.get('note', None)
        commentaire = request.form.get('commentaire', '')
        statut = request.form.get('statut', 'en stock')
        etagere_id = request.form['etagere_id']
        etiquette = None

        if 'etiquette' in request.files:
            file = request.files['etiquette']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                etiquette = filename
        
        try:
            cave.ajouter_bouteille(
                nom=nom,
                annee=annee,
                type_vin=type_vin,
                domaine=domaine,
                quantite=int(quantite),
                note=note if note else None,
                commentaire=commentaire,
                statut=statut,
                etagere_id=etagere_id if etagere_id else None,
                utilisateur_id=session['user_id'],
                etiquette=etiquette
            )
            flash("Bouteille ajoutée avec succès !", "success")
            return redirect(url_for('home'))
        except Exception as e:
            flash(f"Erreur lors de l'ajout de la bouteille: {e}", "danger")
            return redirect(url_for('home'))

    return render_template('ajouter_bouteille.html', etageres=etageres, bouteille=None)

@app.route('/modifier_bouteille/<int:bouteille_id>', methods=['GET', 'POST'])
def modifier_bouteille(bouteille_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    bouteille = cave.obtenir_bouteille(bouteille_id, session['user_id'])
    if not bouteille:
        flash("Bouteille non trouvée ou non autorisée.", "danger")
        return redirect(url_for('home'))

    etageres = cave.lister_etageres(session['user_id'])

    if request.method == 'POST':
        nom = request.form['nom']
        domaine = request.form['domaine']
        annee = request.form['annee']
        type_vin = request.form['type']
        quantite = request.form['quantite']
        note = request.form.get('note', None)
        commentaire = request.form['commentaire']
        etagere_id = request.form['etagere_id']
        statut = request.form.get('statut', bouteille['statut']) 

        etiquette = bouteille['etiquette']
        if 'etiquette' in request.files:
            file = request.files['etiquette']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                etiquette = filename
        
        try:
            cave.modifier_bouteille(
                bouteille_id=bouteille_id,
                nom=nom,
                annee=annee,
                type_vin=type_vin,
                domaine=domaine,
                quantite=quantite,
                note=note if note else None,
                commentaire=commentaire,
                statut=statut,
                etagere_id=etagere_id,
                utilisateur_id=session['user_id'],
                etiquette=etiquette
            )
            flash("Bouteille modifiée avec succès !", "success")
            return redirect(url_for('home'))
        except Exception as e:
            flash(f"Erreur lors de la modification: {e}", "danger")
            return redirect(url_for('home'))

    return render_template('modifier_bouteille.html', bouteille=bouteille, etageres=etageres)

@app.route('/supprimer_bouteille/<int:bouteille_id>', methods=['POST'])
def supprimer_bouteille(bouteille_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    bouteille = cave.obtenir_bouteille(bouteille_id, session['user_id'])
    
    if bouteille and bouteille['etiquette']:
        etiquette_path = os.path.join(app.config['UPLOAD_FOLDER'], bouteille['etiquette'])
        if os.path.exists(etiquette_path):
            try:
                os.remove(etiquette_path)
            except Exception as e:
                print(f"Erreur suppression image: {e}")

    try:
        cave.marquer_bouteille_supprimee(bouteille_id, session['user_id'])
        flash("Bouteille supprimée.", "info")
    except Exception as e:
        flash(f"Erreur suppression bouteille: {e}", "danger")
    
    return redirect(url_for('home'))

@app.route('/consommer_bouteille/<int:bouteille_id>', methods=['POST'])
def consommer_bouteille(bouteille_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        quantite_consomme = int(request.form['quantite_consomme'])
        
        note_str = request.form.get('note') 
        commentaire = request.form.get('commentaire', '') 

        try:
            note = float(note_str)
        except (ValueError, TypeError):
            note = None 

        bouteille = cave.obtenir_bouteille(bouteille_id, session['user_id'])
        
        if not bouteille:
            flash("Bouteille non trouvée.", "danger")
            return redirect(url_for('home'))

        if quantite_consomme > bouteille['quantite']:
            flash("Vous ne pouvez pas consommer plus de bouteilles que vous n'en avez !", "danger")
            return redirect(url_for('home'))

        cave.consommer_bouteille(
            bouteille_id=bouteille_id,
            quantite_consomme=quantite_consomme,
            note=note,
            commentaire=commentaire
        )
        
        flash("Bouteille consommée ! Santé !", "success")
    
    except Exception as e:
        print(f"[ERREUR app.py] Erreur lors de la consommation : {e}")
        flash(f"Erreur lors de la consommation : {e}", "danger")

    return redirect(url_for('home'))

@app.route('/historique')
def historique():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    notes_historique = cave.obtenir_historique_degustation(session['user_id'])
    
    return render_template('historique.html', notes=notes_historique)

# ------------------- LANCEMENT -------------------

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
