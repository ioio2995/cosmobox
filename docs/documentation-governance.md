# Gouvernance normative de la documentation

Statut : **gelé**

Ce document définit l’architecture documentaire normative du dépôt Cosmobox. Il s’applique à tous les niveaux scientifiques et à toute modification susceptible de changer une définition physique, un protocole expérimental, une interface de sortie ou un critère de validation.

---

## 1. Principe général

Le dépôt distingue strictement :

1. le modèle physique général ;
2. les spécifications normatives par niveau ;
3. les décisions gelées ;
4. les plans de validation ;
5. les manifestes de campagne ;
6. les schémas de données ;
7. les résultats ;
8. les documents exploratoires temporaires.

Une information normative ne doit avoir qu’une source de vérité principale. Les autres documents peuvent la résumer ou y faire référence, mais ne doivent pas en maintenir une copie divergente.

Le code implémente les documents normatifs. Il ne redéfinit pas silencieusement les conventions scientifiques.

---

## 2. Emplacement normatif par type de document

### 2.1 `docs/physical-model.md`

Contient le modèle physique général et les conventions communes à plusieurs niveaux :

- degrés de liberté ;
- loi de Gauss ;
- Hamiltonien général ;
- paramètres physiques admissibles ;
- limites d’interprétation générales.

Ce fichier ne doit pas contenir les paramètres détaillés d’une campagne particulière.

### 2.2 `docs/levelN-specification.md`

Contient la spécification normative d’un niveau :

- question scientifique ;
- périmètre et exclusions ;
- définitions mathématiques ;
- conventions opératoires ;
- comportement attendu ;
- architecture conceptuelle minimale ;
- critères d’acceptation généraux ;
- conclusions autorisées et interdites.

Toute spécification gelée d’un niveau doit résider dans `docs/`, selon la convention :

```text
docs/level0-specification.md
docs/level1-specification.md
docs/level2-specification.md
```

Le répertoire `features/` ne peut pas être la source normative d’un niveau gelé.

### 2.3 `docs/decisions.md`

Contient le journal immuable des décisions structurantes :

- décision ;
- statut ;
- justification synthétique ;
- portée ;
- documents normatifs concernés.

Une décision ne remplace pas une spécification détaillée. Elle enregistre le choix et son gel.

Toute modification d’une décision gelée exige une nouvelle entrée de décision. Une ancienne décision n’est pas réécrite pour masquer l’historique, sauf correction purement éditoriale sans changement de sens.

### 2.4 `docs/levelN-validation-plan.md`

Contient le contrat de validation :

- exigences identifiées ;
- cas minimaux ;
- type de preuve ou de test ;
- tolérances ;
- critères de réussite ;
- résultats structurellement attendus, y compris les valeurs `null` légitimes.

Le plan de validation ne doit pas introduire de nouvelle convention scientifique absente de la spécification ou des décisions.

### 2.5 `experiments/`

Contient les protocoles et manifestes de campagne :

- grille exacte de paramètres ;
- géométries et troncatures ;
- fenêtres spectrales ;
- groupes ciblés ;
- seuils ;
- graines ;
- garde-fous de ressources ;
- interdictions post-hoc ;
- empreinte et version de campagne.

Un manifeste pré-enregistré fixe une exécution particulière. Il ne remplace ni le modèle général ni la spécification du niveau.

### 2.6 `schemas/`

Contient les contrats de sérialisation versionnés.

Toute modification incompatible exige une nouvelle version de schéma. Un schéma décrit la forme des données ; il ne doit pas être la seule source d’une définition physique.

### 2.7 `results/`

Contient les sorties de campagne ou leur structure documentée.

Les résultats ne modifient jamais rétroactivement les seuils, les définitions ou les critères du manifeste qui les a produits.

### 2.8 `features/`

Répertoire réservé aux propositions temporaires et non gelées :

- exploration d’un niveau futur ;
- brouillon de fonctionnalité ;
- alternatives encore ouvertes ;
- questions de conception non résolues.

Un document `features/` doit porter explicitement un statut non normatif.

Lorsqu’une feature est validée :

1. son contenu normatif est migré vers `docs/levelN-specification.md` ou le document normatif approprié ;
2. les décisions sont enregistrées dans `docs/decisions.md` ;
3. les protocoles sont placés dans `experiments/` ;
4. les schémas sont placés dans `schemas/` ;
5. les validations sont placées dans `docs/levelN-validation-plan.md` ;
6. le fichier `features/` est supprimé après vérification de la migration.

L’historique Git suffit pour conserver le brouillon d’origine.

---

## 3. Hiérarchie des sources de vérité

En cas de divergence, l’ordre d’autorité est :

1. décision gelée la plus récente dans `docs/decisions.md` ;
2. manifeste pré-enregistré pour les valeurs propres à une campagne ;
3. spécification normative du niveau pour les définitions scientifiques et techniques ;
4. modèle physique général ;
5. plan de validation ;
6. schéma de données ;
7. README et documents de synthèse ;
8. documents exploratoires dans `features/`.

Cette hiérarchie ne dispense pas de corriger immédiatement toute contradiction. Elle sert uniquement à déterminer quelle valeur appliquer pendant la correction.

---

## 4. États documentaires

Les statuts autorisés sont :

```text
brouillon
revue en cours
validé pour gel
gelé
clos
supersédé
archivé
```

### `brouillon`

Document exploratoire, non normatif, implémentation interdite sauf prototype explicitement isolé.

### `revue en cours`

Contenu stabilisé mais comportant encore des décisions ouvertes.

### `validé pour gel`

Revue scientifique terminée ; le paquet documentaire doit encore être rendu cohérent et vérifié.

### `gelé`

Toutes les décisions bloquantes sont fermées, les références sont cohérentes et l’implémentation est autorisée selon les lots définis.

### `clos`

Niveau implémenté, validé et accompagné de sa synthèse de clôture.

### `supersédé`

Document remplacé par une source normative plus récente, avec référence obligatoire vers celle-ci.

### `archivé`

Document conservé uniquement pour son intérêt historique.

Un document ne peut pas être déclaré `gelé` si un autre document normatif indique encore que les mêmes décisions sont ouvertes.

---

## 5. Règles de non-duplication

Une définition complète ne doit exister que dans un document normatif principal.

Les documents secondaires doivent utiliser des renvois explicites, par exemple :

```text
Voir `docs/level1-specification.md`, §16.
```

Les résumés sont autorisés dans `docs/decisions.md` et le README, à condition :

- qu’ils soient identifiés comme synthèses ;
- qu’ils ne reformulent pas une valeur différemment ;
- qu’ils soient mis à jour dans le même paquet documentaire lorsque leur sens change.

---

## 6. Modification d’une norme gelée

Toute modification scientifique ou normative après gel exige :

1. une nouvelle décision dans `docs/decisions.md` ;
2. la mise à jour de la spécification concernée ;
3. la mise à jour du manifeste si une campagne est affectée ;
4. la mise à jour du plan de validation ;
5. une nouvelle version du schéma si la compatibilité des sorties change ;
6. une vérification des références dans le README et les synthèses.

Une correction orthographique ou de mise en forme sans modification de sens ne nécessite pas de nouvelle décision.

---

## 7. Contrôle obligatoire avant push documentaire

Avant de déclarer un paquet documentaire terminé ou gelé, il faut vérifier :

### 7.1 Présence réelle des fichiers

- les nouveaux fichiers existent sur la branche cible ;
- les fichiers annoncés comme modifiés apparaissent dans le diff ;
- les fichiers annoncés comme supprimés sont réellement absents ;
- aucun placeholder, contenu temporaire ou marqueur de génération ne subsiste.

### 7.2 Cohérence des statuts

- aucun document ne dit « implémentation interdite » si D013 ou une décision équivalente autorise l’implémentation ;
- aucune décision gelée n’est encore listée comme question ouverte ;
- le README reflète l’état réel du niveau.

### 7.3 Cohérence des valeurs

Les valeurs suivantes doivent être comparées entre les documents concernés :

- seuils ;
- fenêtres ;
- paramètres de campagne ;
- dimensions ;
- conventions d’opérateurs ;
- listes d’observables ;
- raisons de `null` ;
- géométries et troncatures ;
- critères de verdict.

### 7.4 Références

- aucun lien ne pointe vers un fichier supprimé ou déplacé ;
- les noms et chemins respectent l’arborescence normative ;
- les renvois entre spécification, décisions, manifeste, schéma et validation sont présents.

### 7.5 Diff final

Le diff entre le commit de base et la tête de branche doit être contrôlé fichier par fichier.

Un succès technique de mise à jour de branche ou de référence Git ne constitue pas une preuve qu’un contenu a été créé ou modifié.

Le message final doit distinguer explicitement :

- ce qui a été réellement poussé ;
- ce qui n’a pas été modifié ;
- le SHA de tête vérifié ;
- la liste réelle des fichiers du diff.

---

## 8. Granularité des commits

Un paquet documentaire cohérent peut comporter plusieurs commits techniques lorsque l’outil utilisé impose une écriture fichier par fichier.

Dans ce cas :

- la branche doit être vérifiée sur le diff global ;
- aucun état intermédiaire ne doit être présenté comme le gel final ;
- le dernier commit doit laisser tous les documents cohérents ;
- une consolidation ultérieure par squash est possible avant fusion.

Lorsque l’outil le permet, un commit logique unique est préférable pour une migration normative.

---

## 9. Règles pour le README

Le README est une porte d’entrée et une synthèse, pas une source scientifique principale.

Il doit indiquer :

- l’état de chaque niveau ;
- le chemin de sa spécification normative ;
- le chemin de sa synthèse de clôture lorsqu’elle existe ;
- le rôle des répertoires principaux ;
- le lien vers le présent document de gouvernance.

Il ne doit pas contenir de liste détaillée de décisions susceptible de diverger des documents normatifs.

---

## 10. Critère d’acceptation d’un gel documentaire

Un niveau est documenté comme gelé uniquement si :

1. sa spécification normative réside dans `docs/` ;
2. ses décisions bloquantes sont enregistrées et fermées ;
3. son manifeste est complet lorsque la campagne est définie ;
4. son plan de validation existe ;
5. son schéma existe si des données structurées sont produites ;
6. les questions encore ouvertes sont non bloquantes et clairement séparées ;
7. aucune contradiction de statut ou de valeur ne subsiste ;
8. le diff final a été vérifié ;
9. le README pointe vers les bons documents.

---

## 11. Application au niveau 1B

Pour le niveau 1B, les sources normatives sont :

```text
docs/physical-model.md
docs/level1-specification.md
docs/decisions.md              # D012, D013 et décisions ultérieures
experiments/LEVEL1B-preregistered-manifest.md
docs/level1-validation-plan.md
schemas/level1-correlators-v1.schema.json
```

Les anciens documents placés dans `features/` ont été supprimés après migration. Ils ne constituent plus une source de vérité active.
