# root/core/core_auth.py

import os
from dotenv import load_dotenv
import google.auth
from google.cloud import aiplatform

print("--- Initializing Core Authentication ---")

# Determine the absolute path to the config directory
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config'))

# Load environment variables from the .env file in the config directory
dotenv_path = os.path.join(CONFIG_DIR, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Fetch Project ID and Location from environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# --- Google Cloud Authentication ---
CREDENTIALS = None
try:
    # google.auth.default() automatically finds and loads credentials
    # from the environment (including gcloud auth application-default login)
    CREDENTIALS, discovered_project_id = google.auth.default()
    
    # If PROJECT_ID is not in .env, try to use the one discovered by ADC
    if not PROJECT_ID and discovered_project_id:
        PROJECT_ID = discovered_project_id
        print(f"✅ Project ID discovered via Application Default Credentials: '{PROJECT_ID}'")

    if PROJECT_ID and LOCATION:
        print(f"✅ GCP Config Loaded: Project='{PROJECT_ID}', Location='{LOCATION}'")
        
        # Initialize Vertex AI Platform
        aiplatform.init(project=PROJECT_ID, location=LOCATION, credentials=CREDENTIALS)
        print("✅ Vertex AI SDK Initialized Successfully.")
        
    else:
        # This warning is crucial for the user to debug setup issues
        warning_message = "⚠️ GCP Config Warning: "
        if not PROJECT_ID:
            warning_message += "PROJECT_ID not found in .env or via ADC. "
        if not LOCATION:
            warning_message += "LOCATION not found in .env. "
        warning_message += "Nodes will fail."
        print(warning_message)

except google.auth.exceptions.DefaultCredentialsError:
    print("❌ GCP Authentication Error: Could not find default credentials.")
    print("   Please run 'gcloud auth application-default login' or set up credentials.")
    print("   See README for more details.")
except Exception as e:
    print(f"❌ An unexpected error occurred during GCP initialization: {e}")

def get_vertex_ai_client():
    """
    Returns an initialized Vertex AI client if available, otherwise None.
    Nodes should call this to get a ready-to-use client.
    """
    if not PROJECT_ID or not LOCATION or not CREDENTIALS:
        print("❌ Cannot create Vertex AI client due to missing configuration or credentials.")
        return None
    
    # The aiplatform module is already initialized, you can directly use it.
    # For specific services, you might create a client, e.g., PredictionServiceClient
    # For this template, returning the initialized aiplatform module is sufficient.
    return aiplatform
