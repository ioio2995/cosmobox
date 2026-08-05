# Plan de validation — niveau 0

## T1 — Hermiticité par terme

Pour chaque terme T construit dans le sous-espace physique :

norm(T - T†) < 1e-13.

Le test est appliqué séparément à H_dot, H_hop, H_E et H_B.

## T2 — Fermeture du sous-espace physique

Sur les plus petites géométries, construire H dans l’espace complet non contraint et le projecteur P_phys. Exiger :

norm((1-P_phys) H P_phys) < 1e-13.

## T3 — Invariance de jauge

Dans l’espace complet du triangle puis de ring4 :

norm([H, G_i]) / max(norm(H),1) < 1e-12

pour tout i.

Le test ne doit pas être réalisé uniquement après projection, où G_i est nul par construction.

## T4 — Algèbre fermionique

Construire explicitement c_a et c†_a dans le petit espace complet et vérifier :

{c_a,c†_b} = delta_ab ;
{c_a,c_b} = 0.

Ajouter un contrôle spectral tight-binding lorsque la jauge est désactivée dans un mode réservé aux tests.

## T5 — Amplitudes des quantum links

Pour S = 1,2,3 et tout m :

S^+|m> = sqrt(S(S+1)-m(m+1)) |m+1>.

Vérifier également l’annulation aux bords et les amplitudes de U = S^+/sqrt(S(S+1)).

## T6 — Génération par arbre contre brute force

Comparer exactement les listes triées de clés physiques obtenues par :

- résolution par arbre couvrant ;
- énumération exhaustive de tous les flux suivie d’un filtrage G_i = 0.

Géométries minimales : triangle, chain3, ring4, ring5. Étendre à disk7 seulement si le coût reste raisonnable avec une petite valeur de M.

Critère : égalité exacte des clés et des rapports de secteurs.

## T7 — Conservation de la charge totale

Dans l’espace complet puis dans l’espace physique :

norm([H,Q_tot]) < 1e-13.

## T8 — Absence de fuite dynamique

Évoluer un état physique aléatoire avec expm_multiply jusqu’à t*J = 100 sur un petit système. Vérifier que la composante hors sous-espace physique reste inférieure à 1e-10.

## T9 — Limites analytiques

À t = K = 0, comparer le spectre numérique à la somme :

- des spectres des dots isolés ;
- de l’énergie électrique (g_E/2) somme_e E_e^2 ;
- restreinte aux configurations satisfaisant la loi de Gauss.

Accord valeur par valeur à la précision numérique.

## Robustesse de troncation

Comparer S = 1,2,3 sur triangle et ring4, M = 2 :

- dix premiers écarts spectraux ;
- matrice d’information mutuelle de l’état fondamental lorsque disponible ;
- moyenne de E_e^2 par lien.

Le niveau 1 ne doit pas utiliser S = 1 par défaut si les résultats ne montrent aucune tendance de convergence vers S = 2 puis S = 3.

## Critères du lot 1

Le lot lattice + encoding est accepté lorsque :

- toutes les géométries sont déterministes ;
- l’arbre est connecté, acyclique et contient N-1 liens ;
- chords = edges - tree_edges ;
- chaque plaquette est fermée et cohérente avec les orientations ;
- encode/decode est bijectif sur toutes les petites configurations testables ;
- les débordements uint64 et valeurs de flux invalides lèvent une exception explicite.

## Critères du lot 2

basis.py est accepté lorsque T6 passe exactement et que le rapport de secteurs est reproductible.

## Statut d'implémentation — Hamiltonien (lots 4A-4C)

Couverture effective de T1, T2, T3, T7, T8, T9 pour H_dot, H_hop, H_E, H_B et H_total, dans `tests/level0/test_hamiltonian.py` :

- **T1** (hermiticité) : chaque terme séparément et le total, sur triangle/chain3/ring4/ring5 (H_B et le total : triangle/ring4/ring5).
- **T2** (fermeture) : positif sur la base physique réelle ; négatif sur une base volontairement incomplète (`RuntimeError` explicite).
- **T3** (invariance de jauge) : `[H_x, G_i]=0` vérifié numériquement dans le petit espace complet non contraint (pas la base physique, où ce serait trivial), pour chaque terme puis pour H_total.
- **T7** (conservation de charge) : nombre fermionique total conservé (H_dot, H_hop) ; vecteur d'occupation complet conservé exactement (H_B, qui ne touche jamais l'occupation).
- **T8** (absence de fuite) : chaque transition non nulle vérifiée indépendamment (décodage, `is_physical`, appartenance à `key_index`) ; évolution unitaire courte (`expm_multiply`) sur H_total, conservation de la norme et de l'énergie `⟨H⟩`.
- **T9** (limites analytiques) : couplages nuls, terme électrique seul, terme J seul, transition de hopping isolée, plaquette isolée — chaque cas comparé à un calcul analytique explicite, pas seulement à une formule supposée.

`disk7` : validé au niveau des actions (`W_p`/`W_p†` sur un échantillon déterministe de la base réelle), jamais par assemblage matriciel complet — coût jugé déraisonnable (~450 000+ états) pour la suite de tests courante.

T4 (signes Jordan-Wigner) et T5 (amplitudes S±) : validés en amont dans `tests/level0/test_operators.py` (lot 3B). T6 : validé dans `tests/level0/test_basis.py` (lot 2).
