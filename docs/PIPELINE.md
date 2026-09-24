# Render Pipeline

1. Load viewport image without modifying the source.
2. Analyze brightness, contrast, edge density and structural line distribution.
3. Combine user intent, scene summary, selected domain and Geometry Protection into a structured prompt.
4. Optionally rewrite the user's intent with Qwen PE-I2I, then re-apply MT AI's hard preservation constraints.
5. Load the selected local Qwen Image revision.
6. Preserve source aspect ratio while selecting a quality envelope.
7. Perform image-conditioned editing locally.
8. Compare source and result using Structural Fidelity V1.
9. Display the result; later milestones add controlled auto-retry and stronger masks/depth/segmentation.
