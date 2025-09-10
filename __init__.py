from .google_imagen_node import GoogleImagen

NODE_CLASS_MAPPINGS = {
    "GoogleImagen": GoogleImagen,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GoogleImagen": "Google Imagen",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']