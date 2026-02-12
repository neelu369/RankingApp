"""
FastAPI Backend for Ranking App
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


# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    print("\n" + "="*60)
    print("STARTING RANKING APP")
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
    return {"status": "healthy", "app": "Universal Ranking App"}


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

        # ✅ STORE FOR INSIGHTS
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "crawler",
            "query": request.query,
            "metrics": result["metrics"],
            "ranking": result["ranking"],
            "created_at": datetime.utcnow().isoformat()
        })

        return {
            "success": True,
            "ranking_id": ranking_id,
            "query": request.query,
            "ranking": result["ranking"],
            "intent": result["intent"],
            "metrics_used": result["metrics"]
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

        # 1️⃣ Check file
        print("File received:", file.filename, file.content_type)

        # 2️⃣ Check raw request data
        print("Raw request_data:", request_data)

        # Parse request data
        import json
        req = json.loads(request_data)
        print("Parsed JSON:", req)

        top_k = req.get("top_k", 10)
        request = DatasetRankingRequest(**req)
        print("Request model created")

        # 3️⃣ Read CSV
        contents = await file.read()
        print("File size:", len(contents))

        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        entity_column = None
        possible_names = ["name", "entity", "customer", "company", "material", "employee"]

        for col in df.columns:
            if col.lower() in possible_names:
                entity_column = col
                break

        # Fallback: first column
        if entity_column is None:
            entity_column = df.columns[0]

        # Rename to standard "entity"
        df = df.rename(columns={entity_column: "entity"})


        print("CSV loaded. Shape:", df.shape)
        print("Columns:", df.columns.tolist())

        # Convert to list of dicts
        entities = df.to_dict("records")
        print("Entities count:", len(entities))

        # 4️⃣ Metrics
        if request.metrics:
            metrics = request.metrics
            print("Using provided metrics")
        else:
            print("Auto-detecting metrics")

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

        print("Metrics:", metrics)

        # 5️⃣ Ranking
        print("Calling ranking_engine...")
        ranking = ranking_engine.rank_entities(
            entities=entities,
            metrics=metrics,
            weights=request.weights
        )
        ranking = ranking[:top_k]


        print("Ranking complete")

        # 6️⃣ Store DB
        ranking_id = str(uuid.uuid4())

        print("Storing in vector DB...")
        await vector_db.store_ranking({
            "ranking_id": ranking_id,
            "query_id": ranking_id,
            "type": "dataset",
            "metrics": metrics,
            "ranking": ranking
        })

        print("Stored successfully:", ranking_id)

        return {
            "success": True,
            "ranking_id": ranking_id,
            "ranking": ranking,
            "metrics_used": metrics
        }

    except Exception as e:
        print("❌ ERROR in /api/rank/dataset:", repr(e))
        import traceback
        traceback.print_exc()

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
            "top_entity": ranking[0].get("name") if ranking else None
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
            "insights": insights
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
        
        # Store new ranking
        new_ranking_id = str(uuid.uuid4())
        await vector_db.store_ranking({
            "ranking_id": new_ranking_id,
            "query_id": request.ranking_id,
            "type": "rerank",
            "metrics": metrics,
            "ranking": new_ranking,
            "previous_ranking_id": request.ranking_id
        })
        
        return {
            "success": True,
            "new_ranking_id": new_ranking_id,
            "ranking": new_ranking,
            "changes": changes
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
    Body: {"query": str, "num_results": int}
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

        # Suggest entities (names/urls)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)