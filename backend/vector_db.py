"""
MongoDB Vector Database Manager for storing and retrieving ranking data
"""
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import numpy as np
from datetime import datetime
from config.settings import settings


class VectorDB:
    """MongoDB Vector Database Manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.connected = False
        
    async def connect(self):
        """Connect to MongoDB with detailed error reporting"""
        try:
            print(f"\n🔌 Attempting MongoDB connection...")
            print(f"   URI: {self._mask_uri(settings.mongodb_uri)}")
            print(f"   Database: {settings.mongodb_db_name}")
            
            # Create client with shorter timeout for faster feedback
            self.client = AsyncIOMotorClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[settings.mongodb_db_name]
            
            # Create indexes
            print(f"   Creating indexes...")
            await self.db.rankings.create_index([("query_id", ASCENDING)])
            await self.db.rankings.create_index([("ranking_id", ASCENDING)])
            await self.db.rankings.create_index([("created_at", DESCENDING)])
            await self.db.entities.create_index([("name", ASCENDING)])
            await self.db.metrics.create_index([("entity_id", ASCENDING)])
            
            self.connected = True
            print(f"   ✓ MongoDB connected successfully!")
            return True
            
        except ServerSelectionTimeoutError as e:
            print(f"   ✗ MongoDB connection timeout")
            print(f"     Error: Could not reach MongoDB server")
            print(f"     Possible causes:")
            print(f"       - Network connectivity issues")
            print(f"       - Firewall blocking connection")
            print(f"       - Invalid MongoDB URI")
            print(f"       - MongoDB server is down")
            self.connected = False
            return False
            
        except ConnectionFailure as e:
            print(f"   ✗ MongoDB connection failed")
            print(f"     Error: {str(e)}")
            print(f"     Possible causes:")
            print(f"       - Invalid credentials")
            print(f"       - Database doesn't exist")
            print(f"       - Insufficient permissions")
            self.connected = False
            return False
            
        except Exception as e:
            print(f"   ✗ MongoDB connection error")
            print(f"     Error: {str(e)}")
            print(f"     Type: {type(e).__name__}")
            self.connected = False
            return False
    
    def _mask_uri(self, uri: str) -> str:
        """Mask sensitive parts of MongoDB URI for logging"""
        if '@' in uri:
            # mongodb+srv://user:pass@host/db -> mongodb+srv://***:***@host/db
            parts = uri.split('@')
            if '://' in parts[0]:
                protocol = parts[0].split('://')[0]
                return f"{protocol}://***:***@{parts[1]}"
        return uri
        
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            print("👋 MongoDB disconnected")
    
    async def store_ranking(self, ranking_data: Dict[str, Any]) -> str:
        """
        Store a complete ranking result
        
        Args:
            ranking_data: Dictionary containing ranking information
            
        Returns:
            str: ID of the stored ranking
        """
        if not self.connected:
            print("⚠️ Warning: Cannot store ranking - MongoDB not connected")
            return "not_stored"
            
        try:
            ranking_data["created_at"] = datetime.utcnow()
            result = await self.db.rankings.insert_one(ranking_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error storing ranking: {e}")
            return "error"
    
    async def get_ranking(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a ranking by query ID or ranking ID"""
        if not self.connected:
            return None
            
        try:
            # Try query_id first
            result = await self.db.rankings.find_one({"query_id": query_id})
            if result:
                return result
            # Try ranking_id as fallback
            result = await self.db.rankings.find_one({"ranking_id": query_id})
            return result
        except Exception as e:
            print(f"❌ Error retrieving ranking: {e}")
            return None
    
    async def store_entity(self, entity_data: Dict[str, Any]) -> str:
        """Store entity information"""
        if not self.connected:
            return "not_stored"
            
        try:
            entity_data["updated_at"] = datetime.utcnow()
            result = await self.db.entities.insert_one(entity_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error storing entity: {e}")
            return "error"
    
    async def update_entity_metrics(self, entity_id: str, metrics: Dict[str, Any]):
        """Update metrics for an entity"""
        if not self.connected:
            return
            
        try:
            metric_doc = {
                "entity_id": entity_id,
                "metrics": metrics,
                "timestamp": datetime.utcnow()
            }
            await self.db.metrics.insert_one(metric_doc)
        except Exception as e:
            print(f"❌ Error updating entity metrics: {e}")
    
    async def get_entity_metrics(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for an entity"""
        if not self.connected:
            return []
            
        try:
            cursor = self.db.metrics.find({"entity_id": entity_id}).sort("timestamp", DESCENDING)
            return await cursor.to_list(length=100)
        except Exception as e:
            print(f"❌ Error getting entity metrics: {e}")
            return []
    
    async def store_crawled_data(self, url: str, content: str, metadata: Dict[str, Any]):
        """Store crawled web data"""
        if not self.connected:
            return
            
        try:
            doc = {
                "url": url,
                "content": content,
                "metadata": metadata,
                "crawled_at": datetime.utcnow()
            }
            await self.db.crawled_data.insert_one(doc)
        except Exception as e:
            print(f"❌ Error storing crawled data: {e}")
    
    async def get_crawled_data(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Retrieve crawled data for given URLs"""
        if not self.connected:
            return []
            
        try:
            cursor = self.db.crawled_data.find({"url": {"$in": urls}})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"❌ Error getting crawled data: {e}")
            return []
    
    async def store_knowledge_base(self, knowledge: Dict[str, Any]):
        """Store knowledge base information"""
        if not self.connected:
            return
            
        try:
            knowledge["created_at"] = datetime.utcnow()
            await self.db.knowledge_base.insert_one(knowledge)
        except Exception as e:
            print(f"❌ Error storing knowledge: {e}")
    
    async def query_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query knowledge base (simple text search for now)"""
        if not self.connected:
            return []
            
        try:
            cursor = self.db.knowledge_base.find(
                {"$text": {"$search": query}}
            ).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"❌ Error querying knowledge base: {e}")
            return []
    
    async def get_recent_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent rankings"""
        if not self.connected:
            return []
            
        try:
            cursor = self.db.rankings.find().sort("created_at", DESCENDING).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"❌ Error getting recent rankings: {e}")
            return []


# Global instance
vector_db = VectorDB()