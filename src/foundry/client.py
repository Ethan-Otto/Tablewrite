"""FoundryVTT REST API client."""

import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for interacting with FoundryVTT via REST API."""

    def __init__(self, target: Literal["local", "forge"] = "local"):
        """
        Initialize FoundryVTT API client.

        Args:
            target: Target environment ('local' or 'forge')

        Raises:
            ValueError: If required environment variables are not set
        """
        self.target = target
        self.relay_url = os.getenv("FOUNDRY_RELAY_URL")

        if not self.relay_url:
            raise ValueError("FOUNDRY_RELAY_URL not set in environment")

        if target == "local":
            self.foundry_url = os.getenv("FOUNDRY_LOCAL_URL")
            self.api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_LOCAL_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_LOCAL_API_KEY not set in environment")
        elif target == "forge":
            self.foundry_url = os.getenv("FOUNDRY_FORGE_URL")
            self.api_key = os.getenv("FOUNDRY_FORGE_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_FORGE_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_FORGE_API_KEY not set in environment")
        else:
            raise ValueError(f"Invalid target: {target}. Must be 'local' or 'forge'")

        logger.info(f"Initialized FoundryClient for {target} at {self.foundry_url}")
