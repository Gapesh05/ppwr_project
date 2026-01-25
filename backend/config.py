import logging
import sys
import os
from typing import Dict, Any, Optional

# -------------------------
# CONFIGURATION DATA
# -------------------------
CONFIG = {
    "upload_folder": "shared_data/uploads/",
    "archive_folder": "shared_data/archive/",
    "input_template_folder": "shared_data/input_templates/",
    "download_template_folder": "shared_data/output_templates/",
    "sotafile_path": "shared_data/sota/",

    "storage": {
        "chroma": {
            "host": "10.134.44.228",
            "port": 8000,
            "collection_name": "PFAS_10110_PFAS",
            "ppwr_collection_name": "PPWR_Supplier_Declarations"
        },
        "chunking": {
            "size": 300,
            "overlap": 50
        },
        "postgresql": {
            "host": "10.134.44.228",
            "port": "5432",
            "dbname": "adminportaldb",
            "user": "airadbuser",
            "password": "Password123"
        }
    },
    
    "embeddings": {
        "backend": "azure",
        "azure": {
            "model": "text-embedding-3-large",
            "model_version": "2023-05-15",
            "base_url": "https://aira-openai-dev.openai.azure.com/    ",
            "api_key": "EG1uazO0jiGj18BYA75kZu0WsYB690W0mHvBVUrefExzKCFudio6JQQJ99BFACYeBjFXJ3w3AAABACOG2skg",
            "deployment_name": "text-embedding-3-large",
            "api_type": "azure"
        }
    },

    "llms": {
        "azure": {
            "api_key": "EG1uazO0jiGj18BYA75kZu0WsYB690W0mHvBVUrefExzKCFudio6JQQJ99BFACYeBjFXJ3w3AAABACOG2skg",
            "model": "gpt-4o",
            "base_url": "https://aira-openai-dev.openai.azure.com/    ",
            "api_type": "azure",
            "deployment_name": "gpt-4o",
            "model_version": "2025-01-01-preview"
        }
    },

    "generation": {
        "max_results":3,
        "temperature": 0.4,
        "max_tokens": 2048
    },

    "langsmith": {
        "enable_tracing": True,
        "endpoint": "https://api.smith.langchain.com    ",
        "api_key": "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",
        "project": "default"
    },

    "logging": {
        "level": "INFO"
    },

    "env_vars": {
        "MODEL_NAME": "papluca/xlm-roberta-base-language-detection",
        "HF_TOKEN": "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"
    }
}

# -------------------------
# LOGGING SETUP
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# -------------------------
# CONFIG LOADER CLASS
# -------------------------
class ConfigLoader:
    def __init__(self, config_dict=None):
        self.config = config_dict or CONFIG

    def get(self, *keys, default=None):
        cfg = self.config
        for key in keys:
            if isinstance(cfg, dict) and key in cfg:
                cfg = cfg[key]
            else:
                return default
        return cfg

# -------------------------
# CONFIG CLASS
# -------------------------

class Config:
    DB_USER =  'airadbuser'
    DB_PASSWORD = 'Password123'
    DB_HOST = '10.134.44.228'
    DB_PORT = 5432
    DB_NAME = 'pfasdb'

    # Allow DATABASE_URL override for containerized/local setups
    _default_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    _env_uri = os.environ.get('DATABASE_URL')
    if _env_uri and _env_uri.startswith('postgresql'):
        SQLALCHEMY_DATABASE_URI = _env_uri
    else:
        SQLALCHEMY_DATABASE_URI = _default_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
# -------------------------
# UTILITY FUNCTIONS
# -------------------------
def get_config():
    return CONFIG

def get_config_loader():
    return ConfigLoader(CONFIG)