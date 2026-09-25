# MT AI — AI Architectural Renderer

MT AI is a Windows-first, local-first architectural image renderer designed to turn viewport screenshots from SketchUp, 3ds Max, Blender and similar tools into photorealistic images while preserving the source design.

> **Core rule:** Geometry is truth. AI changes appearance, not design.

## Current repository status

This is the first working MVP codebase (`0.1.0`). The deterministic/core test suite passes. Real Qwen Image 2.1 GPU inference has also been validated successfully on the target RTX 5060 Ti workstation using the low-memory probe; routine CI remains GPU-free so development tests do not monopolize the workstation.

Implemented now:

- PySide6 desktop UI skeleton with dark professional layout.
- Interior / Architecture / Landscape / Masterplan / Enhance / Upscale modes.
- Drag & drop, Open Image and Clipboard Paste.
- Scene Analysis V1 (fast deterministic image/geometry statistics).
- Structured architectural Prompt Engine with strict geometry/camera rules.
- Geometry Protection slider and protection switches.
- Local Qwen Image inference backend through Diffusers auto-pipeline loading.
- CUDA OOM error handling.
- Structural Fidelity V1 using edge correspondence + line orientation.
- Optional official Qwen PE-I2I prompt-rewriter backend.
- Versioned Model Manager with install, activate and rollback.
- Future Qwen model discovery/update checks.
- Side-by-side model revisions; updates never need to overwrite the current model.
- Compatibility preflight against the installed Diffusers pipeline class.
- Project persistence core.
- 2x/4x pluggable upscale API with an always-available Lanczos fallback.
- CLI diagnostics/model/render commands.
- Windows setup/build scripts and CI skeleton.

## Model update design

Model updates are deliberately separate from app updates.

MT AI stores models by family/repository/revision, for example:

```text
<user-data>/MT AI/models/
  qwen-image/
    Qwen_Qwen-Image-2.1/
      <revision>/
    Qwen_Qwen-Image-2.2/
      <revision>/
```

The updater can discover official repositories matching:

```text
Qwen/Qwen-Image-X.Y[.Z]
```

It detects both:

1. a newer model version (for example 2.1 -> 2.2 / 3.0), and
2. a newer revision of the currently selected model.

Before activation MT AI reads the remote `model_index.json` and checks whether the required pipeline class exists in the installed Diffusers build. If the new model needs a newer Diffusers version, it can be downloaded but is not automatically activated. The previous model remains available for rollback.

This design is intended to make later Qwen Image versions adoptable without rewriting the UI or project system, provided the future model remains compatible with a Diffusers-style image-editing interface. Breaking upstream API changes will require an MT AI adapter update rather than silently breaking existing installations.

## Official Qwen backend

The current primary model is:

```text
Qwen/Qwen-Image-2.1
```

The engine uses image-conditioned editing:

```python
pipe(prompt=..., image=source_image, ...)
```

through Diffusers and loads from a local snapshot after installation.

Optional prompt rewriting uses:

```text
Qwen/Qwen-Image-2.1-PE-I2I
```

and follows the official Transformers image-to-text prompt-rewriting pattern.

## Windows development setup

Recommended:

- Windows 10/11
- Python 3.11
- NVIDIA GPU
- recent NVIDIA driver / CUDA-compatible PyTorch
- large SSD space for model weights

PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
python -m mt_ai
```

Manual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements/base.txt
pip install -r requirements/ai.txt
```

If the installed Diffusers release does not yet contain `QwenImage21Pipeline`, install a current Diffusers build containing Qwen Image 2.1 support before rendering.

## First launch

1. Launch `python -m mt_ai`.
2. Open **Model Manager**.
3. Click **Install Qwen Image 2.1**.
4. Optionally install **Prompt Rewriter**.
5. Open/paste a viewport screenshot.
6. Select a render mode and mood.
7. Adjust Geometry Protection if needed.
8. Enter a short prompt or use **Suggest Prompt** / **AI Rewrite Prompt**.
9. Press **RENDER**.

## CLI

```powershell
python -m mt_ai.cli diagnostics
python -m mt_ai.cli model status
python -m mt_ai.cli model install-default
python -m mt_ai.cli model install-rewriter
python -m mt_ai.cli model check-updates
python -m mt_ai.cli model rollback
```

Render:

```powershell
python -m mt_ai.cli render viewport.png --prompt "warm morning, photorealistic" --output result.png
```

## Testing

Fast test suite:

```powershell
$env:PYTHONPATH="."
pytest -q
```

GPU inference tests are intentionally separate because downloading/loading Qwen Image is expensive.

## Important current limitations

- Scene Analysis V1 is a deterministic fallback, not yet a full semantic architectural VLM analysis system.
- Structural Fidelity V1 is an image-structure heuristic, not CAD-level geometric validation.
- The default Upscale implementation is a fallback resampler until a separately licensed AI upscaler is selected and benchmarked.
- Real Qwen inference is proven on the target RTX 5060 Ti, but production-size architectural renders still need broader quality/performance benchmarking.
- Windows installer is a build skeleton at this stage, not yet clean-VM validated.
- The Qwen model license must be reviewed before commercial distribution.

See `docs/ROADMAP.md` for the remaining milestones.
