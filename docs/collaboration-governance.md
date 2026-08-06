# Gouvernance des échanges et des responsabilités

Statut : **gelé**

Ce document définit le protocole de collaboration utilisé pour concevoir, implémenter, publier, auditer et valider les niveaux scientifiques du projet Cosmobox.

Il complète `docs/documentation-governance.md` :

- `documentation-governance.md` fixe où résident les informations normatives ;
- le présent document fixe qui décide, qui produit, qui publie, qui vérifie et sous quelle forme les échanges sont conduits.

Un rappel explicite à ce document suffit à réactiver l’ensemble de ces règles lors d’une nouvelle session ou après une dérive.

---

## 1. Participants et responsabilités

### 1.1 Lionel ORCIL — supervision et décision finale

Lionel est le superviseur du projet.

Il :

- fixe les priorités ;
- valide le lancement d’un lot et le passage au lot suivant ;
- arbitre les désaccords ;
- valide les changements de périmètre ;
- désigne la branche de travail autorisée ;
- autorise les PR, les fusions et les gels ;
- décide du recours exceptionnel à Claude Fable ;
- conserve la décision finale sur toute proposition scientifique ou technique.

L’autorisation d’implémenter un lot sur une branche de travail désignée inclut, sauf restriction explicite, l’autorisation de committer et de pousser le diff strictement limité à ce lot afin de permettre la revue distante.

Aucun participant ne peut présenter comme validée une décision qui n’a pas été acceptée par Lionel.

### 1.2 ChatGPT — responsabilité scientifique et conceptuelle

ChatGPT est responsable de la cohérence scientifique et conceptuelle.

Il prend en charge :

- les hypothèses physiques ;
- les définitions mathématiques ;
- les conventions et invariants ;
- le périmètre scientifique ;
- les critères d’acceptation ;
- les protocoles de validation ;
- l’analyse et l’interprétation des résultats ;
- la préparation des dossiers de conception destinés à Claude Code ;
- la revue du plan, du commit distant, du diff réel et des résultats de tests.

ChatGPT doit distinguer explicitement :

- ce qui est gelé ;
- ce qui est proposé ;
- ce qui relève d’un choix d’ingénierie ;
- ce qui est implémenté et poussé ;
- ce qui est accepté ;
- ce qui nécessite une décision de Lionel.

ChatGPT ne doit pas :

- inventer une implémentation prétendument réalisée ;
- annoncer un push sans vérification du commit et du diff réels ;
- modifier silencieusement une convention gelée ;
- imposer un détail de programmation sans justification scientifique ou contractuelle ;
- déclarer un lot validé uniquement parce que les tests passent.

### 1.3 Claude Code — responsabilité d’ingénierie et d’implémentation

Claude Code est responsable de l’ingénierie logicielle.

Il prend en charge :

- l’audit des API existantes ;
- l’architecture logicielle détaillée ;
- les structures de données et signatures d’API internes ;
- l’implémentation ;
- les tests ;
- le refactoring ;
- le profilage et les optimisations ;
- la documentation développeur ;
- la préparation du diff ;
- le commit et le push du lot sur la branche de travail autorisée ;
- le rapport de livraison accompagné du SHA distant.

Claude Code peut proposer une architecture alternative, une simplification, une amélioration de performance ou une évolution d’API tant que les contrats scientifiques restent inchangés.

Toute proposition touchant une définition scientifique, une convention, un seuil, un protocole ou un critère d’acceptation doit être remontée avant implémentation.

Claude Code ne doit pas :

- résoudre localement une ambiguïté scientifique ;
- modifier une norme pour simplifier le code ;
- élargir le périmètre d’un lot ;
- inclure dans le commit des fichiers sans rapport ;
- pousser sur une autre branche que celle désignée ;
- forcer, réécrire ou écraser l’historique distant sans autorisation ;
- ouvrir une PR ou fusionner sans autorisation ;
- exécuter une campagne scientifique non autorisée ;
- produire un verdict scientifique à partir d’un test technique seul.

### 1.4 Claude Fable — audit externe exceptionnel

Claude Fable est un relecteur externe exceptionnel.

Son intervention est réservée aux gels scientifiques importants, changements structurels de modèle, contradictions persistantes, résultats surprenants à fort enjeu ou audits explicitement demandés par Lionel.

Claude Fable n’intervient pas dans la boucle quotidienne. Son avis ne remplace pas la décision de Lionel et ne peut pas introduire silencieusement un nouveau périmètre.

---

## 2. Hiérarchie d’autorité

Pour les décisions de projet :

1. Lionel tranche ;
2. les documents normatifs gelés fixent les contrats ;
3. ChatGPT interprète et contrôle la cohérence scientifique ;
4. Claude Code choisit et publie l’implémentation compatible ;
5. Claude Fable audite exceptionnellement.

Pour les informations documentaires, la hiérarchie de `docs/documentation-governance.md` reste applicable.

Aucun message de conversation ne remplace durablement un document normatif lorsqu’une décision doit survivre à la session.

---

## 3. Cycle standard d’un lot

### Étape 1 — cadrage scientifique

ChatGPT produit ou rappelle :

- l’objectif ;
- le périmètre inclus ;
- le hors-périmètre ;
- les invariants ;
- les critères d’acceptation ;
- les documents normatifs applicables.

Lionel valide le lancement du lot et la branche de travail.

### Étape 2 — audit préalable par Claude Code

Avant de coder, Claude Code lit les documents indiqués et audite le code existant.

Il remet une proposition contenant au minimum :

- fichiers à créer ou modifier ;
- API réutilisées ;
- lacunes identifiées ;
- architecture proposée ;
- stratégie de test ;
- risques ;
- questions nécessitant une décision scientifique.

Sauf autorisation explicite, cette étape ne comporte aucune modification de code.

### Étape 3 — revue conceptuelle

ChatGPT vérifie la conformité aux normes, l’absence d’hypothèse physique ajoutée, la couverture des invariants, la pertinence des tests et le respect du périmètre.

Lionel autorise ou refuse le passage à l’implémentation.

### Étape 4 — implémentation, commit et push

Claude Code implémente uniquement le lot autorisé.

L’autorisation d’implémenter comprend par défaut le droit de :

1. modifier les seuls fichiers du périmètre ;
2. exécuter les tests prescrits ;
3. stager explicitement les chemins concernés ;
4. créer un commit logique ;
5. pousser ce commit sur la branche de travail désignée ;
6. vérifier que la tête distante correspond au SHA annoncé.

Cette autorisation implicite ne couvre jamais :

- un fichier sans rapport ;
- une modification normative non validée ;
- une autre branche ;
- un push forcé ;
- une réécriture d’historique ;
- une PR ;
- une fusion ;
- le passage au lot suivant.

Si le périmètre réel diffère du plan validé, si un fichier sans rapport est modifié ou si la branche distante a divergé de manière non triviale, Claude Code s’arrête avant commit ou push et remonte le problème.

### Étape 5 — rapport de livraison après push

Le rapport est envoyé uniquement après publication du commit distant.

Claude Code fournit :

- résumé des changements ;
- branche distante ;
- SHA du commit poussé ;
- SHA de base ;
- diff réel et liste exacte des fichiers ;
- décisions techniques ;
- tests exécutés et résultats ;
- écarts par rapport au plan ;
- limites connues ;
- état du répertoire de travail ;
- confirmation qu’aucun fichier hors périmètre n’a été poussé.

Un rapport décrivant seulement des fichiers locaux non suivis n’est pas une livraison révisable et doit être évité lorsqu’un push sur la branche de travail est autorisé.

### Étape 6 — revue du commit distant et validation

ChatGPT examine directement le commit et le diff distants, puis contrôle la conformité scientifique et conceptuelle.

Lionel valide :

- l’acceptation du lot ;
- les corrections éventuelles ;
- le passage au lot suivant ;
- l’ouverture d’une PR ou la fusion lorsque celles-ci deviennent pertinentes.

Un lot n’est pas accepté uniquement parce que le commit est poussé ou que les tests passent.

---

## 4. Format standard d’un prompt destiné à Claude Code

Chaque mission contient :

```text
Contexte
Branche de travail autorisée
Documents obligatoires
Objectif du lot
Périmètre inclus
Hors-périmètre
Invariants non négociables
Travail demandé maintenant
Livrable attendu
Critères d’acceptation
Restrictions Git particulières
```

La liste des documents commence toujours par :

```text
docs/collaboration-governance.md
docs/documentation-governance.md
```

Puis viennent les spécifications, décisions, manifestes, schémas et plans de validation applicables.

### Autorisation Git par défaut

Lorsque le travail demandé est une implémentation ou un correctif sur une branche explicitement désignée, `committer et pousser le lot avant le rapport` est la règle par défaut.

Le prompt ne doit mentionner `ne pas committer` ou `ne pas pousser` que lorsqu’une restriction particulière est réellement nécessaire, par exemple pour un audit, un prototype isolé, une branche non prête ou une investigation sans modification.

Une autorisation de push n’autorise jamais une PR, une fusion, un changement de branche, un force-push ou un élargissement de périmètre.

---

## 5. Format standard d’une réponse de Claude Code

### 5.1 Réponse d’audit ou de plan

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

### 5.2 Rapport de livraison après push

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

Les affirmations telles que « terminé », « validé », « poussé » ou « conforme » doivent être accompagnées d’éléments vérifiables.

Le mot `validé` est réservé à l’acceptation par Lionel après revue de ChatGPT. Claude Code peut dire `implémenté`, `testé` et `poussé` lorsqu’il fournit les preuves correspondantes.

---

## 6. Gestion des ambiguïtés

### 6.1 Ambiguïté scientifique

Claude Code s’arrête et remonte la question. ChatGPT propose une résolution fondée sur les normes existantes ou prépare une décision. Lionel tranche lorsque la norme ne suffit pas.

### 6.2 Ambiguïté d’ingénierie

Claude Code décide et documente son choix tant que les contrats externes restent inchangés.

### 6.3 Ambiguïté de périmètre

En cas de doute, l’élément est hors-périmètre jusqu’à autorisation explicite.

### 6.4 Contradiction documentaire

Aucune implémentation ne choisit silencieusement entre deux textes contradictoires. La contradiction est signalée et corrigée selon `docs/documentation-governance.md` lorsque son impact est normatif.

---

## 7. Gestion des dérives et régressions d’échange

Une dérive est notamment caractérisée par :

- un participant empiétant sur le rôle d’un autre ;
- une implémentation lancée avant validation du plan ;
- une décision scientifique prise dans le code ;
- un élargissement de périmètre ;
- un push hors branche ou hors périmètre ;
- une PR, une fusion ou un force-push non autorisé ;
- une affirmation non vérifiée ;
- une perte du format standard ;
- un oubli des documents applicables.

Le rappel minimal est :

```text
Reviens à `docs/collaboration-governance.md` et reprends au dernier jalon validé.
```

Après ce rappel, le participant doit identifier la règle violée, indiquer le dernier jalon réellement validé, distinguer ce qui a été fait de ce qui a seulement été annoncé et proposer la reprise la plus courte.

Si une modification erronée a déjà été publiée, elle doit être auditée avant tout nouveau travail.

---

## 8. Règles Git

### 8.1 Opérations intégrées au lot

Pour un lot d’implémentation autorisé sur une branche de travail désignée, les opérations suivantes constituent une seule chaîne de livraison :

```text
modifier → tester → stager explicitement → committer → pousser → vérifier → rapporter
```

Elles ne nécessitent pas un aller-retour d’autorisation entre chaque étape, sauf restriction explicite du prompt ou apparition d’un écart de périmètre.

### 8.2 Opérations toujours séparées

Les opérations suivantes exigent toujours une autorisation explicite :

```text
créer ou changer de branche
force-push ou réécriture d’historique
ouvrir une PR
fusionner
publier une release
modifier une norme gelée hors périmètre du lot
```

### 8.3 Vérifications avant annonce

Avant d’annoncer une livraison, Claude Code doit :

- vérifier la branche ;
- vérifier le SHA de départ ;
- inspecter le diff et les chemins stagés ;
- exclure tout fichier sans rapport ;
- vérifier l’absence de placeholder ;
- exécuter les tests prescrits ;
- pousser ;
- vérifier le SHA de la tête distante ;
- fournir le SHA final et la liste réelle des fichiers.

Un succès de commande Git ne prouve pas à lui seul que le contenu annoncé est correct. ChatGPT contrôle ensuite le diff distant réel.

---

## 9. Recours à Claude Fable

Le recours à Claude Fable est formulé comme un audit borné précisant les documents, décisions gelées, questions exactes, éléments hors-périmètre et forme du verdict attendu.

Après son retour, ChatGPT classe les remarques, Lionel décide lesquelles retenir, les correctifs sont écrits dans les documents appropriés et le diff est audité avant tout nouveau gel.

---

## 10. Jalon et mémoire de session

À la fin d’une session importante, le résumé précise :

```text
branche
commit de tête distant
lot courant
dernier jalon validé
documents applicables
travail réalisé et poussé
travail non réalisé
prochaine action autorisée
questions ouvertes
```

Le dépôt reste la mémoire durable du projet. Les conversations servent à préparer et piloter le travail, mais les décisions durables sont inscrites dans les documents normatifs ou de gouvernance.

---

## 11. Règle de démarrage d’une nouvelle session

Une nouvelle session commence par :

1. lecture de `docs/collaboration-governance.md` ;
2. identification du dernier jalon validé ;
3. vérification de la branche et du commit distant de tête ;
4. lecture des documents spécifiques au lot ;
5. formulation de la prochaine action autorisée.

Il est interdit de déduire l’état réel du dépôt à partir d’un simple souvenir de conversation lorsqu’une vérification Git est possible.

---

## 12. Formule de rappel standard

```text
Applique `docs/collaboration-governance.md` et reprends au dernier jalon validé.
```

Cette phrase impose automatiquement le retour aux rôles définis, l’arrêt des actions hors périmètre, la vérification de l’état distant réel, la distinction entre proposition, réalisation, publication et validation, puis la reprise au dernier jalon accepté.

---

## 13. Évolution de la présente charte

Toute modification de cette gouvernance exige :

1. une justification explicite ;
2. une nouvelle décision dans `docs/decisions.md` ;
3. un audit des documents qui la référencent ;
4. une vérification du diff réel ;
5. une validation de Lionel.

La charte ne peut pas être modifiée implicitement par les habitudes d’une conversation.