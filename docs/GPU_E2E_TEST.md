# MT AI — Real GPU End-to-End Validation

This document covers the real Qwen Image 2.1 image-editing test. It is intentionally separate from the normal GitHub-hosted Windows smoke tests.

## Why a self-hosted GPU runner is required

Standard GitHub-hosted Windows runners do not expose NVIDIA CUDA GPUs. MT AI therefore uses a manually dispatched job targeting:

```text
[self-hosted, gpu, nvidia]
```

The test runner should preferably have:

- NVIDIA GPU supported by current PyTorch CUDA wheels.
- Plenty of system RAM for Qwen Image 2.1 CPU offload.
- Large free SSD space for the model snapshot and Python environment.
- Current NVIDIA driver.
- Windows with PowerShell available.
- Internet access to Hugging Face for the first model download.

The GPU job starts with the `low-memory` MT AI profile and Qwen's CPU-offload support.

## What the test actually does

`scripts/gpu_e2e.py`:

1. Creates a deterministic, rights-free three-storey office viewport image.
2. Runs MT AI Scene Analyzer.
3. Builds a strict Architecture / Geometry Protection 98 prompt.
4. Installs and activates the official `Qwen/Qwen-Image-2.1` model if it is not already present.
5. Runs real local image-conditioned inference through `QwenEngine`.
6. Measures wall-clock render time and CUDA peak memory.
7. Runs Structural Fidelity on source vs output.
8. Checks that the generated output is not blank/uniform.
9. Writes:
   - `source.png`
   - `render.png`
   - `prompt.txt`
   - `report.json`
10. Uploads the directory as a GitHub Actions artifact.

The first real GPU baseline should use `min_fidelity=0`. This records the actual behavior before imposing a pass/fail Structural Fidelity threshold.

## Persistent model cache

The harness stores model data under:

```text
~/.mt-ai-gpu-e2e
```

on the self-hosted runner.

For a persistent runner, do not delete this directory between tests unless intentionally testing a clean model installation.

## GitHub Actions

Workflow:

```text
.github/workflows/gpu-e2e.yml
```

Use **Actions → gpu-e2e → Run workflow**.

Inputs:

- `run_gpu=true`
- `steps=20` for a first smoke render.
- `min_fidelity=0` for the first benchmark.
- `torch_index_url` matching the CUDA wheel family supported by the runner driver.

The workflow explicitly verifies:

```python
torch.cuda.is_available()
```

before attempting model inference.

## Interpreting report.json

Important fields:

```text
status
hardware.gpu_name
runtime.torch
runtime.diffusers
runtime.transformers
model.revision
render_seconds_wall
gpu_memory.peak_allocated_bytes
gpu_memory.peak_reserved_bytes
fidelity.overall_score
render_stats.std
```

A PASS proves that the exact MT AI engine can:

- download/load the selected Qwen revision,
- accept an architectural source image,
- perform image-conditioned inference,
- produce a valid image,
- complete the Structural Fidelity stage.

It does **not** prove that architectural preservation is already good enough for production. The actual `source.png` and `render.png` must be visually reviewed and the measured fidelity becomes the starting benchmark.

## After the first GPU baseline

Use the measured result to tune:

1. resolution,
2. steps,
3. memory profile,
4. geometry prompt constraints,
5. future protected masks/depth/segmentation,
6. automatic retry threshold.

Only after multiple representative scenes have been run should MT AI adopt a hard default fidelity threshold.
