# Cosmobox

Cosmobox est un simulateur modulaire d'un réseau diamant/blende déformable.

## Architecture

```text
cosmobox/
├── core/
│   ├── config.py
│   ├── matrix.py
│   ├── mechanics.py
│   └── simulation.py
├── physics/
│   ├── particle.py
│   └── metrics.py
├── visualization/
│   └── animation.py
└── cli.py
```

- `Matrix` porte la géométrie et les degrés de liberté.
- `Particle` injecte des contraintes et des flux.
- `MechanicsEngine` transforme ces contraintes en déformation réelle.
- `Simulation` orchestre les cycles.
- `AnimationRenderer` exporte un GIF ou un MP4.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Exécution

```bash
cosmobox --config examples/opposed.yaml
```

ou :

```bash
python -m cosmobox.cli --config examples/opposed.yaml
```

## Animation

```bash
cosmobox \
  --config examples/opposed.yaml \
  --animate \
  --rotate \
  --visual-amplification 5
```

Les résultats sont écrits dans `output/`.
