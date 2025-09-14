# Run the core authentication and initialization logic on startup
from . import core

# Import the node mappings from the node file
from .nodes.imagen_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Expose the mappings to ComfyUI
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']