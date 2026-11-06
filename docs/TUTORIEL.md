# 🎓 Tutoriel pas à pas — mettre chasse-logement en ligne (Clever Cloud)

Pour débutant : chaque étape dit **où cliquer**, **quoi copier**, et **ce qu'on doit voir à la fin**.
Temps estimé : 45-60 min. Prérequis : ton compte GitHub, un compte Clever Cloud (à créer), une adresse mail neuve.

> 🔒 **Règle d'or** : on ne partage jamais de mot de passe (ni avec moi, ni sur GitHub).
> Seuls des « mots de passe d'application » / clés API vont dans les **variables d'environnement Clever Cloud**.

---

## Étape 0 — Mettre le code à jour sur `prod`

L'application vit sur la branche `preprod` (travail) et `prod` (ce qui tourne en ligne).

1. Va sur [github.com/standlsg/chasse-logement/pulls](https://github.com/standlsg/chasse-logement/pulls)
2. Ouvre la PR **#3** (`preprod → prod`)
3. Clique **« Merge pull request »** → **« Confirm merge »**
4. ✅ Résultat attendu : la PR passe en violet « Merged », et la branche `prod` contient tout le code.

*Pourquoi : Clever Cloud déploiera la branche `prod`.*

---

## Étape 1 — Créer la boîte mail dédiée (celle qui recevra les alertes des portails)

L'appli ne se connecte à aucun portail avec tes identifiants : elle lit **uniquement les e-mails
d'alerte** reçus dans cette boîte dédiée.

1. Crée une adresse neuve, ex. `alertes-logement@gmail.com` (ou chez ton fournisseur mail habituel).
2. Active l'**IMAP** :
   - Gmail : Paramètres (⚙️) → « Voir tous les paramètres » → onglet **« Transfert et POP/IMAP »** → « Activer IMAP » → Enregistrer.
3. Si tu as la double authentification (2FA) — recommandé : crée un **mot de passe d'application** :
   - Compte Google → **Sécurité** → **Mots de passe d'applications** → choisis « Autre » → nomme `chasse-logement` → **Copier** le mot de passe affiché (16 caractères).
   - Sans 2FA : c'est ton mot de passe mail habituel qui servira (moins sûr).
4. ✅ À garder pour plus tard : l'adresse de la boîte + le mot de passe d'application → ira dans la variable `CL_IMAP_PASSWORD` (étape 6).

---

## Étape 2 — Activer les alertes e-mail sur chaque portail (depuis ton navigateur, connecté normalement)

Pour **chaaque** portail de cette liste : **Leboncoin, SeLoger, PAP, Bien'ici, Logic-Immo, Gens de Confiance, Appartager, Studapart**

1. Connecte-toi sur le portail.
2. Fais ta recherche avec les filtres : zone (Aix-en-Provence, Marseille 7e/8e/9e, Luynes, Les Milles, Bouc-Bel-Air, Gardanne), **prix max 2 800 €**, **4 pièces et +** (ou 3 pièces, l'IA détectera le bureau dans le texte).
3. Clique sur **« Sauvegarder la recherche »** / **« Créer une alerte »**.
4. Dans les options de l'alerte, choisis **« Notification par e-mail »** et indique l'adresse de la boîte dédiée (étape 1).
5. ✅ Résultat attendu : tu recevras un e-mail de confirmation ; à chaque nouvelle annonce correspondante, un e-mail arrivera dans la boîte dédiée.

*Astuce : fais une recherche par grande zone (ex. « Aix-en-Provence 13100 », « Marseille 13008 ») plutôt qu'une seule recherche France entière.*

---

## Étape 3 — Resend (pour envoyer les e-mails de résultats)

1. [resend.com](https://resend.com) → **Sign up** (gratuit : 3 000 e-mails/mois).
2. Menu **API Keys** → **Create API Key** → nom `chasse-logement` → **copie la clé** (elle ne sera plus affichée).
3. Menu **Domains** :
   - Pour **tester tout de suite** : tu peux envoyer depuis `onboarding@resend.dev` mais **uniquement vers ton adresse** de création du compte.
   - Pour envoyer à d'autres adresses (famille, etc.) : **Add Domain** → entre ton domaine (ex. `chezmoi.fr`) → copie les enregistrements DNS proposés chez ton registrar (OVH, Gandi…) → attends la validation (vert « Valid »).
4. ✅ À garder : la clé API → variable `CL_RESEND_API_KEY` (étape 6).

---

## Étape 4 — MoteurImmo (API d'annonces agrégées, payante à l'usage)

1. [moteurimmo.fr/offre-api](https://moteurimmo.fr/offre-api) → crée un compte développeur.
2. Dans ton espace, récupère ta **clé API** (et la doc exacte des endpoints/paramètres).
3. ✅ À garder : la clé → variable `CL_API_KEY` (étape 6).
4. Si leur doc indique un chemin différent de `/api/v1/annonces`, on l'ajustera dans la config (`sources.api.path` / `items_path`).

---

## Étape 5 — Mistral (l'IA qui lit les annonces)

1. [console.mistral.ai](https://console.mistral.ai) → Sign up → **API keys** → **Create new key** → copie-la.
2. ✅ À garder : la clé → variable `CL_MISTRAL_API_KEY` (étape 6).
3. Coût : modèle `mistral-small-latest` ≈ 0,20 €/million de tokens → quelques centimes par tournée.

---

## Étape 6 — Clever Cloud : créer l'application et brancher le stockage persistant

1. [console.clever-cloud.com](https://console.clever-cloud.com) → crée un compte (une **carte bancaire est demandée** pour les add-ons payants, mais une instance Nano + un petit bucket coûtent ~5-10 €/mois au total ; rien n'est prélevé sans action).
2. **Add an app** → **From a GitHub repository** → choisis `standlsg/chasse-logement` → branche **`prod`** → Clever Cloud détecte le `Dockerfile` (runtime Docker) → région **Paris (FR)** → nomme l'app `chasse-logement` → **Create**.
3. Taille d'instance : **Nano** (512 Mo) suffit largement.
4. **Stockage persistant** (sinon la base de données serait perdue à chaque redéploiement) :
   - Onglet **Add-ons** → **FS Bucket** → **Create a new FS bucket** → nom : `chasse-logement-data` → région **Paris (`infra:clever-cloud`)** → Create.
   - Puis **Link this add-on** à l'app `chasse-logement`, **mount path : `/app/data`** → Link.
5. Vérifie : dans l'app → **Environment variables**, tu dois voir `CC_FS_BUCKET=/app/data`.
6. Toujours dans **Environment variables** de l'app, ajoute les 4 secrets (bouton « Add » pour chacune, type «secret" recommandé) :
   - `CL_IMAP_PASSWORD` = mot de passe d'application de la boîte dédiée (étape 1)
   - `CL_RESEND_API_KEY` = clé Resend (étape 3)
   - `CL_API_KEY` = clé MoteurImmo (étape 4)
   - `CL_MISTRAL_API_KEY` = clé Mistral (étape 5)
7. ✅ Laisse le premier déploiement se faire (onglet **Activity** / logs jusqu'à « Application started »).
   L'URL de l'app est affichée en haut de la page Overview : `https://<app>.cleverapps.io`

---

## Étape 7 — Ouvrir l'interface et régler les paramètres

1. Ouvre `https://<app>.cleverapps.io` → tu vois le **tableau de bord**.
2. Va dans **Paramètres** (`/parametres`) :
   - **Critères** : budget max `2800`, codes postaux `13100 13080 13090 13290 13320 13120 13007 13008 13009`, pièces min `4` (l'IA ajoute +1 si elle détecte un bureau dans le texte), meublé selon ta préférence, score min 50.
   - Clique sur **« 📦 Appliquer le catalogue »** (région aix-marseille) pour cocher les portails recommandés.
   - Coche les portails dans la liste.
   - **Flux RSS d'agences** (optionnel) : ajoute 2-5 agences locales du 13.
   - **Destinataires e-mail** : ton adresse (et éventuellement d'autres), un par ligne.
   - Mode **Digest** (1 e-mail par tournée avec uniquement les nouveaux biens).
   - Clique **« 💾 Enregistrer les paramètres »**.
   - ✅ Ces réglages sont sauvegardés dans `/app/data/config.yaml` (sur le FS Bucket) → ils **persistent** même après un redéploiement.
3. La notification par e-mail se fait via **Resend** : vérifie dans la config embarquée que
   `notify.resend.enabled: true` et mets ton `from_addr` (domaine vérifié à l'étape 3).

---

## Étape 8 — Première tournée et vérifications

1. Retourne sur le **tableau de bord** (`/`), clique **« ▶ Lancer une tournée »**.
2. Regarde les **logs** Clever Cloud (onglet Logs) : tu dois voir la collecte IMAP + API + RSS
   et un résumé JSON (`collected`, `new`, `properties`, `matches`, `notified`).
3. Va dans l'onglet **Biens** (`/biens`) : chaque bien apparaît **une seule fois**, triable/filtrable,
   avec liens vers chaque source, encart « à vérifier », signaux IA, adresse estimée, écoles/commerces,
   et trajet hors trafic vers la destination.
4. ✅ Vérifie dans ta boîte mail perso : le **digest** « [chasse-logement] N nouveau(x) bien(s) »
   (pense au dossier spam au début).
5. À partir de là, la tournée tourne **toute seule toutes les 24 h** (pas besoin de laisser l'onglet ouvert).

---

## Étape 9 — Le trajet vers Salesforce Marseille

L'adresse exacte du bureau (The Babel Community, entre La Joliette et le Vieux-Port) est dans la
config (`commute.destination_address`). Pour la rendre précise : cherche l'adresse postale exacte
(ex. sur Google Maps / PagesJaunes), puis on la renseigne — dis-moi l'adresse et je la mets dans la
config, ou on l'ajoute dans l'UI à la prochaine itération.

---

## Étape 10 — Sécurité et sauvegarde

- [ ] L'URL `*.cleverapps.io` est **publique** : pour protéger l'UI (tes critères sont dedans),
      on peut ajouter un domaine perso + **basic auth** (voir `deploy/README.md`) — ou simplement
      ne rien y mettre de sensible. Je recommande la protection.
- [ ] **Backup** de la base : `data/chasse-logement.db` vit sur le FS Bucket (persistant).
      On peut ajouter une copie périodique externe en V2.
- [ ] `.env`, `config.yaml`, `data/` sont gitignés : **ne jamais les committer** (vérifié : ils le sont).

---

## 🆘 Dépannage (les 5 pannes classiques)

| Symptôme | Cause probable | Fix |
|---|---|---|
| Build Clever Cloud en échec | branche `prod` pas à jour | Étape 0 (merger la PR #3) puis « Redeploy » |
| App démarre puis erreur dans les logs | variable d'env manquante | Vérifier les 4 `CL_*` dans Environment variables |
| 0 annonce collectée (IMAP) | IMAP désactivé ou mauvais mot de passe | Étape 1 : IMAP activé + mot de passe d'application |
| 0 annonce (portails) | alerte e-mail pas activée sur le portail | Étape 2 : vérifier « Mes recherches » → notif e-mail ON |
| Pas d'e-mail de résultats | `from_addr` non vérifié sur Resend, ou spam | Étape 3 : domaine « Valid », ou test avec `onboarding@resend.dev` vers ton adresse |
| L'UI affiche une erreur 500 | bug | Copie le message d'erreur des logs Clever Cloud et dis-le moi |

---

## 📌 Récap des secrets (où ils vont)

| Secret | Valeur | Où la mettre |
|---|---|---|
| `CL_IMAP_PASSWORD` | mot de passe d'application de la boîte dédiée | Clever Cloud → app → Environment variables |
| `CL_RESEND_API_KEY` | clé API Resend | idem |
| `CL_API_KEY` | clé API MoteurImmo | idem |
| `CL_MISTRAL_API_KEY` | clé API Mistral | idem |

Jamais dans GitHub, jamais dans le chat, jamais dans un fichier commité.
