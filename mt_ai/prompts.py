from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

MODE_DEFAULTS = {
    "Interior": 90,
    "Architecture": 95,
    "Landscape": 92,
    "Masterplan": 98,
    "Enhance": 96,
    "Upscale": 100,
}

MODE_CONTEXT = {
    "Interior": "interior architectural photography",
    "Architecture": "exterior architectural photography",
    "Landscape": "professional landscape architectural photography",
    "Masterplan": "photorealistic architectural masterplan visualization",
    "Enhance": "high quality architectural image enhancement",
    "Upscale": "detail-preserving architectural image restoration",
}


@dataclass
class ProtectionOptions:
    camera: bool = True
    architecture: bool = True
    furniture: bool = True
    windows: bool = True
    doors: bool = True
    ceiling: bool = True
    major_objects: bool = True
    signage: bool = True

    def enabled_labels(self) -> list[str]:
        labels = []
        for name, value in vars(self).items():
            if value:
                labels.append(name.replace("_", " "))
        return labels


@dataclass
class RenderIntent:
    mode: str
    user_prompt: str
    geometry_strength: int
    mood: str = "Natural"
    protections: ProtectionOptions = field(default_factory=ProtectionOptions)
    scene_summary: str = ""


def geometry_instruction(strength: int) -> str:
    strength = max(0, min(100, strength))
    if strength >= 95:
        return (
            "Use extremely strict structural preservation. Treat the source geometry, camera, "
            "object placement and architectural proportions as immutable design constraints."
        )
    if strength >= 85:
        return (
            "Preserve the source geometry and camera very strongly. Improve realism without redesigning "
            "the scene or moving major objects."
        )
    if strength >= 65:
        return "Preserve the overall layout and camera while allowing small appearance-level variation."
    return "Preserve recognizable composition but allow moderate creative appearance variation."


def build_prompt(intent: RenderIntent, extra_forbidden: Iterable[str] = ()) -> str:
    protected = ", ".join(intent.protections.enabled_labels()) or "none"
    forbidden = [
        "do not change the camera viewpoint",
        "do not crop or zoom the composition",
        "do not change floor count",
        "do not move doors or windows",
        "do not replace major furniture with different designs",
        "do not add or remove major architectural masses",
    ]
    forbidden.extend(extra_forbidden)
    context = MODE_CONTEXT.get(intent.mode, "photorealistic architectural visualization")
    parts = [
        f"SOURCE / TASK: Transform the provided 3D viewport into {context}.",
        f"USER INTENT: {intent.user_prompt.strip() or 'Create a natural photorealistic render.'}",
    ]
    if intent.scene_summary:
        parts.append(f"SCENE ANALYSIS: {intent.scene_summary}")
    parts.extend(
        [
            f"MOOD / LIGHTING: {intent.mood}.",
            f"GEOMETRY CONSTRAINT: {geometry_instruction(intent.geometry_strength)}",
            (
                "CAMERA CONSTRAINT: Preserve the exact source viewpoint, perspective, framing, camera "
                "height and aspect ratio."
            ),
            (
                "MATERIAL REALISM: Preserve material intent while improving physically believable "
                "roughness, reflections, micro-texture, glass, metal, wood, stone, fabric and leather."
            ),
            (
                "PHOTOGRAPHIC QUALITY: Natural global illumination appearance, believable shadows, "
                "realistic dynamic range, physically plausible reflections, professional architectural "
                "photography, no artificial oversharpening."
            ),
            f"PROTECTED ELEMENTS: {protected}.",
            "FORBIDDEN CHANGES: " + "; ".join(forbidden) + ".",
        ]
    )
    if intent.mode == "Masterplan":
        parts.append(
            "MASTERPLAN RULE: Keep roads, plot boundaries, building footprints, block orientation, water "
            "bodies and major green-space boundaries fixed."
        )
    if intent.mode == "Enhance":
        parts.append(
            "ENHANCE RULE: Improve quality only. Do not redesign, add, remove or relocate major objects."
        )
    return "\n\n".join(parts)


def suggest_user_prompt(mode: str, mood: str = "Natural") -> str:
    suggestions = {
        "Interior": f"{mood} light, premium but natural materials, realistic architectural photography",
        "Architecture": f"{mood} exterior light, realistic facade materials, subtle environment activity",
        "Landscape": f"{mood} atmosphere, natural vegetation, realistic ground and water materials",
        "Masterplan": f"{mood} aerial visualization, realistic vegetation and materials, preserve exact plan",
        "Enhance": "Improve material, lighting, reflections and fine detail only; keep the scene unchanged",
        "Upscale": "Preserve exact image content while recovering fine architectural texture and edges",
    }
    return suggestions.get(mode, suggestions["Architecture"])
