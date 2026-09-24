from __future__ import annotations

import json
import re
from dataclasses import dataclass

from PIL import Image

from mt_ai.models.schemas import InstalledModel


@dataclass(frozen=True)
class RewriteResult:
    rewritten_prompt: str
    ratio_follow: str = "<image1>"
    wh_ratio: str = ""


class PromptRewriteError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    candidates = re.findall(r"\{.*?\}", text, flags=re.DOTALL)
    for candidate in reversed(candidates):
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "rewritten_prompt" in obj:
            return obj
    raise PromptRewriteError("Prompt rewriter did not return the expected JSON object")


class QwenPEI2IRewriter:
    """Optional official Qwen-Image PE-I2I prompt rewriter, loaded locally."""

    def __init__(self, model: InstalledModel) -> None:
        self.model_info = model
        self.model = None
        self.processor = None
        self.system_prompt = ""

    def load(self) -> None:
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as exc:
            raise PromptRewriteError("Transformers/PyTorch are required for PE-I2I") from exc
        model_path = self.model_info.local_path
        self.processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_path,
            dtype=torch.bfloat16,
            device_map="auto",
            local_files_only=True,
        ).eval()
        system_path = self.model_info.path / "system_prompt.txt"
        if not system_path.exists():
            raise PromptRewriteError("system_prompt.txt is missing from the prompt rewriter model")
        self.system_prompt = system_path.read_text(encoding="utf-8").strip()

    def rewrite(self, image: Image.Image, user_prompt: str) -> RewriteResult:
        if self.model is None or self.processor is None:
            self.load()
        import torch

        messages = [
            {"role": "system", "content": [{"type": "text", "text": self.system_prompt}]},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image.convert("RGB")},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            enable_thinking=True,
        ).to(self.model.device)
        input_length = inputs["input_ids"].shape[1]
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=24000,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=20,
            )
        generated = out[0, input_length:]
        text = self.processor.decode(generated, skip_special_tokens=True)
        data = _extract_json(text)
        return RewriteResult(
            rewritten_prompt=data["rewritten_prompt"],
            wh_ratio=data.get("wh_ratio", ""),
            ratio_follow=data.get("ratio_follow", "<image1>"),
        )
