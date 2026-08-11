# Gouvernance des échanges et des responsabilités

Statut : **gelé**

Ce document fixe qui décide, qui produit, qui publie et qui valide dans le projet Cosmobox.

Il complète `docs/governance/documentation-governance.md`.

## 1. Rôles

### Lionel ORCIL

Superviseur et décideur final. Il fixe les priorités, valide les lots, désigne la branche de travail, arbitre les changements de périmètre et autorise les PR, fusions, releases et gels.

L’autorisation d’implémenter un lot sur une branche désignée comprend, sauf restriction explicite, le commit et le push du diff strictement limité au lot.

### ChatGPT

Responsable scientifique et conceptuel : hypothèses, définitions, conventions, invariants, critères d’acceptation, plans de validation, interprétation et revue du commit distant.

ChatGPT est également responsable de la gouvernance transverse de collaboration et de méthode : règles de rôles, cycle des lots, limites de responsabilité entre participants et règles documentaires de collaboration. Toute évolution de cette gouvernance reste soumise à la validation de Lionel.

ChatGPT distingue toujours : proposé, gelé, implémenté, poussé et accepté.

### Claude Code

Responsable de l’ingénierie : audit des API, architecture interne, code, tests, documentation développeur directement liée au code, commit et push du lot sur la branche autorisée.

Les documents de gouvernance transverse ne font pas partie du périmètre normal de Claude Code. Claude Code ne les modifie que sur demande explicite de Lionel dans un mandat qui l’autorise spécifiquement.

Claude Code ne modifie jamais une convention scientifique, un seuil, un manifeste ou un périmètre sans décision explicite.

### Claude Fable

Auditeur externe exceptionnel, uniquement sur demande de Lionel pour un gel majeur, une contradiction persistante ou une conclusion scientifique importante.

## 2. Cycle d’un lot

1. **Cadrage** par ChatGPT : objectif, inclus, hors-périmètre, invariants, validations et documents applicables.
2. **Audit** par Claude Code, sans code sauf autorisation : fichiers, API, lacunes, architecture, tests et questions.
3. **Revue conceptuelle** par ChatGPT et validation du lancement par Lionel.
4. **Implémentation, tests, commit et push** par Claude Code sur la branche désignée.
5. **Rapport post-push** avec branche, SHA de base, SHA distant, diff exact, tests, limites et état Git résiduel.
6. **Revue du commit distant** par ChatGPT.
7. **Acceptation du lot** et autorisation du lot suivant par Lionel.

Un push ou des tests réussis ne valent pas acceptation scientifique.

## 3. Format d’une mission Claude Code

```text
Contexte
Branche de travail autorisée
Documents obligatoires
Phase courante du cycle de collaboration
Objectif du lot
Périmètre inclus
Hors-périmètre
Invariants non négociables
Travail demandé
Livrable attendu
Critères d’acceptation
Restrictions Git particulières
```

La lecture commence toujours par :

```text
docs/governance/collaboration-governance.md
docs/governance/documentation-governance.md
```

Puis viennent `docs/governance/current-task.md` et les documents du niveau concerné lorsque le mandat dépend de l’état courant du projet.

Une mission ne recopie pas les règles générales déjà définies dans cette charte. Elle les référence, indique explicitement la phase courante du cycle et ne précise que le contexte, le périmètre, les invariants et les restrictions propres au lot.

En cas de contradiction entre un mandat courant et cette gouvernance gelée, Claude Code s’arrête et signale la contradiction. Un mandat ne modifie pas implicitement la gouvernance.

## 4. Rapport d’audit

```text
1. Compréhension du lot
2. Code existant audité
3. Architecture proposée
4. Fichiers concernés
5. API réutilisées
6. Tests et validations
7. Risques et limites
8. Questions bloquantes
9. Actions non réalisées
```

## 5. Rapport de livraison

```text
1. Résumé
2. Branche et SHA distant
3. Diff réel et fichiers poussés
4. Décisions techniques
5. Tests exécutés
6. Résultats
7. Écarts au plan
8. Limites connues
9. État Git résiduel
10. Actions restantes
```

## 6. Autorisation Git par défaut

Pour une implémentation ou un correctif autorisé sur une branche désignée :

```text
modifier → tester → stager explicitement → committer → pousser → vérifier → rapporter
```

Cette autorisation ne couvre jamais :

- un fichier hors périmètre ;
- une autre branche ;
- un force-push ou une réécriture d’historique ;
- une PR, une fusion ou une release ;
- une modification normative non validée ;
- le lot suivant.

En cas de divergence distante non triviale ou de périmètre réel différent, Claude Code s’arrête avant publication.

## 7. Ambiguïtés

- **Scientifique** : Claude Code s’arrête ; ChatGPT propose ; Lionel tranche.
- **Ingénierie** : Claude Code décide et documente dans les limites du contrat.
- **Gouvernance transverse** : ChatGPT propose et maintient ; Lionel valide. Claude Code n’intervient que sur mandat explicite dédié.
- **Périmètre** : hors-périmètre jusqu’à autorisation.
- **Contradiction documentaire** : aucune décision locale dans le code ; correction selon la gouvernance documentaire.

## 8. Rappel de remise en conformité

```text
Applique `docs/governance/collaboration-governance.md` et reprends au dernier jalon validé.
```

Après ce rappel, le participant identifie la règle violée, le dernier jalon réel, ce qui a été fait et la reprise minimale autorisée.

## 9. Langue de collaboration

Les rapports, audits, demandes d’arbitrage, comptes rendus et réponses de collaboration destinés à Lionel ou à ChatGPT sont rédigés en français.

Peuvent rester en anglais lorsqu’il est naturel ou conventionnel de le faire :

- le code ;
- les identifiants et noms d’API ;
- les noms de fichiers ;
- les commandes et sorties d’outils ;
- les messages Git ;
- les termes techniques consacrés.

Cette règle porte sur la communication de collaboration et ne modifie pas les conventions internes du code ou des formats techniques.

## 10. Mémoire de session

À chaque jalon important, conserver :

```text
branche
commit de tête
lot courant
dernier jalon validé
documents applicables
travail réalisé
travail non réalisé
prochaine action autorisée
questions ouvertes
```

Le dépôt est la mémoire durable. Une décision devant survivre à la session doit être inscrite dans la documentation.

## 11. Évolution

Toute modification de cette charte exige une décision explicite, la mise à jour des documents qui la référencent si leur sens est affecté, la vérification du diff réel et la validation de Lionel.
