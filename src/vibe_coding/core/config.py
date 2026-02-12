"""
Configuration for the project.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """
    Project settings loaded from environment with local defaults.
    """

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Vibe Coding Data Science Template")


settings = Settings()
