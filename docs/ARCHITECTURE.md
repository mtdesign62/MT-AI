# Architecture

## Main flow

```text
Image Input
  -> Scene Analyzer
  -> Prompt Builder / optional PE-I2I Rewriter
  -> QwenEngine (local Diffusers pipeline)
  -> Structural Fidelity
  -> Result / future auto-retry
```

## Separation rules

- UI never owns AI model logic.
- `QwenEngine` receives an `InstalledModel` and `RenderRequest`.
- Model files are managed independently of app source and installer.
- Model families are versioned side-by-side.
- Project metadata records model repository and revision for reproducibility.
- Future generators should implement the same render request/result boundary rather than rewriting UI code.

## Future-model adoption

The primary model backend intentionally uses `DiffusionPipeline.from_pretrained(local_path)` and `model_index.json`. This allows a future Qwen Diffusers pipeline to be instantiated from metadata when the installed Diffusers package supports the new class.

Update flow:

```text
Check official Qwen repos
 -> parse semantic version
 -> inspect model_index.json
 -> verify pipeline class in installed Diffusers
 -> download side-by-side
 -> activate only when compatible
 -> retain previous active model
 -> rollback on demand
```
