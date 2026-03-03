"""
Token Usage Tracking System
Stores token usage in MongoDB and tracks budget
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os


class TokenTracker:
    """Track and store LLM token usage"""
    
    def __init__(self):
        self.collection = None  # Will be set when DB connects
        
        # Pricing per 1M tokens (adjust based on your provider)
        self.pricing = {
            "replicate": {
                "meta-llama-3-70b": {
                    "input": 0.65,   # $0.65 per 1M input tokens
                    "output": 2.75   # $2.75 per 1M output tokens
                },
                "meta-llama-3.1-405b": {
                    "input": 5.00,
                    "output": 15.00
                }
            },
            "openai": {
                "gpt-4": {
                    "input": 30.00,
                    "output": 60.00
                },
                "gpt-3.5-turbo": {
                    "input": 0.50,
                    "output": 1.50
                }
            }
        }
        
        # Budget settings (in dollars)
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET", "3.0"))
        self.warning_threshold = 0.8  # Warn at 80% usage
        self.critical_threshold = 0.95  # Critical at 95% usage
    
    async def connect(self, db):
        """Connect to MongoDB collection"""
        self.collection = db.token_usage
        # Create indexes
        await self.collection.create_index([("timestamp", -1)])
        await self.collection.create_index([("query_id", 1)])
        await self.collection.create_index([("date", 1)])
    
    async def track_usage(
        self,
        query_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track token usage for a single operation
        
        Args:
            query_id: ID of the query/ranking
            provider: "replicate", "openai", etc.
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            operation: Type of operation (e.g., "intent_extraction", "metric_suggestion")
            metadata: Additional info
            
        Returns:
            Usage record with cost
        """
        # Calculate cost
        cost = self._calculate_cost(provider, model, input_tokens, output_tokens)
        
        # Create record
        record = {
            "query_id": query_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "operation": operation,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
            "date": datetime.utcnow().strftime("%Y-%m-%d")
        }
        
        # Store in database
        if self.collection is not None:
            await self.collection.insert_one(record)
        
        return record
    
    def _calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD"""
        try:
            pricing = self.pricing.get(provider, {}).get(model, {})
            if not pricing:
                # Unknown model, estimate
                return (input_tokens + output_tokens) / 1_000_000 * 1.0
            
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            
            return round(input_cost + output_cost, 6)
        except Exception as e:
            print(f"Error calculating cost: {e}")
            return 0.0
    
    async def get_usage_summary(
        self,
        period: str = "today"  # "today", "week", "month", "all"
    ) -> Dict[str, Any]:
        """
        Get usage summary for a time period
        
        Returns:
            Summary with tokens, cost, budget info
        """
        # Determine date range
        now = datetime.utcnow()
        
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # "all"
            start_date = datetime(2020, 1, 1)
        
        # Query database
        if self.collection is None:
            return self._get_empty_summary()
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_input_tokens": {"$sum": "$input_tokens"},
                    "total_output_tokens": {"$sum": "$output_tokens"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$cost_usd"},
                    "query_count": {"$sum": 1}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return self._get_empty_summary()
        
        data = result[0]
        
        # Calculate budget info
        budget_used = data["total_cost"]
        budget_remaining = max(0, self.monthly_budget - budget_used)
        budget_percentage = (budget_used / self.monthly_budget * 100) if self.monthly_budget > 0 else 0
        
        # Determine status
        if budget_percentage >= self.critical_threshold * 100:
            status = "critical"
        elif budget_percentage >= self.warning_threshold * 100:
            status = "warning"
        else:
            status = "normal"
        
        return {
            "period": period,
            "tokens": {
                "input": data["total_input_tokens"],
                "output": data["total_output_tokens"],
                "total": data["total_tokens"]
            },
            "cost": {
                "total": round(data["total_cost"], 2),
                "currency": "USD"
            },
            "budget": {
                "monthly_limit": self.monthly_budget,
                "used": round(budget_used, 2),
                "remaining": round(budget_remaining, 2),
                "percentage": round(budget_percentage, 1),
                "status": status
            },
            "queries": data["query_count"],
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat()
        }
    
    def _get_empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data"""
        return {
            "period": "today",
            "tokens": {"input": 0, "output": 0, "total": 0},
            "cost": {"total": 0.0, "currency": "USD"},
            "budget": {
                "monthly_limit": self.monthly_budget,
                "used": 0.0,
                "remaining": self.monthly_budget,
                "percentage": 0.0,
                "status": "normal"
            },
            "queries": 0,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    
    async def get_usage_by_operation(
        self,
        period: str = "month"
    ) -> Dict[str, Any]:
        """Get token usage breakdown by operation type"""
        now = datetime.utcnow()
        
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # "month"
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if self.collection is None:
            return {}
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$operation",
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$cost_usd"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"total_cost": -1}
            }
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        breakdown = {}
        for item in results:
            breakdown[item["_id"]] = {
                "tokens": item["total_tokens"],
                "cost": round(item["total_cost"], 4),
                "calls": item["count"]
            }
        
        return breakdown
    
    async def get_daily_usage(self, days: int = 30) -> list:
        """Get daily usage for the last N days"""
        if self.collection is None:
            return []
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$cost_usd"},
                    "queries": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=days)
        
        return [
            {
                "date": item["_id"],
                "tokens": item["total_tokens"],
                "cost": round(item["total_cost"], 4),
                "queries": item["queries"]
            }
            for item in results
        ]
    
    async def check_budget_exceeded(self) -> Dict[str, Any]:
        """Check if budget is exceeded or near limit"""
        summary = await self.get_usage_summary("month")
        budget = summary["budget"]
        
        return {
            "exceeded": budget["percentage"] >= 100,
            "near_limit": budget["percentage"] >= self.warning_threshold * 100,
            "critical": budget["percentage"] >= self.critical_threshold * 100,
            "percentage": budget["percentage"],
            "used": budget["used"],
            "remaining": budget["remaining"],
            "status": budget["status"]
        }


# Global instance
token_tracker = TokenTracker()