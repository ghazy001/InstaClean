
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

> Vous pouvez récupérer ces cookies en vous connectant à Instagram via Safari, puis en allant dans "Développement > Afficher l’inspecteur Web > Storage > Cookies".

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


