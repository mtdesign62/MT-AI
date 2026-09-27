# Changelog

## 0.2.4

- Added persistent rotating logs under the MT AI user-data log folder.
- Added copyable runtime diagnostics with free VRAM/RAM, model paths and package versions.
- Added runtime VRAM-aware memory profile selection and Smart Render size clamping.
- Added one controlled CUDA OOM recovery retry at a smaller internal resolution.
- Persisted the last selected local Qwen model folder and updated the PowerShell download guide.
- Improved render stage reporting for model load, preparation, diffusion, post-processing and fidelity checks.

## 0.1.0

- Initial MT AI MVP codebase.
- Added Qwen Image local Diffusers backend.
- Added future Qwen version/revision updater architecture with compatibility preflight and rollback.
- Added PySide6 desktop UI.
- Added scene analysis, architectural prompt builder and Structural Fidelity V1.
- Added optional Qwen PE-I2I prompt rewriting backend.
- Added project and upscale core abstractions.
