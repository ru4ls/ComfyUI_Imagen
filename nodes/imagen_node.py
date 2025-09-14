import json
import torch
import numpy as np
from PIL import Image
import io
import os

import vertexai
from vertexai.preview.vision_models import Image as VertexImage, ImageGenerationModel

# --- Load Model List ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
models_path = os.path.join(project_root, 'data', 'models.json')
with open(models_path, 'r') as f:
    models_data = json.load(f)
    model_list = models_data.get('imagen', [])

# --- Helper Functions ---
def tensor_to_pil(image_tensor):
    """Converts a torch tensor to a PIL Image."""
    return Image.fromarray((image_tensor[0].cpu().numpy() * 255.).astype(np.uint8)).convert("RGB")

def mask_tensor_to_pil(mask_tensor):
    """Converts a mask tensor to a PIL Image."""
    return Image.fromarray((mask_tensor[0].cpu().numpy() * 255.).astype(np.uint8)).convert("L")

# --- Unified Imagen Node ---
class ImagenNode:
    CATEGORY = "Ru4ls/Imagen"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "model_name": (model_list, {"default": model_list[0] if model_list else ''}),
            },
            "optional": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "aspect_ratio": (["1:1", "9:16", "16:9", "4:3", "3:4"], {"default": "1:1"}),
                "edit_mode": (["inpainting", "outpainting"], {"default": "inpainting"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "add_watermark": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_image"

    def _handle_error(self, message):
        print(f"\033[91mERROR: {message}\033[0m")
        return (torch.zeros(1, 64, 64, 3),)

    def process_image(self, prompt, model_name, image=None, mask=None, aspect_ratio="1:1", 
                      edit_mode="inpainting", seed=0, add_watermark=True):
        try:
            model = ImageGenerationModel.from_pretrained(model_name)

            if image is None:
                # --- Text-to-Image Logic ---
                params = {
                    "prompt": prompt,
                    "number_of_images": 1,
                    "aspect_ratio": aspect_ratio,
                    "add_watermark": add_watermark,
                }
                if not add_watermark:
                    params["seed"] = seed
                
                response = model.generate_images(**params)

            else:
                # --- Image-to-Image Logic ---
                base_image_pil = tensor_to_pil(image)
                buffered = io.BytesIO()
                base_image_pil.save(buffered, format="PNG")
                vertex_base_image = VertexImage(image_bytes=buffered.getvalue())

                vertex_mask = None
                if mask is not None:
                    mask_pil = mask_tensor_to_pil(mask)
                    buffered = io.BytesIO()
                    mask_pil.save(buffered, format="PNG")
                    vertex_mask = VertexImage(image_bytes=buffered.getvalue())

                params = {
                    "prompt": prompt,
                    "base_image": vertex_base_image,
                    "mask": vertex_mask,
                    "edit_mode": edit_mode,
                    "seed": seed, # Seed is always passed in edit mode
                }
                
                response = model.edit_image(**params)

            # --- Process and return the result ---
            if not response.images:
                return self._handle_error("API returned no images. The prompt may have been blocked.")

            pil_image = response.images[0]._pil_image
            output_image = np.array(pil_image).astype(np.float32) / 255.0
            output_tensor = torch.from_numpy(output_image)[None,]
            return (output_tensor,)

        except Exception as e:
            return self._handle_error(f"{type(e).__name__} in ImagenNode: {e}")

# --- Node Mappings ---
NODE_CLASS_MAPPINGS = {
    "ImagenNode": ImagenNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImagenNode": "Google Imagen",
}
