import json
import requests
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class StatusNotifier:
    """Client for sending status updates to the API server"""
    
    def __init__(self):
        self.api_url = os.environ.get('API_SERVER_URL', 'http://localhost:3000') # nodejs server api url
        self.api_key = os.environ.get('INTERNAL_API_KEY', 'development_key')
    
    def send_notification(self, file_id: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        print(f'will send_notification: {status}')
        """
        Send a status notification to the API server
        
        Args:
            file_id: The ID of the file being processed
            status: Current status (processing, completed, failed)
            metadata: Additional information about the status
            
        Returns:
            bool: Whether the notification was sent successfully
        """

        # Safely convert metadata to JSON-serializable format
        safe_metadata = self._sanitize_metadata(metadata or {})

        try:
            logger.info(f"Sending {status} notification for file {file_id}")
            print(f"API URL: {self.api_url}")

            response = requests.post(
                f"{self.api_url}/api/notifications/internal/notify",
                json={
                    "fileId": file_id,
                    "status": status,
                    "metadata": safe_metadata or {}
                },
                headers={
                    "Content-Type": "application/json",
                    "x-internal-api-key": self.api_key
                },
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Exception sending notification: {e}")
            return False
        
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure metadata is JSON-serializable
        
        Args:
            metadata: The metadata to sanitize
            
        Returns:
            Dict with JSON-safe values
        """
        safe_metadata = {}
        
        for key, value in metadata.items():
            # Skip None values
            if value is None:
                continue
                
            # Convert basic types directly
            if isinstance(value, (str, int, float, bool)):
                safe_metadata[key] = value
            # Convert lists and tuples if they contain basic types
            elif isinstance(value, (list, tuple)):
                try:
                    # Test if it's JSON serializable by encoding/decoding
                    json.dumps(value)
                    safe_metadata[key] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    safe_metadata[key] = str(value)
            # Convert dicts recursively
            elif isinstance(value, dict):
                safe_metadata[key] = self._sanitize_metadata(value)
            # Convert everything else to string
            else:
                safe_metadata[key] = str(value)
                
        return safe_metadata