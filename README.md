
# 📱 Instagram Unfollowers GUI App (macOS)

Une application de bureau avec interface graphique pour **voir qui ne vous suit pas en retour sur Instagram** et les **unfollow facilement**, avec un style moderne type Instagram en mode sombre.

---

## ✨ Fonctionnalités

- 🔍 Analyse des comptes qui ne vous suivent pas en retour
- ✅ Sélection multiple pour unfollow
- 🎨 Interface graphique sombre façon Instagram
- 🔎 Barre de recherche intégrée
- 📄 Résultats paginés (10 par page)
- 🚫 Bouton "Unfollow Selected"
- 💻 Application 100 % locale (aucune donnée n'est envoyée ailleurs)

---

## 🛠️ Prérequis

- macOS (Catalina ou supérieur recommandé)
- Python 3.9+
- Connexion à Instagram avec votre propre navigateur pour obtenir les cookies

---

## ⚙️ Installation

1. **Téléchargez ou clonez le projet :**

```bash
git clone https://github.com/ton-nom/instagram-unfollowers-gui.git
cd instagram-unfollowers-gui
````

2. **Installez les dépendances Python :**

```bash
pip install -r requirements.txt
```

3. **Configurez vos cookies Instagram :**

Dans `app.py`, remplacez les valeurs par vos cookies personnels :

```python
CSRFTOKEN = "votre_csrftoken"
SESSIONID = "votre_sessionid"
DS_USER_ID = "votre_user_id"
```

> Pour que l’application fonctionne, vous devez récupérer vos cookies Instagram (`csrftoken`, `sessionid`, `ds_user_id`) depuis votre navigateur. Voici comment faire depuis Safari :

### Étapes pour récupérer les cookies dans Safari :

1. Ouvrez Safari et connectez-vous à votre compte Instagram.
2. Dans la barre de menu, cliquez sur **Développement** > **Afficher l’inspecteur Web**  
   (ou utilisez le raccourci clavier `⌘ + ⌥ + I`)
3. Dans l’inspecteur, allez à l’onglet **Application** (ou Storage).
4. Dans la colonne de gauche, cliquez sur **Cookies**, puis sélectionnez le domaine **.instagram.com**.
5. Trouvez et copiez la valeur des cookies suivants :  
   - `csrftoken`  
   - `sessionid`  
   - `ds_user_id`
6. Collez ces valeurs dans le fichier `app.py` à la section **Configuration** :

```python
CSRFTOKEN = "votre_csrftoken_ici"
SESSIONID = "votre_sessionid_ici"
DS_USER_ID = "votre_ds_user_id_ici"



4. **Lancez l’application :**

```bash
python app.py
```

---

## 🧪 Utilisation

1. Cliquez sur **🔍 Scan Now** pour charger les comptes qui ne vous suivent pas en retour.
2. Utilisez la **barre de recherche** pour filtrer les utilisateurs.
3. Cochez les cases à côté des utilisateurs que vous souhaitez unfollow.
4. Cliquez sur **🚫 Unfollow Selected** pour les supprimer de votre liste de suivis.

---

## 📦 Générer un `.app` exécutable (facultatif)

Pour créer une application `.app` utilisable comme un vrai programme macOS :

```bash
pip install py2app
python setup.py py2app
```

Le fichier sera généré dans le dossier `dist/`.

---

## 📌 Conseils

* ⚠️ **N’abusez pas des unfollows** : Instagram peut vous bloquer temporairement.
* 🧠 L’application utilise l’API Web non officielle d’Instagram via vos propres cookies, elle n’est pas approuvée par Meta.
* 🔒 **Vos données ne quittent jamais votre machine.**

---

## 👤 Auteur
                                    
Développée avec ❤️ par Ghazi Saoudi et ChatGPT

---

## 📜 Licence

Libre pour usage personnel. Toute reproduction commerciale nécessite l’accord de l’auteur.


