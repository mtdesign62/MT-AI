from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import ssl
import tempfile

# On Windows, Python HTTP clients can miss roots that are trusted by the OS.
# Build a temporary CA bundle from certifi plus the Windows ROOT store.
if sys.platform == "win32":
    try:
        import certifi
        pem_path = Path(tempfile.gettempdir()) / "mt_ai_windows_ca_bundle.pem"
        with open(certifi.where(), "rb") as src, open(pem_path, "wb") as dst:
            dst.write(src.read())
            dst.write(b"\n")
            for cert_bytes, encoding, _trust in ssl.enum_certificates("ROOT"):
                if encoding == "x509_asn":
                    dst.write(ssl.DER_cert_to_PEM_cert(cert_bytes).encode("ascii"))
        os.environ["SSL_CERT_FILE"] = str(pem_path)
    except Exception as exc:
        print(f"Windows CA bundle setup warning: {exc}", file=sys.stderr)

from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from mt_ai.analysis.fidelity import compare_source_and_render
from mt_ai.analysis.scene import SceneAnalyzer
from mt_ai.config import AppPaths, SettingsStore
from mt_ai.hardware import detect_hardware
from mt_ai.inference.qwen import QwenEngine
from mt_ai.inference.types import RenderRequest
from mt_ai.models.manager import ModelManager
from mt_ai.models.registry import DEFAULT_IMAGE_MODEL
from mt_ai.prompts import ProtectionOptions, RenderIntent, build_prompt


def make_paths(root: Path) -> AppPaths:
    return AppPaths(
        root=root,
        models=root / "models",
        projects=root / "projects",
        cache=root / "cache",
        logs=root / "logs",
        settings=root / "settings.json",
    ).ensure()


def create_architecture_scene(width: int = 1024, height: int = 576) -> Image.Image:
    """Create a deterministic rights-free architectural viewport-like test scene."""
    image = Image.new("RGB", (width, height), (213, 221, 229))
    d = ImageDraw.Draw(image)

    horizon = int(height * 0.72)
    d.rectangle((0, horizon, width, height), fill=(169, 174, 166))

    bx0, by0 = int(width * 0.16), int(height * 0.18)
    bx1, by1 = int(width * 0.86), int(height * 0.73)
    d.rectangle((bx0, by0, bx1, by1), fill=(202, 200, 190), outline=(56, 58, 62), width=5)

    roof_h = int(height * 0.035)
    d.rectangle((bx0 - 10, by0 - roof_h, bx1 + 10, by0), fill=(70, 72, 75))

    floor_h = (by1 - by0) // 3
    for floor in (1, 2):
        y = by0 + floor * floor_h
        d.line((bx0, y, bx1, y), fill=(86, 88, 92), width=4)

    margin_x = int(width * 0.035)
    window_w = int(width * 0.085)
    window_h = int(height * 0.105)
    for floor in range(3):
        fy = by0 + floor * floor_h + int(floor_h * 0.20)
        for col in range(6):
            x = bx0 + margin_x + col * int((bx1 - bx0 - 2 * margin_x) / 6)
            d.rectangle(
                (x, fy, x + window_w, fy + window_h),
                fill=(90, 120, 142),
                outline=(44, 48, 52),
                width=3,
            )
            d.line((x + window_w // 2, fy, x + window_w // 2, fy + window_h), fill=(52, 58, 62), width=2)

    entrance_w = int(width * 0.11)
    entrance_h = int(height * 0.15)
    ex0 = int((bx0 + bx1) / 2 - entrance_w / 2)
    ey0 = by1 - entrance_h
    d.rectangle((ex0, ey0, ex0 + entrance_w, by1), fill=(70, 96, 112), outline=(30, 34, 38), width=4)
    d.line((ex0 + entrance_w // 2, ey0, ex0 + entrance_w // 2, by1), fill=(35, 40, 45), width=2)

    # Two simple trees provide organic detail without obscuring the building.
    for tx in (int(width * 0.09), int(width * 0.91)):
        trunk_y0 = int(height * 0.48)
        d.rectangle((tx - 6, trunk_y0, tx + 6, horizon), fill=(103, 75, 53))
        d.ellipse((tx - 45, trunk_y0 - 72, tx + 45, trunk_y0 + 18), fill=(91, 129, 81), outline=(55, 84, 52), width=3)

    # Pavement and perspective guide lines.
    d.polygon(
        [
            (int(width * 0.23), horizon),
            (int(width * 0.77), horizon),
            (int(width * 0.92), height),
            (int(width * 0.08), height),
        ],
        fill=(190, 188, 181),
        outline=(115, 114, 110),
    )
    d.line((width // 2, horizon, width // 2, height), fill=(145, 143, 138), width=3)

    return image


def image_stats(image: Image.Image) -> dict:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def build_test_prompt(source: Image.Image) -> tuple[str, dict]:
    analysis = SceneAnalyzer().analyze(source, "Architecture")
    prompt = build_prompt(
        RenderIntent(
            mode="Architecture",
            user_prompt=(
                "Transform this exact three-storey office building viewport into a photorealistic "
                "professional architectural photograph at soft golden hour. Preserve the exact three "
                "floors, all window positions, entrance, roofline, camera framing and landscaping layout. "
                "Use realistic concrete, glass, subtle reflections, believable global illumination and "
                "natural shadows. Do not redesign the building."
            ),
            geometry_strength=98,
            mood="Soft golden hour",
            protections=ProtectionOptions(
                camera=True,
                architecture=True,
                furniture=True,
                windows=True,
                doors=True,
                ceiling=True,
                major_objects=True,
                signage=True,
            ),
            scene_summary=analysis.summary(),
        )
    )
    return prompt, analysis.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="MT AI real Qwen Image 2.1 GPU end-to-end test")
    parser.add_argument("--output-dir", default="gpu_e2e_artifacts")
    parser.add_argument("--data-root", default=str(Path.home() / ".mt-ai-gpu-e2e"))
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=576)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--memory-profile", choices=["quality", "balanced", "low-memory"], default="low-memory")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--min-fidelity", type=float, default=0.0)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = create_architecture_scene(args.width, args.height)
    source_path = out_dir / "source.png"
    source.save(source_path)
    prompt, scene_analysis = build_test_prompt(source)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    hw = detect_hardware(Path(args.data_root))
    report: dict = {
        "test": "MT AI Qwen Image 2.1 GPU E2E",
        "python": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "source": str(source_path),
        "requested_size": [args.width, args.height],
        "steps": args.steps,
        "seed": args.seed,
        "memory_profile": args.memory_profile,
        "hardware": hw.to_dict(),
        "scene_analysis": scene_analysis,
        "source_stats": image_stats(source),
        "status": "PREPARED",
    }

    if args.prepare_only:
        (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    try:
        import diffusers
        import torch
        import transformers
    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = f"AI runtime import failed: {exc}"
        (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise

    report["runtime"] = {
        "torch": getattr(torch, "__version__", "unknown"),
        "diffusers": getattr(diffusers, "__version__", "unknown"),
        "transformers": getattr(transformers, "__version__", "unknown"),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": getattr(torch.version, "cuda", None),
    }

    if not torch.cuda.is_available():
        report["status"] = "FAILED"
        report["error"] = "CUDA is not available; a real GPU test was not executed."
        (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    report["gpu"] = {
        "name": torch.cuda.get_device_name(0),
        "capability": list(torch.cuda.get_device_capability(0)),
        "total_vram_bytes": int(torch.cuda.get_device_properties(0).total_memory),
    }

    paths = make_paths(Path(args.data_root))
    manager = ModelManager(paths=paths, settings=SettingsStore(paths))
    active = manager.active()

    if active is None or active.repo_id != DEFAULT_IMAGE_MODEL.repo_id:
        print("Installing Qwen Image 2.1 model snapshot...")
        install_started = time.perf_counter()
        active = manager.install_spec(DEFAULT_IMAGE_MODEL, progress=print)
        manager.activate(active)
        report["model_install_seconds"] = time.perf_counter() - install_started

    report["model"] = {
        "repo_id": active.repo_id,
        "version": active.version,
        "revision": active.revision,
        "local_path": active.local_path,
        "pipeline_class": active.pipeline_class,
    }

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    free_before, total_before = torch.cuda.mem_get_info(0)

    engine = QwenEngine(active)
    render_started = time.perf_counter()
    result = engine.render(
        RenderRequest(
            source=source,
            prompt=prompt,
            seed=args.seed,
            steps=args.steps,
            quality="Draft",
            memory_profile=args.memory_profile,
            width=args.width,
            height=args.height,
        )
    )
    wall_seconds = time.perf_counter() - render_started

    free_after, total_after = torch.cuda.mem_get_info(0)
    peak_alloc = int(torch.cuda.max_memory_allocated(0))
    peak_reserved = int(torch.cuda.max_memory_reserved(0))

    render_path = out_dir / "render.png"
    result.image.save(render_path)
    fidelity = compare_source_and_render(source, result.image)
    stats = image_stats(result.image)

    report.update(
        {
            "status": "PASS",
            "render_path": str(render_path),
            "render_size": [result.image.width, result.image.height],
            "render_seconds_engine": result.duration_seconds,
            "render_seconds_wall": wall_seconds,
            "fidelity": fidelity.to_dict(),
            "render_stats": stats,
            "gpu_memory": {
                "free_before_bytes": int(free_before),
                "total_before_bytes": int(total_before),
                "free_after_bytes": int(free_after),
                "total_after_bytes": int(total_after),
                "peak_allocated_bytes": peak_alloc,
                "peak_reserved_bytes": peak_reserved,
            },
        }
    )

    # Basic catastrophic-output guards. Structural quality remains a measured benchmark,
    # not a hard architectural guarantee.
    if stats["std"] < 5.0:
        report["status"] = "FAILED"
        report["error"] = "Rendered image appears nearly blank/uniform."
    elif fidelity.overall_score < args.min_fidelity:
        report["status"] = "FAILED"
        report["error"] = (
            f"Structural Fidelity {fidelity.overall_score:.4f} is below required "
            f"{args.min_fidelity:.4f}."
        )

    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
