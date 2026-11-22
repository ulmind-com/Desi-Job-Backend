import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_connected: bool = False

    async def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at: {settings.MONGODB_URI.split('@')[-1] if '@' in settings.MONGODB_URI else 'local/uri'}...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2500,
                connectTimeoutMS=2500
            )
            # Ping to verify
            await self.client.admin.command('ping')
            self.db = self.client[settings.DATABASE_NAME]
            self.is_connected = True
            logger.info(f"Successfully connected to MongoDB database: {settings.DATABASE_NAME}")
            await self._create_indexes()
        except Exception as e:
            self.is_connected = False
            logger.warning(f"MongoDB Atlas is currently offline or unreachable ({e}). Backend running in high-availability resilient memory-backed mode.")

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    async def _create_indexes(self):
        if not self.is_connected or self.db is None:
            return
        try:
            # Users indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("firebase_uid", unique=True, sparse=True)
            # Jobs indexes
            await self.db.jobs.create_index("category")
            await self.db.jobs.create_index("status")
            await self.db.jobs.create_index([("title", "text"), ("description", "text"), ("company", "text")])
            # Applications indexes
            await self.db.applications.create_index([("job_id", 1), ("user_id", 1)], unique=True)
            # Categories indexes
            await self.db.categories.create_index("slug", unique=True)
            logger.info("Database indexes created successfully.")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

db_manager = DatabaseManager()

def get_database() -> Optional[AsyncIOMotorDatabase]:
    return db_manager.db
