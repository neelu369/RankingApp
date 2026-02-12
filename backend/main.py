"""
FastAPI Backend for Ranking App - With Optimization
"""
import sys
from pathlib import Path

# Add the parent directory to Python path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(project_dir))

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import io
from datetime import datetime
import uuid

from agent import ranking_agent
from llm_interface import ranking_llm
from ranking_engine import ranking_engine
from vector_db import vector_db
from crawler import crawler
from ranking_optimizer import get_optimizer  # NEW
from token_tracking import token_tracker

app = FastAPI(title="Universal Ranking App", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class RankingQuery(BaseModel):
    query: str
    num_results: int = 10
    metrics: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[str]] = None
    entities: Optional[List[Dict[str, Any]]] = None


class DatasetRankingRequest(BaseModel):
    metrics: Optional[List[Dict[str, Any]]] = None
    weights: Optional[Dict[str, float]] = None
    sources: Optional[List[str]] = None


class InsightRequest(BaseModel):
    entity_name: str
    ranking_id: str


class RerankRequest(BaseModel):
    ranking_id: str
    updated_metrics: Dict[str, Dict[str, Any]]


# NEW: Optimization request model
class OptimizationRequest(BaseModel):
    ranking_id: str
    ground_truth: Optional[List[str]] = None  # Optional ideal rankings for better metrics


# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    print("\n" + "="*60)
    print("STARTING RANKING APP WITH OPTIMIZATION")
    print("="*60)
    
    # Check environment variables
    from config.settings import settings
    print(f"\nConfiguration Check:")
    print(f"  Replicate API Key: {'✓ Set' if settings.replicate_api_key else '✗ NOT SET'}")
    print(f"  OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ NOT SET'}")
    print(f"  MongoDB URI: {settings.mongodb_uri}")
    print(f"  Default LLM Model: {settings.default_llm_model}")
    
    # Connect to MongoDB
    print(f"\nConnecting to MongoDB...")
    try:
        await vector_db.connect()
        print("✓ MongoDB connected successfully")
    except Exception as e:
        print(f"✗ MongoDB connection failed: {str(e)}")
        print("  The app will still run but won't persist data")
    
    # Initialize optimizer
    print(f"\nInitializing ranking optimizer...")
    try:
        optimizer = get_optimizer(ranking_engine)
        print("✓ Ranking optimizer ready")
    except Exception as e:
        print(f"✗ Optimizer initialization warning: {str(e)}")
    
    print("\n" + "="*60)
    print("APP READY - Listening on http://localhost:8000")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    print("\nShutting down...")
    await vector_db.disconnect()
    print("Goodbye!")


# Routes
@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy", 
        "app": "Universal Ranking App",
        "features": ["ranking", "optimization", "insights"]
    }


@app.post("/api/rank/crawler")
async def rank_by_crawler(request: RankingQuery):
    try:
        metrics = request.metrics
        sources = [{"url": url} for url in request.sources] if request.sources else None
        entities = request.entities

        result = await ranking_agent.run(
            query=request.query,
            query_type="crawler",
            entities=entities,
            metrics=metrics,
            sources=sources
        )

        ranking_id = result.get("query_id") or str(uuid.uuid4())

        # Store for insights (now includes optimization report)
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "crawler",
            "query": request.query,
            "metrics": result["metrics"],
            "ranking": result["ranking"],
            "optimization": result.get("optimization", {}),  # NEW
            "created_at": datetime.utcnow().isoformat()
        })

        return {
            "success": True,
            "ranking_id": ranking_id,
            "query": request.query,
            "ranking": result["ranking"],
            "intent": result["intent"],
            "metrics_used": result["metrics"],
            "optimization": result.get("optimization", {})  # NEW
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rank/dataset")
async def rank_dataset(
    file: UploadFile = File(...),
    request_data: str = Body(...)
):
    try:
        print("=== /api/rank/dataset called ===")

        # Parse request
        import json
        req = json.loads(request_data)
        top_k = req.get("top_k", 10)
        request = DatasetRankingRequest(**req)

        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        # Find entity column
        entity_column = None
        possible_names = ["name", "entity", "customer", "company", "material", "employee"]

        for col in df.columns:
            if col.lower() in possible_names:
                entity_column = col
                break

        if entity_column is None:
            entity_column = df.columns[0]

        df = df.rename(columns={entity_column: "entity"})

        # Convert to entities
        entities = df.to_dict("records")

        # Determine metrics
        if request.metrics:
            metrics = request.metrics
        else:
            metrics = []
            for col in df.columns:
                if col.lower() not in ["name", "id", "entity"]:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        metric_type = "numerical"
                    else:
                        metric_type = "categorical"

                    metrics.append({
                        "name": col,
                        "type": metric_type,
                        "higher_is_better": True
                    })

        # Ranking
        weights = request.weights if request.weights else {m["name"]: 1.0/len(metrics) for m in metrics}
        
        ranking = ranking_engine.rank_entities(
            entities=entities,
            metrics=metrics,
            weights=weights
        )
        ranking = ranking[:top_k]

        # NEW: Run optimization analysis
        optimizer = get_optimizer(ranking_engine)
        optimization_result = optimizer.analyze_and_optimize(
            rankings=ranking,
            metrics=metrics,
            current_weights=weights,
            ground_truth=None
        )

        # Use optimized rankings if available
        if optimization_result.get("optimized_rankings"):
            final_ranking = optimization_result["optimized_rankings"][:top_k]
        else:
            final_ranking = ranking

        # Store in DB
        ranking_id = str(uuid.uuid4())
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "dataset",
            "metrics": metrics,
            "ranking": final_ranking,
            "optimization": {
                "applied": optimization_result.get("should_optimize", False),
                "report": optimization_result.get("analysis", {})
            }
        })

        return {
            "success": True,
            "ranking_id": ranking_id,
            "ranking": final_ranking,
            "metrics_used": metrics,
            "optimization": {  # NEW
                "applied": optimization_result.get("should_optimize", False),
                "report": optimization_result.get("analysis", {}),
                "weight_changes": optimization_result.get("weight_changes", {})
            }
        }

    except Exception as e:
        print("❌ ERROR in /api/rank/dataset:", repr(e))
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# NEW: Optimization endpoint
@app.post("/api/optimize")
async def optimize_ranking(request: OptimizationRequest):
    """
    Analyze and optimize an existing ranking
    """
    try:
        # Retrieve ranking from database
        ranking_data = await vector_db.get_ranking(request.ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        rankings = ranking_data.get("ranking", [])
        metrics = ranking_data.get("metrics", [])
        
        if not rankings or not metrics:
            raise HTTPException(status_code=400, detail="Invalid ranking data")
        
        # Extract current weights (if stored) or create defaults
        weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        
        # Run optimization
        optimizer = get_optimizer(ranking_engine)
        result = optimizer.analyze_and_optimize(
            rankings=rankings,
            metrics=metrics,
            current_weights=weights,
            ground_truth=request.ground_truth
        )
        
        # Store optimized ranking if created
        if result.get("optimized_rankings"):
            new_ranking_id = str(uuid.uuid4())
            await vector_db.store_ranking({
                "ranking_id": new_ranking_id,
                "query_id": request.ranking_id,
                "type": "optimized",
                "metrics": metrics,
                "ranking": result["optimized_rankings"],
                "previous_ranking_id": request.ranking_id,
                "optimization": {
                    "applied": True,
                    "report": result["analysis"]
                }
            })
            
            return {
                "success": True,
                "optimized_ranking_id": new_ranking_id,
                "original_ranking_id": request.ranking_id,
                "optimization_report": result["analysis"],
                "optimized_rankings": result["optimized_rankings"],
                "weight_changes": result.get("weight_changes", {}),
                "current_metrics": result.get("current_metrics", {})
            }
        else:
            return {
                "success": True,
                "message": "Rankings are already optimal",
                "optimization_report": result["analysis"],
                "current_metrics": result.get("current_metrics", {})
            }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# NEW: Get optimization history
@app.get("/api/optimization/history")
async def get_optimization_history(limit: int = 10):
    """
    Get history of optimizations performed
    """
    try:
        optimizer = get_optimizer(ranking_engine)
        history = optimizer.metrics_history[-limit:]
        
        return {
            "success": True,
            "history": history,
            "total_optimizations": len(optimizer.metrics_history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/insights")
async def get_insights(request: InsightRequest):
    """
    Get insights for a specific entity in the ranking
    """
    try:
        # Retrieve ranking from database
        ranking_data = await vector_db.get_ranking(request.ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        # Find the entity
        ranking = ranking_data.get("ranking", [])
        entity = next(
            (
                e for e in ranking
                if e.get("name") == request.entity_name
                or e.get("entity") == request.entity_name
                or e.get("title") == request.entity_name
            ),
            None
        )
        
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        # Extract metrics
        metrics = {k: v for k, v in entity.items() 
                  if k not in ["rank", "final_score", "name"] and not k.endswith("_normalized")}
        
        # Generate insights using LLM
        context = {
            "total_entities": len(ranking),
            "top_entity": ranking[0].get("name") if ranking else None,
            "optimization_applied": ranking_data.get("optimization", {}).get("applied", False)
        }
        
        insights = await ranking_llm.generate_insight(
            entity_name=request.entity_name,
            metrics=metrics,
            rank=entity.get("rank", 0),
            context=context
        )
        
        return {
            "success": True,
            "entity": request.entity_name,
            "rank": entity.get("rank"),
            "metrics": metrics,
            "insights": insights,
            "optimization_info": ranking_data.get("optimization", {})  # NEW
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rerank")
async def rerank_entities(request: RerankRequest):
    """
    Rerank entities with updated metrics
    """
    try:
        # Retrieve current ranking
        ranking_data = await vector_db.get_ranking(request.ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        current_ranking = ranking_data.get("ranking", [])
        metrics = ranking_data.get("metrics", [])
        
        # Rerank with updated metrics
        new_ranking, changes = ranking_engine.rerank(
            current_ranking=current_ranking,
            updated_metrics=request.updated_metrics,
            metric_definitions=metrics
        )
        
        # NEW: Analyze new ranking quality
        optimizer = get_optimizer(ranking_engine)
        weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        optimization_result = optimizer.analyze_and_optimize(
            rankings=new_ranking,
            metrics=metrics,
            current_weights=weights
        )
        
        # Store new ranking
        new_ranking_id = str(uuid.uuid4())
        await vector_db.store_ranking({
            "ranking_id": new_ranking_id,
            "query_id": request.ranking_id,
            "type": "rerank",
            "metrics": metrics,
            "ranking": new_ranking,
            "previous_ranking_id": request.ranking_id,
            "optimization": {
                "report": optimization_result.get("analysis", {})
            }
        })
        
        return {
            "success": True,
            "new_ranking_id": new_ranking_id,
            "ranking": new_ranking,
            "changes": changes,
            "optimization_report": optimization_result.get("analysis", {})  # NEW
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rankings/recent")
async def get_recent_rankings(limit: int = 10):
    """Get recent rankings"""
    try:
        rankings = await vector_db.get_recent_rankings(limit)
        return {
            "success": True,
            "rankings": rankings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/suggest/metrics")
async def suggest_metrics(entity_type: str, domain: str):
    """Suggest metrics for a given entity type and domain"""
    try:
        metrics = await ranking_llm.suggest_metrics(entity_type, domain)
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview")
async def preview_query(body: Dict[str, Any]):
    """
    Preview a query: return suggested intent, suggested metrics and suggested entities
    """
    try:
        query = body.get("query")
        num_results = int(body.get("num_results", 10))

        # Extract intent
        intent = await ranking_llm.extract_ranking_intent(query)

        # Determine entity_type and domain fallbacks
        entity_type = intent.get("entity_type", "entity")
        domain = intent.get("domain", "general")

        # Suggest metrics
        metrics = await ranking_llm.suggest_metrics(entity_type=entity_type, domain=domain, context=query)

        # Suggest entities
        entities = await ranking_llm.suggest_entities(query=query, number=num_results)

        return {
            "success": True,
            "query": query,
            "intent": intent,
            "metrics": metrics,
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
async def compare_entities(
    ranking_id: str,
    entity1: str,
    entity2: str
):
    """Compare two entities from a ranking"""
    try:
        # Retrieve ranking
        ranking_data = await vector_db.get_ranking(ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        ranking = ranking_data.get("ranking", [])
        metrics = ranking_data.get("metrics", [])
        
        # Find entities
        e1 = next((e for e in ranking if e.get("name") == entity1), None)
        e2 = next((e for e in ranking if e.get("name") == entity2), None)
        
        if not e1 or not e2:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        # Compare
        metric_names = [m["name"] for m in metrics]
        comparison = ranking_engine.compare_entities(e1, e2, metric_names)
        
        return { 
            "success": True,
            "comparison": comparison
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/token-usage")
async def get_token_usage():
    """Get current token usage and budget status"""
    try:
        summary = token_tracker.get_summary()
        
        return {
            "success": True,
            "budget": {
                "total_usd": summary["budget_usd"],
                "spent_usd": summary["spent_usd"],
                "remaining_usd": summary["remaining_usd"],
                "percent_used": summary["percent_used"]
            },
            "tokens": {
                "input": summary["total_input_tokens"],
                "output": summary["total_output_tokens"],
                "total": summary["total_tokens"]
            },
            "requests": {
                "total": summary["total_requests"]
            },
            "models": summary["models_used"],
            "timeline": {
                "started_at": summary["started_at"],
                "last_updated": summary["last_updated"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/token-usage/reset")
async def reset_token_usage():
    """Reset token usage tracking (admin only)"""
    try:
        token_tracker.reset()
        return {
            "success": True,
            "message": "Token usage tracking has been reset"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/token-usage/can-proceed")
async def can_proceed_with_request(estimated_tokens: int = 2000):
    """Check if there's budget for another request"""
    try:
        can_proceed = token_tracker.can_make_request(estimated_tokens)
        remaining = token_tracker.get_remaining_budget()
        
        return {
            "success": True,
            "can_proceed": can_proceed,
            "remaining_budget_usd": remaining,
            "estimated_cost_usd": (estimated_tokens // 2 * 0.00065 / 1000) + (estimated_tokens // 2 * 0.00275 / 1000)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add this to your startup event in main.py:
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    print("\n" + "="*60)
    print("STARTING RANKING APP WITH TOKEN TRACKING")
    print("="*60)
    
    # ... existing startup code ...
    
    # Print initial token status
    print("\n💰 Token Budget Status:")
    token_tracker.print_status()
    
    print("\n" + "="*60)
    print("APP READY")
    print("="*60 + "\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)