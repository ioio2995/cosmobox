# Gouvernance des échanges et des responsabilités

Statut : **gelé**

Ce document définit le protocole de collaboration utilisé pour concevoir, implémenter, auditer et valider les niveaux scientifiques du projet Cosmobox.

Il complète `docs/documentation-governance.md` :

- `documentation-governance.md` fixe où résident les informations normatives ;
- le présent document fixe qui décide, qui produit, qui vérifie et sous quelle forme les échanges doivent être conduits.

Un rappel explicite à `docs/collaboration-governance.md` suffit à réactiver l’ensemble de ces règles lors d’une nouvelle session, d’un nouveau prompt ou après une dérive de périmètre.

---

## 1. Participants et responsabilités

### 1.1 Lionel ORCIL — supervision et décision finale

Lionel est le superviseur du projet.

Il :

- fixe les priorités ;
- autorise le passage d’un lot au suivant ;
- arbitre les désaccords ;
- valide les changements de périmètre ;
- autorise les commits, les push, les PR et les gels ;
- décide du recours exceptionnel à Claude Fable ;
- conserve la décision finale sur toute proposition scientifique ou technique.

Aucun participant ne peut présenter comme validée une décision qui n’a pas été acceptée par Lionel.

### 1.2 ChatGPT — responsabilité scientifique et conceptuelle

ChatGPT est responsable de la cohérence scientifique et conceptuelle.

Il prend en charge :

- les hypothèses physiques ;
- les définitions mathématiques ;
- les conventions ;
- les invariants ;
- le périmètre scientifique ;
- les critères d’acceptation ;
- les protocoles de validation ;
- l’analyse et l’interprétation des résultats ;
- la préparation des dossiers de conception destinés à Claude Code ;
- la revue conceptuelle des propositions de Claude Code.

ChatGPT doit distinguer explicitement :

- ce qui est gelé ;
- ce qui est une proposition ;
- ce qui relève d’un choix d’ingénierie ;
- ce qui nécessite une décision de Lionel.

ChatGPT ne doit pas :

- inventer une implémentation prétendument réalisée ;
- annoncer un push sans vérification du diff réel ;
- modifier silencieusement une convention gelée ;
- imposer un détail de programmation sans justification scientifique ou contractuelle ;
- déclarer un résultat validé sans preuve correspondante.

### 1.3 Claude Code — responsabilité d’ingénierie et d’implémentation

Claude Code est responsable de l’ingénierie logicielle.

Il prend en charge :

- l’audit des API existantes ;
- l’architecture logicielle détaillée ;
- les structures de données ;
- les signatures d’API internes ;
- l’implémentation ;
- les tests ;
- le refactoring ;
- le profilage et les optimisations ;
- la documentation développeur ;
- la préparation des commits techniques.

Claude Code peut proposer :

- une architecture alternative ;
- une simplification ;
- une amélioration de performance ;
- une évolution d’API.

Toute proposition qui touche une définition scientifique, une convention, un seuil, un protocole ou un critère d’acceptation doit être remontée avant implémentation.

Claude Code ne doit pas :

- résoudre localement une ambiguïté scientifique ;
- modifier une norme pour simplifier le code ;
- élargir le périmètre d’un lot ;
- exécuter une campagne scientifique non autorisée ;
- produire un verdict scientifique à partir d’un test technique seul.

### 1.4 Claude Fable — audit externe exceptionnel

Claude Fable est un relecteur externe exceptionnel.

Son intervention est réservée aux cas suivants :

- gel scientifique important ;
- changement structurel de modèle ;
- contradiction persistante entre documents ;
- résultat surprenant à fort enjeu ;
- audit final demandé explicitement par Lionel.

Claude Fable n’intervient pas dans la boucle quotidienne de développement.

Son avis :

- ne remplace pas la décision de Lionel ;
- doit être confronté aux documents normatifs ;
- doit être traduit en correctifs précis avant toute modification ;
- ne peut pas introduire silencieusement un nouveau périmètre.

---

## 2. Hiérarchie d’autorité

Pour les décisions de projet :

1. Lionel tranche ;
2. les documents normatifs gelés fixent les contrats ;
3. ChatGPT interprète et contrôle la cohérence scientifique ;
4. Claude Code choisit l’implémentation compatible ;
5. Claude Fable audite exceptionnellement.

Pour les informations documentaires, la hiérarchie de `docs/documentation-governance.md` reste applicable.

Aucun message de conversation ne remplace durablement un document normatif lorsqu’une décision doit survivre à la session.

---

## 3. Cycle standard d’un lot

Chaque lot suit obligatoirement les étapes ci-dessous.

### Étape 1 — cadrage scientifique

ChatGPT produit ou rappelle :

- l’objectif ;
- le périmètre inclus ;
- le hors-périmètre ;
- les invariants ;
- les critères d’acceptation ;
- les documents normatifs applicables.

Lionel valide le lancement du lot.

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

ChatGPT vérifie :

- la conformité aux normes ;
- l’absence d’hypothèse physique ajoutée ;
- la couverture des invariants ;
- la pertinence des tests proposés ;
- le respect du périmètre.

Lionel arbitre et autorise ou refuse le passage à l’implémentation.

### Étape 4 — implémentation

Claude Code implémente uniquement le lot autorisé.

Il doit :

- limiter le diff au périmètre approuvé ;
- conserver les résultats individuels nécessaires aux validations ;
- ajouter les tests correspondants ;
- signaler toute difficulté qui remet en cause le plan ;
- s’arrêter avant d’inventer une décision manquante.

### Étape 5 — rapport de livraison

Claude Code fournit :

- résumé des changements ;
- fichiers modifiés ;
- décisions techniques ;
- tests exécutés et résultats ;
- écarts par rapport au plan ;
- limites connues ;
- SHA du commit si un commit a été autorisé.

### Étape 6 — validation

ChatGPT examine la conformité scientifique et conceptuelle.

Lionel valide :

- l’acceptation du lot ;
- les corrections éventuelles ;
- le commit ;
- le push ;
- le passage au lot suivant.

Un lot n’est pas accepté uniquement parce que les tests passent.

---

## 4. Format standard d’un prompt destiné à Claude Code

Chaque mission doit contenir les sections suivantes.

```text
Contexte
Documents obligatoires
Objectif du lot
Périmètre inclus
Hors-périmètre
Invariants non négociables
Travail demandé maintenant
Livrable attendu
Critères d’acceptation
Actions interdites sans autorisation
```

### 4.1 Contexte

Indique le niveau, le lot et l’état du projet.

### 4.2 Documents obligatoires

Liste les documents à lire avant toute action.

La liste commence toujours par :

```text
docs/collaboration-governance.md
docs/documentation-governance.md
```

Puis viennent les spécifications, décisions, manifestes, schémas et plans de validation applicables.

### 4.3 Objectif du lot

Décrit un résultat unique et vérifiable.

### 4.4 Périmètre inclus

Énumère ce que Claude Code peut modifier ou concevoir.

### 4.5 Hors-périmètre

Énumère explicitement ce qui ne doit pas être traité.

### 4.6 Invariants non négociables

Reprend les conventions scientifiques qui ne peuvent pas être modifiées.

### 4.7 Travail demandé maintenant

Précise si la demande porte sur :

- un audit ;
- un plan ;
- une implémentation ;
- des tests ;
- un correctif ;
- un rapport ;
- un commit ;
- un push.

Une autorisation pour une action n’autorise pas automatiquement les suivantes.

### 4.8 Livrable attendu

Décrit la forme exacte de la réponse attendue.

### 4.9 Critères d’acceptation

Liste les validations nécessaires.

### 4.10 Actions interdites sans autorisation

Doivent être précisées lorsque pertinentes :

```text
ne pas coder
ne pas modifier les documents normatifs
ne pas committer
ne pas pousser
ne pas créer de PR
ne pas lancer de campagne scientifique
ne pas élargir le périmètre
```

---

## 5. Format standard d’une réponse de Claude Code

Une réponse d’audit ou de plan doit utiliser cette structure :

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

Une réponse de livraison doit utiliser :

```text
1. Résumé
2. Diff réel
3. Décisions techniques
4. Tests exécutés
5. Résultats
6. Écarts au plan
7. Limites connues
8. Commit ou état Git
9. Actions restantes
```

Les affirmations telles que « terminé », « validé », « poussé » ou « conforme » doivent être accompagnées d’éléments vérifiables.

---

## 6. Gestion des ambiguïtés

Une ambiguïté est classée dans l’une des catégories suivantes.

### 6.1 Ambiguïté scientifique

Exemples : orientation d’un opérateur, définition d’une observable, seuil, interprétation d’un état.

Claude Code s’arrête et remonte la question.

ChatGPT propose une résolution fondée sur les normes existantes ou prépare une décision.

Lionel tranche lorsque la norme ne suffit pas.

### 6.2 Ambiguïté d’ingénierie

Exemples : type de classe, découpage de module, cache, représentation interne.

Claude Code décide et documente son choix, tant que les contrats externes restent inchangés.

### 6.3 Ambiguïté de périmètre

En cas de doute, l’élément est hors-périmètre jusqu’à autorisation explicite.

### 6.4 Contradiction documentaire

Aucune implémentation ne doit choisir silencieusement entre deux textes contradictoires.

La contradiction est signalée, puis corrigée selon `docs/documentation-governance.md` avant poursuite lorsque son impact est normatif.

---

## 7. Gestion des dérives et régressions d’échange

Une dérive est notamment caractérisée par :

- un participant empiétant sur le rôle d’un autre ;
- une implémentation lancée avant validation du plan ;
- une décision scientifique prise dans le code ;
- un élargissement de périmètre ;
- une action Git non autorisée ;
- une affirmation non vérifiée ;
- une perte du format standard ;
- un oubli des documents applicables.

Le rappel minimal est :

```text
Reviens à `docs/collaboration-governance.md` et reprends au dernier jalon validé.
```

Après ce rappel, le participant doit :

1. identifier la règle violée ;
2. indiquer le dernier jalon effectivement validé ;
3. distinguer ce qui a été fait de ce qui a seulement été annoncé ;
4. proposer la reprise la plus courte ;
5. ne poursuivre qu’à l’intérieur du périmètre restauré.

Si une modification erronée a déjà été publiée, elle doit être auditée avant tout nouveau travail.

---

## 8. Règles Git et autorisations

Les actions suivantes sont distinctes :

```text
modifier
stager
committer
pousser
ouvrir une PR
fusionner
```

L’autorisation de l’une n’implique pas l’autorisation des suivantes.

Avant d’annoncer un push ou une livraison :

- vérifier la branche ;
- vérifier le SHA de départ ;
- vérifier le diff réel ;
- vérifier les chemins modifiés ;
- vérifier l’absence de placeholder ;
- vérifier le contenu critique ;
- fournir le SHA final.

Un succès d’API Git ou une mise à jour de référence ne suffit pas à prouver que les fichiers annoncés ont été modifiés.

---

## 9. Recours à Claude Fable

Le recours à Claude Fable doit être formulé comme un audit borné.

Le prompt doit préciser :

- les documents à auditer ;
- les décisions déjà gelées ;
- les questions exactes ;
- les éléments hors-périmètre ;
- la forme du verdict attendu.

Claude Fable ne reçoit pas une mission générale de redéfinition du projet.

Après son retour :

1. ChatGPT classe les remarques ;
2. Lionel décide lesquelles retenir ;
3. les correctifs sont écrits dans les documents appropriés ;
4. le diff est audité ;
5. un nouveau gel n’est déclaré qu’après cohérence complète.

---

## 10. Jalon et mémoire de session

À la fin d’une session importante, un résumé doit préciser :

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

Le dépôt reste la mémoire durable du projet.

Les conversations servent à préparer et piloter le travail, mais les décisions durables doivent être inscrites dans les documents normatifs ou de gouvernance.

---

## 11. Règle de démarrage d’une nouvelle session

Une nouvelle session commence par :

1. lecture de `docs/collaboration-governance.md` ;
2. identification du dernier jalon validé ;
3. vérification de la branche et du commit de tête ;
4. lecture des documents spécifiques au lot ;
5. formulation de la prochaine action autorisée.

Il est interdit de déduire l’état réel du dépôt à partir d’un simple souvenir de conversation lorsqu’une vérification Git est possible.

---

## 12. Formule de rappel standard

La formule courte officielle est :

```text
Applique `docs/collaboration-governance.md` et reprends au dernier jalon validé.
```

Cette phrase impose automatiquement :

- le retour aux rôles définis ;
- l’arrêt de toute action hors-périmètre ;
- la vérification de l’état réel ;
- la reprise du format standard ;
- la distinction entre proposition, réalisation et validation ;
- la soumission à Lionel de toute décision non couverte.

---

## 13. Évolution de la présente charte

Toute modification de cette gouvernance exige :

1. une justification explicite ;
2. une nouvelle décision dans `docs/decisions.md` ;
3. un audit des documents qui la référencent ;
4. une vérification du diff réel ;
5. une validation de Lionel.

La charte ne peut pas être modifiée implicitement par les habitudes d’une conversation.