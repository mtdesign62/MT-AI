from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from mt_ai.diagnostics import diagnostics_text
from mt_ai.inference.qwen import QwenEngine
from mt_ai.inference.types import RenderRequest
from mt_ai.models.manager import ModelManager
from mt_ai.models.registry import DEFAULT_IMAGE_MODEL, DEFAULT_PROMPT_REWRITER


def main() -> int:
    parser = argparse.ArgumentParser(prog="mt-ai-cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("diagnostics")
    model = sub.add_parser("model")
    msub = model.add_subparsers(dest="model_cmd", required=True)
    msub.add_parser("status")
    msub.add_parser("install-default")
    msub.add_parser("install-rewriter")
    msub.add_parser("check-updates")
    msub.add_parser("rollback")
    render = sub.add_parser("render")
    render.add_argument("input")
    render.add_argument("--prompt", required=True)
    render.add_argument("--output", default="mt_ai_render.png")
    render.add_argument("--seed", type=int, default=42)
    render.add_argument("--steps", type=int, default=40)
    args = parser.parse_args()
    manager = ModelManager()

    if args.cmd == "diagnostics":
        print(diagnostics_text())
        return 0
    if args.cmd == "model":
        if args.model_cmd == "status":
            active = manager.active()
            print(active.to_dict() if active else "No active model")
            return 0
        if args.model_cmd == "install-default":
            installed = manager.install_spec(DEFAULT_IMAGE_MODEL, progress=print)
            manager.activate(installed)
            print(f"Activated {installed.repo_id}@{installed.revision[:12]}")
            return 0
        if args.model_cmd == "install-rewriter":
            installed = manager.install_spec(DEFAULT_PROMPT_REWRITER, progress=print)
            manager.activate(installed)
            print(f"Activated prompt rewriter {installed.repo_id}@{installed.revision[:12]}")
            return 0
        if args.model_cmd == "check-updates":
            for item in manager.check_updates():
                print(item)
            return 0
        if args.model_cmd == "rollback":
            print(manager.rollback())
            return 0
    if args.cmd == "render":
        active = manager.active()
        if not active:
            raise SystemExit("No active model. Run: mt-ai-cli model install-default")
        source = Image.open(args.input).convert("RGB")
        result = QwenEngine(active).render(
            RenderRequest(source=source, prompt=args.prompt, seed=args.seed, steps=args.steps)
        )
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        result.image.save(args.output)
        print(args.output)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
