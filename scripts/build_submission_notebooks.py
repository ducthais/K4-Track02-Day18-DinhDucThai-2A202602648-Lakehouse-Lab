"""Generate executed .ipynb notebooks with preserved outputs for submission."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import jupytext
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
OUT_DIR = ROOT / "submission" / "notebooks"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scripts = sorted(p for p in NB_DIR.glob("[0-9]*.py"))
    print(f"Found {len(scripts)} notebooks to build in {OUT_DIR}:")
    
    total_t0 = time.perf_counter()
    for p in scripts:
        t0 = time.perf_counter()
        out_path = OUT_DIR / (p.stem + ".ipynb")
        print(f"\n--- Processing {p.name} -> {out_path.name} ---")
        
        # Read percent script into notebook
        nb = jupytext.read(str(p))
        
        # Ensure metadata specifies python3 kernel
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3"
        }
        
        # Execute notebook
        client = NotebookClient(
            nb,
            timeout=600,
            kernel_name="python3",
            resources={"metadata": {"path": str(NB_DIR)}}
        )
        client.execute()
        
        # Write executed notebook
        with open(out_path, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)
            
        dt = time.perf_counter() - t0
        print(f"  PASS: {out_path.name} generated with {len(nb.cells)} cells in {dt:.1f}s")
        
    print(f"\nAll {len(scripts)} notebooks built successfully in {time.perf_counter() - total_t0:.1f}s")


if __name__ == "__main__":
    main()
