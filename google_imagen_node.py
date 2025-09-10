import configparser
import torch
import numpy as np
from PIL import Image
import requests
import base64
import io
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

def get_gcloud_auth_token():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    gcloud_path = 'gcloud'
    if os.path.exists(config_path):
        config.read(config_path)
        if 'gcloud' in config and 'path' in config['gcloud'] and config['gcloud']['path']:
            gcloud_path = config['gcloud']['path']

    try:
        token = subprocess.check_output([gcloud_path, 'auth', 'print-access-token'], text=True).strip()
        return token
    except FileNotFoundError:
        raise Exception(f"'{gcloud_path}' not found. Please ensure the Google Cloud SDK is installed and the path is correct in config.ini or your system's PATH.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get gcloud auth token: {e}")

def image_to_base64(image_tensor):
    image_pil = Image.fromarray((image_tensor[0].cpu().numpy() * 255.).astype(np.uint8)).convert("RGB")
    buffered = io.BytesIO()
    image_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def mask_to_base64(mask_tensor):
    mask_pil = Image.fromarray((mask_tensor[0].cpu().numpy() * 255.).astype(np.uint8)).convert("L")
    buffered = io.BytesIO()
    mask_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

class GoogleImagen:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "model_version": (["imagen-4.0-fast-generate-001", "imagen-4.0-ultra-generate-001"],),
                "aspect_ratio": (["1:1", "9:16", "16:9", "4:3", "3:4"],),
                "resolution": (["standard", "high"],),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "edit_mode": (["inpainting", "outpainting"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate_image"
    CATEGORY = "Ru4ls/Imagen"

    def generate_image(self, prompt, model_version, aspect_ratio, resolution, seed=0,
                       image=None, mask=None, edit_mode="inpainting"):
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")

        if not project_id or not location:
            raise Exception("PROJECT_ID or LOCATION not found in .env file.")

        token = get_gcloud_auth_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_version}:predict"

        if image is None:
            # Text-to-image generation
            data = {
                "instances": [
                    {"prompt": prompt}
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": aspect_ratio
                }
            }
        else:
            # Image editing (inpainting/outpainting)
            if mask is None:
                raise Exception("Image editing (inpainting/outpainting) requires a mask. Please connect a mask to the 'mask' input.")
            image_b64 = image_to_base64(image)
            payload = {
                "prompt": prompt,
                "image": {"bytesBase64Encoded": image_b64},
                "edit_mode": edit_mode,
            }
            if mask is not None:
                mask_b64 = mask_to_base64(mask)
                payload["mask"] = {"image": {"bytesBase64Encoded": mask_b64}}
            
            data = {
                "instances": [payload],
                "parameters": {}
            }


        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            if 'predictions' not in result or not result['predictions']:
                raise Exception("No predictions found in API response")

            image_data_b64 = result['predictions'][0]['bytesBase64Encoded']
            image_data = base64.b64decode(image_data_b64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]

            return (image,)

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e.response.text}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse API response: {e}")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
