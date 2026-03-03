"""
FastAPI Backend for Ranking App
Complete version with Optimization, Re-ranking, and Token Tracking
"""
import sys
from pathlib import Path

# Add the parent directory to Python path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(project_dir))

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from ranking_optimizer import get_optimizer
from token_tracking import token_tracker


app = FastAPI(title="Universal Ranking App", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== PYDANTIC MODELS ====================

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


class OptimizationRequest(BaseModel):
    ranking_id: str
    ground_truth: Optional[List[str]] = None


class CustomRerankRequest(BaseModel):
    ranking_id: str
    new_weights: Optional[Dict[str, float]] = None
    new_metrics: Optional[List[Dict[str, Any]]] = None


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    print("\n" + "="*60)
    print("STARTING UNIVERSAL RANKING APP v2.0")
    print("="*60)
    
    # Check environment variables
    from config.settings import settings
    print(f"\n📋 Configuration Check:")
    print(f"  Replicate API Key: {'✓ Set' if settings.replicate_api_key else '✗ NOT SET'}")
    print(f"  OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ NOT SET'}")
    print(f"  MongoDB URI: {settings.mongodb_uri}")
    print(f"  Default LLM Model: {settings.default_llm_model}")
    
    # Connect to MongoDB
    print(f"\n🔌 Connecting to MongoDB...")
    try:
        await vector_db.connect()
        print("✓ MongoDB connected successfully")
    except Exception as e:
        print(f"✗ MongoDB connection failed: {str(e)}")
        print("  The app will still run but won't persist data")
    
    # Initialize optimizer
    print(f"\n🔧 Initializing ranking optimizer...")
    try:
        optimizer = get_optimizer(ranking_engine)
        print("✓ Ranking optimizer ready")
    except Exception as e:
        print(f"✗ Optimizer initialization warning: {str(e)}")
    
    # Initialize token tracker
    print(f"\n💰 Initializing token tracker...")
    try:
        await token_tracker.connect(vector_db.db)
        print("✓ Token tracker initialized")
        # Print budget status
        summary = await token_tracker.get_usage_summary("month")
        print(f"  Monthly Budget: ${summary['budget']['monthly_limit']:.2f}")
        print(f"  Used: ${summary['budget']['used']:.2f} ({summary['budget']['percentage']:.1f}%)")
        print(f"  Remaining: ${summary['budget']['remaining']:.2f}")
    except Exception as e:
        print(f"✗ Token tracker initialization failed: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ APP READY - Listening on http://localhost:8000")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    print("\n👋 Shutting down...")
    await vector_db.disconnect()
    print("Goodbye!")


# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def check_budget_middleware(request, call_next):
    """Check if budget is exceeded before processing ranking requests"""
    
    # Only check for ranking endpoints
    if not request.url.path.startswith("/api/rank"):
        return await call_next(request)
    
    try:
        # Check budget
        budget_status = await token_tracker.check_budget_exceeded()
        
        if budget_status["exceeded"]:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Monthly token budget exceeded",
                    "budget": budget_status,
                    "message": f"You've used {budget_status['percentage']:.1f}% of your monthly budget"
                }
            )
        
        # Warn if near limit (but allow request)
        if budget_status["critical"]:
            print(f"⚠️ WARNING: Budget at {budget_status['percentage']:.1f}%")
        
    except Exception as e:
        print(f"Budget check error: {e}")
        # Don't block request if budget check fails
    
    response = await call_next(request)
    return response


# ==================== BASIC ROUTES ====================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy", 
        "app": "Universal Ranking App",
        "version": "2.0.0",
        "features": [
            "ranking", 
            "optimization", 
            "re-ranking",
            "insights",
            "token-tracking"
        ]
    }


# ==================== RANKING ENDPOINTS ====================

@app.post("/api/rank/crawler")
async def rank_by_crawler(request: RankingQuery):
    """Rank entities by crawling the web"""
    try:
        # Generate query ID
        query_id = str(uuid.uuid4())
        
        # Set query ID for token tracking
        ranking_llm.set_query_id(query_id)
        
        # Prepare request data
        metrics = request.metrics
        sources = [{"url": url} for url in request.sources] if request.sources else None
        entities = request.entities

        # Run ranking workflow
        result = await ranking_agent.run(
            query=request.query,
            query_type="crawler",
            entities=entities,
            metrics=metrics,
            sources=sources
        )

        ranking_id = result.get("query_id") or query_id

        # Store for insights
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "crawler",
            "query": request.query,
            "metrics": result["metrics"],
            "ranking": result["ranking"],
            "optimization": result.get("optimization", {}),
            "created_at": datetime.utcnow().isoformat()
        })

        return {
            "success": True,
            "ranking_id": ranking_id,
            "query": request.query,
            "ranking": result["ranking"],
            "intent": result["intent"],
            "metrics_used": result["metrics"],
            "optimization": result.get("optimization", {})
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rank/dataset")
async def rank_dataset(
    file: UploadFile = File(...),
    request_data: str = Body(...)
):
    """Rank entities from uploaded CSV dataset"""
    try:
        print("=== /api/rank/dataset called ===")

        # Generate query ID
        query_id = str(uuid.uuid4())
        
        # Set query ID for token tracking
        ranking_llm.set_query_id(query_id)

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

        # Run optimization analysis
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
        ranking_id = query_id
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "dataset",
            "metrics": metrics,
            "ranking": final_ranking,
            "weights": weights,
            "optimization": {
                "applied": optimization_result.get("should_optimize", False),
                "report": optimization_result.get("analysis", {})
            },
            "created_at": datetime.utcnow().isoformat()
        })

        return {
            "success": True,
            "ranking_id": ranking_id,
            "ranking": final_ranking,
            "metrics_used": metrics,
            "optimization": {
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


# ==================== OPTIMIZATION ENDPOINTS ====================

@app.post("/api/optimize")
async def optimize_ranking(request: OptimizationRequest):
    """
    Auto-optimize an existing ranking
    Analyzes quality and improves weights if needed
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
        weights = ranking_data.get("weights", {})
        if not weights:
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
                "weights": result.get("optimized_weights", weights),
                "previous_ranking_id": request.ranking_id,
                "optimization": {
                    "applied": True,
                    "report": result["analysis"]
                },
                "created_at": datetime.utcnow().isoformat()
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


@app.get("/api/optimization/history")
async def get_optimization_history(limit: int = 10):
    """Get history of optimizations performed"""
    try:
        optimizer = get_optimizer(ranking_engine)
        history = optimizer.metrics_history[-limit:] if optimizer.metrics_history else []
        
        return {
            "success": True,
            "history": history,
            "total_optimizations": len(optimizer.metrics_history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RE-RANKING ENDPOINTS ====================

@app.post("/api/rerank/custom")
async def rerank_custom(request: CustomRerankRequest):
    """
    Re-rank with custom user-provided weights and/or metrics
    Allows manual adjustment of weights and metrics
    """
    try:
        # Retrieve original ranking
        ranking_data = await vector_db.get_ranking(request.ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        # Get original data
        current_ranking = ranking_data.get("ranking", [])
        original_metrics = ranking_data.get("metrics", [])
        
        # Use new metrics if provided, otherwise keep original
        metrics_to_use = request.new_metrics if request.new_metrics else original_metrics
        
        # Validate and set weights
        if request.new_weights:
            total_weight = sum(request.new_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Weights must sum to 1.0 (got {total_weight:.3f})"
                )
            weights_to_use = request.new_weights
        else:
            # Create equal weights
            weights_to_use = {m["name"]: 1.0 / len(metrics_to_use) for m in metrics_to_use}
        
        # Extract entities (remove ranking-specific fields)
        entities = []
        for item in current_ranking:
            entity = {k: v for k, v in item.items() 
                     if k not in ["rank", "final_score"] and not k.endswith("_normalized")}
            entities.append(entity)
        
        # Re-rank with new weights/metrics
        print(f"Re-ranking with custom weights: {weights_to_use}")
        new_ranking = ranking_engine.rank_entities(
            entities=entities,
            metrics=metrics_to_use,
            weights=weights_to_use,
            normalization="minmax"
        )
        
        # Run optimization analysis on new ranking
        optimizer = get_optimizer(ranking_engine)
        optimization_result = optimizer.analyze_and_optimize(
            rankings=new_ranking,
            metrics=metrics_to_use,
            current_weights=weights_to_use,
            ground_truth=None
        )
        
        # Calculate changes from original ranking
        changes = []
        old_ranks = {item.get("name") or item.get("entity"): item.get("rank") 
                    for item in current_ranking}
        
        for item in new_ranking:
            entity_name = item.get("name") or item.get("entity")
            old_rank = old_ranks.get(entity_name)
            new_rank = item.get("rank")
            
            if old_rank and old_rank != new_rank:
                changes.append({
                    "entity": entity_name,
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                    "change": old_rank - new_rank,
                    "direction": "up" if new_rank < old_rank else "down"
                })
        
        # Store new ranking
        new_ranking_id = str(uuid.uuid4())
        await vector_db.store_ranking({
            "ranking_id": new_ranking_id,
            "query_id": request.ranking_id,
            "type": "custom_rerank",
            "metrics": metrics_to_use,
            "ranking": new_ranking,
            "weights": weights_to_use,
            "previous_ranking_id": request.ranking_id,
            "user_modified": True,
            "optimization": {
                "report": optimization_result.get("analysis", {})
            },
            "created_at": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "new_ranking_id": new_ranking_id,
            "ranking": new_ranking,
            "changes": changes,
            "weights_used": weights_to_use,
            "metrics_used": metrics_to_use,
            "optimization_report": optimization_result.get("analysis", {}),
            "message": f"Re-ranked successfully. {len(changes)} positions changed."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rerank/metrics")
async def rerank_with_new_metrics(request: RerankRequest):
    """
    Re-rank entities with updated metric VALUES (not weights)
    Use when you have new data for entities
    """
    try:
        # Retrieve current ranking
        ranking_data = await vector_db.get_ranking(request.ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        current_ranking = ranking_data.get("ranking", [])
        metrics = ranking_data.get("metrics", [])
        
        # Rerank with updated metric values
        new_ranking, changes = ranking_engine.rerank(
            current_ranking=current_ranking,
            updated_metrics=request.updated_metrics,
            metric_definitions=metrics
        )
        
        # Analyze new ranking quality
        optimizer = get_optimizer(ranking_engine)
        weights = ranking_data.get("weights", {})
        if not weights:
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
            "type": "rerank_metrics",
            "metrics": metrics,
            "ranking": new_ranking,
            "weights": weights,
            "previous_ranking_id": request.ranking_id,
            "optimization": {
                "report": optimization_result.get("analysis", {})
            },
            "created_at": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "new_ranking_id": new_ranking_id,
            "ranking": new_ranking,
            "changes": changes,
            "optimization_report": optimization_result.get("analysis", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/suggest/weight-adjustments")
async def suggest_weight_adjustments(ranking_id: str = Body(..., embed=True)):
    """
    Suggest optimal weight adjustments for a ranking
    Helps users understand what changes would improve rankings
    """
    try:
        # Retrieve ranking
        ranking_data = await vector_db.get_ranking(ranking_id)
        
        if not ranking_data:
            raise HTTPException(status_code=404, detail="Ranking not found")
        
        rankings = ranking_data.get("ranking", [])
        metrics = ranking_data.get("metrics", [])
        current_weights = ranking_data.get("weights", {})
        
        if not current_weights:
            # Create equal weights if not stored
            current_weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        
        # Run optimization to get suggestions
        optimizer = get_optimizer(ranking_engine)
        result = optimizer.analyze_and_optimize(
            rankings=rankings,
            metrics=metrics,
            current_weights=current_weights
        )
        
        suggestions = []
        
        # Add suggestions from optimization
        if result.get("suggested_actions"):
            for action in result["suggested_actions"]:
                suggestions.append({
                    "type": action.get("type"),
                    "metric": action.get("metric") or action.get("feature"),
                    "recommendation": action.get("recommendation"),
                    "priority": action.get("priority", 3)
                })
        
        # Add weight change suggestions if available
        weight_suggestions = {}
        if result.get("optimized_weights"):
            for feature, new_weight in result["optimized_weights"].items():
                old_weight = current_weights.get(feature, 0)
                if abs(new_weight - old_weight) > 0.01:
                    weight_suggestions[feature] = {
                        "current": round(old_weight, 3),
                        "suggested": round(new_weight, 3),
                        "change": round(new_weight - old_weight, 3),
                        "reason": "Optimization recommendation"
                    }
        
        return {
            "success": True,
            "current_weights": current_weights,
            "suggested_weights": result.get("optimized_weights"),
            "weight_suggestions": weight_suggestions,
            "general_suggestions": suggestions,
            "current_metrics": result.get("current_metrics", {}),
            "overall_health": result["analysis"]["overall_health"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INSIGHTS ENDPOINTS ====================

@app.post("/api/insights")
async def get_insights(request: InsightRequest):
    """Get AI-generated insights for a specific entity"""
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
                  if k not in ["rank", "final_score", "name", "entity"] and not k.endswith("_normalized")}
        
        # Generate insights using LLM
        context = {
            "total_entities": len(ranking),
            "top_entity": ranking[0].get("name") or ranking[0].get("entity") if ranking else None,
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
            "optimization_info": ranking_data.get("optimization", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
async def compare_entities(
    ranking_id: str = Body(...),
    entity1: str = Body(...),
    entity2: str = Body(...)
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
        e1 = next((e for e in ranking if (e.get("name") or e.get("entity")) == entity1), None)
        e2 = next((e for e in ranking if (e.get("name") or e.get("entity")) == entity2), None)
        
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


# ==================== UTILITY ENDPOINTS ====================

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
async def suggest_metrics(
    entity_type: str = Body(...),
    domain: str = Body(...)
):
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
    """Preview a query: return suggested intent, metrics and entities"""
    try:
        query = body.get("query")
        num_results = int(body.get("num_results", 10))

        # Extract intent
        intent = await ranking_llm.extract_ranking_intent(query)

        # Determine entity_type and domain
        entity_type = intent.get("entity_type", "entity")
        domain = intent.get("domain", "general")

        # Suggest metrics
        metrics = await ranking_llm.suggest_metrics(
            entity_type=entity_type, 
            domain=domain, 
            context=query
        )

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


# ==================== TOKEN TRACKING ENDPOINTS ====================

@app.get("/api/tokens/usage")
async def get_token_usage(period: str = "month"):
    """
    Get token usage summary
    
    Query params:
        period: "today", "week", "month", or "all"
    """
    try:
        summary = await token_tracker.get_usage_summary(period)
        return {
            "success": True,
            **summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tokens/breakdown")
async def get_token_breakdown(period: str = "month"):
    """
    Get token usage breakdown by operation type
    Shows which operations use the most tokens
    """
    try:
        breakdown = await token_tracker.get_usage_by_operation(period)
        return {
            "success": True,
            "period": period,
            "breakdown": breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tokens/daily")
async def get_daily_usage(days: int = 30):
    """
    Get daily token usage for the last N days
    
    Query params:
        days: Number of days to retrieve (default: 30, max: 90)
    """
    try:
        days = min(days, 90)  # Cap at 90 days
        daily_usage = await token_tracker.get_daily_usage(days)
        return {
            "success": True,
            "days": days,
            "usage": daily_usage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tokens/budget")
async def check_budget():
    """
    Check budget status
    Returns whether budget is exceeded, near limit, etc.
    """
    try:
        budget_status = await token_tracker.check_budget_exceeded()
        return {
            "success": True,
            **budget_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tokens/stats")
async def get_token_stats():
    """
    Get comprehensive token statistics
    Returns today's usage, monthly usage, budget status, etc.
    """
    try:
        today = await token_tracker.get_usage_summary("today")
        month = await token_tracker.get_usage_summary("month")
        breakdown = await token_tracker.get_usage_by_operation("month")
        daily = await token_tracker.get_daily_usage(7)
        budget = await token_tracker.check_budget_exceeded()
        
        return {
            "success": True,
            "today": today,
            "month": month,
            "breakdown": breakdown,
            "last_7_days": daily,
            "budget_status": budget
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)