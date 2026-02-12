"""
MongoDB Vector Database Manager for storing and retrieving ranking data
"""
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
import numpy as np
from datetime import datetime
from config.settings import settings


class VectorDB:
    """MongoDB Vector Database Manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db_name]
        
        # Create indexes
        await self.db.rankings.create_index([("query_id", ASCENDING)])
        await self.db.rankings.create_index([("created_at", DESCENDING)])
        await self.db.entities.create_index([("name", ASCENDING)])
        await self.db.metrics.create_index([("entity_id", ASCENDING)])
        
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
    
    async def store_ranking(self, ranking_data: Dict[str, Any]) -> str:
        """
        Store a complete ranking result
        
        Args:
            ranking_data: Dictionary containing ranking information
            
        Returns:
            str: ID of the stored ranking
        """
        ranking_data["created_at"] = datetime.utcnow()
        result = await self.db.rankings.insert_one(ranking_data)
        return str(result.inserted_id)
    
    async def get_ranking(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a ranking by query ID"""
        return await self.db.rankings.find_one({"query_id": query_id})
    
    async def store_entity(self, entity_data: Dict[str, Any]) -> str:
        """Store entity information"""
        entity_data["updated_at"] = datetime.utcnow()
        result = await self.db.entities.insert_one(entity_data)
        return str(result.inserted_id)
    
    async def update_entity_metrics(self, entity_id: str, metrics: Dict[str, Any]):
        """Update metrics for an entity"""
        metric_doc = {
            "entity_id": entity_id,
            "metrics": metrics,
            "timestamp": datetime.utcnow()
        }
        await self.db.metrics.insert_one(metric_doc)
    
    async def get_entity_metrics(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for an entity"""
        cursor = self.db.metrics.find({"entity_id": entity_id}).sort("timestamp", DESCENDING)
        return await cursor.to_list(length=100)
    
    async def store_crawled_data(self, url: str, content: str, metadata: Dict[str, Any]):
        """Store crawled web data"""
        doc = {
            "url": url,
            "content": content,
            "metadata": metadata,
            "crawled_at": datetime.utcnow()
        }
        await self.db.crawled_data.insert_one(doc)
    
    async def get_crawled_data(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Retrieve crawled data for given URLs"""
        cursor = self.db.crawled_data.find({"url": {"$in": urls}})
        return await cursor.to_list(length=None)
    
    async def store_knowledge_base(self, knowledge: Dict[str, Any]):
        """Store knowledge base information"""
        knowledge["created_at"] = datetime.utcnow()
        await self.db.knowledge_base.insert_one(knowledge)
    
    async def query_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query knowledge base (simple text search for now)"""
        cursor = self.db.knowledge_base.find(
            {"$text": {"$search": query}}
        ).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_recent_rankings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent rankings"""
        cursor = self.db.rankings.find().sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)


# Global instance
vector_db = VectorDB()
