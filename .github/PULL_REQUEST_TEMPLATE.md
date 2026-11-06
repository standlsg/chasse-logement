## Summary
- Qu'est-ce qui change et pourquoi ?

## Conformité (obligatoire pour toute nouvelle source)
- [ ] robots.txt vérifié (`chasse-logement check-robots <url>`) ou flux/API public documenté
- [ ] CGU de la source ne interdisent pas l'extraction automatisée
- [ ] Aucun contournement de CAPTCHA / authentification / blocage IP
- [ ] Pas de données personnelles d'annonceurs stockées (RGPD : minimisation)
- [ ] Source ajoutée au registre `docs/sources.md`

## Verification
- [ ] `pytest -q`
- [ ] `ruff check .` et `ruff format --check .`
