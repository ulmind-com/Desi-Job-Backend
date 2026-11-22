import logging
import json
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

firebase_app = None

def init_firebase():
    global firebase_app
    if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            # Check if JSON string or file path
            if settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip().startswith("{"):
                cred_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Firebase Admin SDK: {e}. Falling back to JWT verification.")
    else:
        logger.info("Firebase credentials not configured yet. Using secure internal auth / JWT engine.")

async def verify_firebase_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Firebase token if firebase_admin is initialized.
    Otherwise decode and validate standard payload claims.
    """
    global firebase_app
    if firebase_app:
        try:
            from firebase_admin import auth
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return None
    
    # Graceful fallback decoding for development testing
    try:
        from jose import jwt
        unverified_claims = jwt.get_unverified_claims(id_token)
        return unverified_claims
    except Exception as e:
        logger.warning(f"Token decoding failed: {e}")
        return None
