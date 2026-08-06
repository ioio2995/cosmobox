# D017 — Arborescence documentaire fonctionnelle

**Statut : gelé**

La documentation Cosmobox est désormais classée par fonction, puis par niveau scientifique lorsque le contenu est propre à un niveau.

Les chemins canoniques deviennent :

```text
docs/governance/documentation-governance.md
docs/governance/collaboration-governance.md
docs/model/physical-model.md
docs/decisions/decisions.md
docs/levels/level0/specification.md
docs/levels/level0/validation-plan.md
docs/levels/level1/specification.md
docs/levels/level1/validation-plan.md
docs/levels/level1/implementation-design.md
experiments/level1/preregistered-manifest.md
schemas/level1/correlators-v1.schema.json
```

`docs/README.md` devient l’index documentaire principal.

Les anciens chemins sont supersédés. Ils peuvent être conservés temporairement comme fichiers de redirection sans contenu normatif afin de maintenir la compatibilité avec les références historiques et les outils existants.

Tout nouveau document, prompt, commentaire de code ou renvoi doit utiliser les chemins fonctionnels.

La migration ne modifie aucune définition scientifique, valeur de campagne, convention d’opérateur, seuil, fenêtre spectrale ou schéma de données.

Le jalon documentaire est réalisé après acceptation du lot 1B-1, au commit scientifique `9a352b2e17fe989397996117b1b089174547db07`.
