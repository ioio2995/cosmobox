import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

E = np.array([
    [ 1.0,  1.0,  1.0],
    [ 1.0, -1.0, -1.0],
    [-1.0,  1.0, -1.0],
    [-1.0, -1.0,  1.0],
], dtype=float)
E /= np.linalg.norm(E, axis=1, keepdims=True)


def laplacian(field: np.ndarray) -> np.ndarray:
    out = np.zeros_like(field)
    for axis in range(3):
        out += np.roll(field, 1, axis=axis)
        out += np.roll(field, -1, axis=axis)
        out -= 2.0 * field
    return out


def anisotropy_gradient(state: np.ndarray) -> np.ndarray:
    deformation = 1.0 - state
    resultant = deformation @ E
    return -np.einsum("...j,ij->...i", resultant, E)


def run(size=9, steps=500, dt=0.025, k_rest=1.0, k_coupling=0.35,
        k_aniso=0.20, damping=0.08, output_dir="fixed_tetrahedral_results"):
    T = np.ones((size, size, size, 4), dtype=float)
    V = np.zeros_like(T)

    c = size // 2
    radius = 1.7
    for x in range(size):
        for y in range(size):
            for z in range(size):
                r2 = (x-c)**2 + (y-c)**2 + (z-c)**2
                g = np.exp(-r2 / (2.0 * radius**2))
                T[x, y, z, 0] -= 0.40 * g
                T[x, y, z, 1] -= 0.18 * g
                T[x, y, z, 2] -= 0.18 * g
                T[x, y, z, 3] -= 0.18 * g

    coords = np.indices((size, size, size)).transpose(1,2,3,0)
    center = np.array([c, c, c], dtype=float)

    energy_hist, peak_hist, radius_hist = [], [], []

    for _ in range(steps):
        grad_rest = k_rest * (T - 1.0)
        grad_aniso = k_aniso * anisotropy_gradient(T)

        force = (
            -grad_rest
            -grad_aniso
            +k_coupling * laplacian(T)
            -damping * V
        )

        V += dt * force
        T += dt * V

        deformation = 1.0 - T
        resultant = deformation @ E
        energy_density = (
            0.5 * k_rest * np.sum((T - 1.0)**2, axis=-1)
            +0.5 * k_aniso * np.sum(resultant**2, axis=-1)
        )

        weights = np.sum(deformation**2, axis=-1)
        r = np.linalg.norm(coords - center, axis=-1)
        mean_radius = float(np.sum(r * weights) / max(np.sum(weights), 1e-15))

        energy_hist.append(float(np.sum(energy_density)))
        peak_hist.append(float(np.max(np.linalg.norm(resultant, axis=-1))))
        radius_hist.append(mean_radius)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    with (out / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step", "energy", "peak_resultant", "mean_radius"])
        for i, row in enumerate(zip(energy_hist, peak_hist, radius_hist)):
            w.writerow([i, *row])

    deformation = 1.0 - T
    resultant = deformation @ E
    magnitude = np.linalg.norm(resultant, axis=-1)

    plt.figure(figsize=(7, 6))
    plt.imshow(magnitude[:, :, c], origin="lower")
    plt.colorbar(label="Norme du vecteur spatial résultant")
    plt.title("Coupe centrale finale")
    plt.tight_layout()
    plt.savefig(out / "final_central_slice.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(energy_hist)
    plt.xlabel("Cycle")
    plt.ylabel("Énergie locale totale")
    plt.title("Évolution de l'énergie")
    plt.tight_layout()
    plt.savefig(out / "energy_history.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(radius_hist)
    plt.xlabel("Cycle")
    plt.ylabel("Rayon moyen de la perturbation")
    plt.title("Propagation de la perturbation")
    plt.tight_layout()
    plt.savefig(out / "propagation_radius.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(peak_hist)
    plt.xlabel("Cycle")
    plt.ylabel("Amplitude maximale")
    plt.title("Amplitude maximale du vecteur résultant")
    plt.tight_layout()
    plt.savefig(out / "peak_history.png", dpi=160)
    plt.close()

    print(f"Energie initiale : {energy_hist[0]:.6f}")
    print(f"Energie finale   : {energy_hist[-1]:.6f}")
    print(f"Pic initial      : {peak_hist[0]:.6f}")
    print(f"Pic final        : {peak_hist[-1]:.6f}")
    print(f"Rayon initial    : {radius_hist[0]:.6f}")
    print(f"Rayon final      : {radius_hist[-1]:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=9)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--output-dir", default="fixed_tetrahedral_results")
    args = parser.parse_args()
    run(size=args.size, steps=args.steps, output_dir=args.output_dir)
