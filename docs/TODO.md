# TODO — actions côté utilisateur (standlsg)

Ordre conseillé. **Règle d'or : ne jamais partager de mot de passe** (ni avec moi, ni dans le dépôt) — seuls les secrets de la **boîte mail dédiée** et des API vont en variables d'environnement Clever Cloud.

## 0. Git
- [ ] Merger la **PR #3** `preprod → prod` (bouton « Merge ») : prod manque encore 7 commits
      (hébergement/Clever Cloud, schéma + IA, tests récolte, connecteur MoteurImmo + IA-3 Mistral).
- [ ] Ensuite : itérations sur `preprod`, merge vers `prod` quand validé.

## 1. Comptes & accès à créer (jamais partagés)
- [ ] **Boîte mail dédiée** (ex. `alertes-logement@…`) + activer l'accès **IMAP** (+ mot de passe
      d'application si 2FA) → secret `CL_IMAP_PASSWORD`.
- [ ] Comptes portails (dans ton navigateur, connecté normalement) : **Leboncoin, SeLoger, PAP,
      Bien'ici, Logic-Immo, Gens de Confiance, Appartager, Studapart** — pour chacun :
      sauvegarder la recherche (zones 13xxx, budget 2 800 €, ≥ 4 pièces) et **activer l'alerte
      email** vers la boîte dédiée.
- [ ] **Resend** (resend.com, 3 000 mails/mois gratuits) : clé API → `CL_RESEND_API_KEY` ;
      domaine d'envoi vérifié (ou `*.resend.dev` pour tester) → `notify.resend.from_addr`.
- [ ] **MoteurImmo** (moteurimmo.fr/offre-api) : compte + clé API → `CL_API_KEY` ;
      ajuster `sources.api.path` / `items_path` selon leur documentation.
- [ ] **Mistral** (console.mistral.ai) : clé API → `CL_MISTRAL_API_KEY` (active `ai.provider: mistral`).

## 2. Clever Cloud
- [ ] App Docker buildée depuis la branche `prod`, région **Paris**, instance **Nano**.
- [ ] FS Bucket `chasse-logement-data` créé et **lié à l'app, mount `/app/data`**
      (vérifier `CC_FS_BUCKET=/app/data` dans les variables d'env de l'app).
- [ ] Ajouter les 4 variables d'env : `CL_IMAP_PASSWORD`, `CL_RESEND_API_KEY`, `CL_API_KEY`,
      `CL_MISTRAL_API_KEY`.
- [ ] Premier déploiement OK → ouvrir `https://<app>.cleverapps.io` (HTTPS auto).

## 3. Dans l'UI `/parametres`
- [ ] Critères : budget max 2 800 €, codes postaux 13100/13080/13090/13290/13320/13120/13007/13008/13009,
      pièces min 4 (l'IA compte un bureau détecté dans le texte), meublé selon préférence.
- [ ] Cocher les portails à surveiller (imap.portals) ; appliquer le **catalogue régional** Aix-Marseille.
- [ ] Ajouter 2-5 flux RSS d'agences locales (détectés localement avec
      `chasse-logement discover https://www.<agence>.fr`).
- [ ] Destinataires email (un par ligne) + activer **Resend** (`from_addr`).
- [ ] Trajet quotidien : `commute.destination_address` = adresse exacte du bureau
      **Salesforce Marseille** (The Babel Community, entre La Joliette et le Vieux-Port) pour un
      géocodage précis.

## 4. Premier run & vérifications
- [ ] Bouton « ▶ Lancer une tournée » → vérifier les **logs** Clever Cloud (collecte IMAP + API + RSS,
      pas d'erreur `source_errors`).
- [ ] Onglet `/biens` : biens dédupliqués, liens multi-sources, encarts IA / à vérifier / adresse / POI / trajet.
- [ ] Vérifier la réception du **digest email** (nouveaux biens uniquement) à l'adresse test.
- [ ] La tournée quotidienne tourne automatiquement (`serve`, toutes les 24 h).

## 5. Sécurité & sauvegarde
- [ ] L'URL `*.cleverapps.io` est publique : si besoin, protège l'UI (domaine perso + basic auth
      via Caddy — voir `deploy/` — ou restreins l'accès réseau).
- [ ] Backup régulier de `data/chasse-logement.db` (volume FS Bucket) — ex. job/cron de copie.
- [ ] `.env`, `config.yaml`, `data/` restent **gitignés** — jamais commités.
