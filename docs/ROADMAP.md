# Roadmap

## Completed in 0.1.0 MVP codebase

- Foundation/repository structure.
- Model registry and versioned model storage.
- Hardware diagnostics.
- Qwen Diffusers inference adapter.
- Background-capable task architecture.
- Basic PySide6 GUI.
- Prompt builder.
- Scene analysis V1.
- Geometry/fidelity V1.
- Model update discovery + rollback architecture.
- Optional PE-I2I rewriter backend.
- Project persistence core.
- Upscale backend abstraction.

## Next P0

- Execute real Qwen Image 2.1 inference on target NVIDIA workstation.
- Pin the exact proven PyTorch/Transformers/Diffusers versions.
- Add model-download byte-level progress.
- Add true render cancellation hooks at diffusion-step boundaries where supported.
- Add project/history integration to GUI.
- Add controlled auto-retry using fidelity thresholds.
- Build and validate Windows installer on a clean Windows VM.

## Next P1

- Stronger scene understanding using a local VLM backend.
- Depth estimation backend.
- Segmentation backend.
- Protected/edit mask editor.
- Multi-reference UI.
- Dedicated licensed AI upscaler.
- Benchmark suite with 60+ rights-cleared architectural scenes.
