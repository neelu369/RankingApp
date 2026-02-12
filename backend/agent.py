"""
LangGraph Agent for orchestrating ranking workflow
Manages the multi-step process of understanding queries, gathering data, ranking, and optimizing
"""
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
from llm_interface import ranking_llm
from crawler import crawler
from ranking_engine import ranking_engine
from vector_db import vector_db
from ranking_optimizer import get_optimizer


class RankingState(TypedDict):
    """State for the ranking agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    query_type: str  # "dataset" or "crawler"
    intent: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    ranking_result: List[Dict[str, Any]]
    # NEW: Optimization fields
    optimization_report: Dict[str, Any]
    optimized_rankings: List[Dict[str, Any]]
    used_optimization: bool
    feature_weights: Dict[str, float]
    error: str


class RankingAgent:
    """LangGraph-based agent for handling ranking requests with optimization"""
    
    def __init__(self):
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        # Initialize optimizer
        self.optimizer = get_optimizer(ranking_engine)
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(RankingState)
        
        # Add nodes
        workflow.add_node("understand_query", self.understand_query)
        workflow.add_node("determine_metrics", self.determine_metrics)
        workflow.add_node("identify_sources", self.identify_sources)
        workflow.add_node("gather_data", self.gather_data)
        workflow.add_node("normalize_data", self.normalize_data)
        workflow.add_node("compute_ranking", self.compute_ranking)
        workflow.add_node("optimize_ranking", self.optimize_ranking)  # NEW
        workflow.add_node("generate_insights", self.generate_insights)
        
        # Define edges - optimization added as post-processing step (Option 1)
        workflow.set_entry_point("understand_query")
        workflow.add_edge("understand_query", "determine_metrics")
        workflow.add_edge("determine_metrics", "identify_sources")
        workflow.add_edge("identify_sources", "gather_data")
        workflow.add_edge("gather_data", "normalize_data")
        workflow.add_edge("normalize_data", "compute_ranking")
        workflow.add_edge("compute_ranking", "optimize_ranking")  # NEW: Post-processing
        workflow.add_edge("optimize_ranking", "generate_insights")  # UPDATED
        workflow.add_edge("generate_insights", END)
        
        return workflow
    
    async def understand_query(self, state: RankingState) -> RankingState:
        """Understand the ranking query"""
        query = state["query"]
        
        print(f"Understanding query: {query}")
        
        # Extract intent using LLM
        try:
            intent = await ranking_llm.extract_ranking_intent(query)
            print(f"Extracted intent: {intent}")
            
            # Validate intent has required fields
            if not intent.get("entity_type"):
                # Try to extract entity type from query
                query_lower = query.lower()
                if "incubator" in query_lower:
                    intent["entity_type"] = "incubator"
                elif "startup" in query_lower or "company" in query_lower:
                    intent["entity_type"] = "startup"
                elif "product" in query_lower:
                    intent["entity_type"] = "product"
                else:
                    intent["entity_type"] = "entity"
            
            if not intent.get("domain"):
                intent["domain"] = "general"
            
            if not intent.get("number"):
                # Try to extract number from query
                import re
                numbers = re.findall(r'\d+', query)
                intent["number"] = int(numbers[0]) if numbers else 10
            
            state["intent"] = intent
        except Exception as e:
            print(f"Error extracting intent: {str(e)}")
            # Fallback intent
            state["intent"] = {
                "entity_type": "entity",
                "domain": "general",
                "location": None,
                "number": 10,
                "suggested_metrics": [],
                "time_period": None
            }
        
        state["messages"].append(
            AIMessage(content=f"Understood: Ranking {state['intent'].get('entity_type')} in {state['intent'].get('domain')}")
        )
        
        print(f"Final intent: {state['intent']}")
        
        return state
    
    async def determine_metrics(self, state: RankingState) -> RankingState:
        """Determine metrics for ranking"""
        intent = state["intent"]
        
        print("Determining metrics...")
        
        # Check if metrics were provided by user
        if state.get("metrics") and len(state.get("metrics", [])) > 0:
            # User provided metrics
            print(f"Using user-provided metrics: {[m['name'] for m in state['metrics']]}")
        else:
            # Suggest metrics using LLM
            entity_type = intent.get("entity_type", "entity")
            domain = intent.get("domain", "general")
            
            print(f"Suggesting metrics for {entity_type} in {domain}")
            
            try:
                suggested = await ranking_llm.suggest_metrics(
                    entity_type=entity_type,
                    domain=domain,
                    context=state["query"]
                )
                
                if suggested and len(suggested) > 0:
                    state["metrics"] = suggested
                    print(f"LLM suggested {len(suggested)} metrics")
                else:
                    # Fallback to default metrics
                    print("LLM returned no metrics, using defaults")
                    state["metrics"] = self._get_default_metrics(entity_type)
            except Exception as e:
                print(f"Error getting metrics from LLM: {str(e)}")
                # Fallback to default metrics
                state["metrics"] = self._get_default_metrics(entity_type)
        
        state["messages"].append(
            AIMessage(content=f"Using metrics: {[m['name'] for m in state['metrics']]}")
        )
        
        return state
    
    def _get_default_metrics(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get default metrics based on entity type"""
        default_metrics = {
            "startup": [
                {"name": "Funding", "type": "numerical", "higher_is_better": True},
                {"name": "Team Size", "type": "numerical", "higher_is_better": True},
                {"name": "Revenue", "type": "numerical", "higher_is_better": True},
                {"name": "Growth Rate", "type": "numerical", "higher_is_better": True},
            ],
            "incubator": [
                {"name": "Total Funding", "type": "numerical", "higher_is_better": True},
                {"name": "Success Rate", "type": "numerical", "higher_is_better": True},
                {"name": "Portfolio Size", "type": "numerical", "higher_is_better": True},
                {"name": "Reputation Score", "type": "numerical", "higher_is_better": True},
            ],
            "company": [
                {"name": "Revenue", "type": "numerical", "higher_is_better": True},
                {"name": "Market Share", "type": "numerical", "higher_is_better": True},
                {"name": "Employee Count", "type": "numerical", "higher_is_better": True},
                {"name": "Customer Rating", "type": "numerical", "higher_is_better": True},
            ],
        }
        
        # Return specific metrics or generic ones
        return default_metrics.get(entity_type.lower(), [
            {"name": "Score", "type": "numerical", "higher_is_better": True},
            {"name": "Rating", "type": "numerical", "higher_is_better": True},
            {"name": "Performance", "type": "numerical", "higher_is_better": True},
        ])
    
    async def identify_sources(self, state: RankingState) -> RankingState:
        """Identify data sources"""
        intent = state["intent"]
        metrics = state["metrics"]
        
        print("Identifying sources...")
        
        # Check if sources were provided
        if state.get("sources") and len(state.get("sources", [])) > 0:
            # User provided sources
            print(f"Using user-provided sources: {len(state['sources'])} sources")
        else:
            # Suggest sources using LLM
            metric_names = [m["name"] for m in metrics]
            entity_type = intent.get("entity_type", "entity")
            domain = intent.get("domain", "general")
            
            print(f"Suggesting sources for {entity_type} in {domain}")
            
            try:
                suggested = await ranking_llm.suggest_sources(
                    entity_type=entity_type,
                    domain=domain,
                    metrics=metric_names
                )
                
                if suggested and len(suggested) > 0:
                    state["sources"] = suggested
                    print(f"LLM suggested {len(suggested)} sources")
                else:
                    print("LLM returned no sources, will use default data generation")
                    state["sources"] = []
            except Exception as e:
                print(f"Error getting sources from LLM: {str(e)}")
                state["sources"] = []
        
        return state
    
    async def gather_data(self, state: RankingState) -> RankingState:
        """Gather data from sources"""
        query_type = state.get("query_type", "crawler")
        
        print(f"Gathering data for query type: {query_type}")
        
        if query_type == "dataset":
            # Data already in entities
            print(f"Dataset mode: {len(state.get('entities', []))} entities provided")
        else:
            # Crawler version - crawl sources
            intent = state.get("intent", {})
            metrics = state.get("metrics", [])
            sources = state.get("sources", [])
            
            # If no entities provided, try to discover real entities via the LLM and then crawl for data
            entity_type = intent.get("entity_type", "entity")
            num_results = intent.get("number", 10)

            discovered = []
            try:
                discovered = await ranking_llm.suggest_entities(state.get("query", ""), number=num_results)
                print(f"LLM suggested {len(discovered)} entities")
            except Exception as e:
                print(f"Error suggesting entities via LLM: {e}")

            entities_list: List[Dict[str, Any]] = []
            for d in discovered:
                if isinstance(d, dict):
                    name = d.get("name")
                    url = d.get("url")
                else:
                    name = str(d)
                    url = None
                if name:
                    ent = {"name": name}
                    if url:
                        ent["source_url"] = url
                    entities_list.append(ent)

            # If we still don't have entities, fallback to generating placeholder names (rare)
            if not entities_list:
                for i in range(num_results):
                    entities_list.append({"name": f"{entity_type.capitalize()} {chr(65+i)}"})

            # For each entity, try to find pages and extract metrics using the crawler
            for ent in entities_list:
                name = ent.get("name")
                try:
                    urls = await crawler._get_search_results(name, min(5, num_results))
                    if urls:
                        crawled = await crawler.crawl_multiple(urls[:5])
                        # store crawled pages
                        for data in crawled:
                            if data.get("success"):
                                await vector_db.store_crawled_data(
                                    url=data.get("url"),
                                    content=data.get("markdown", ""),
                                    metadata=data.get("metadata", {})
                                )

                        # For each metric, attempt to extract using crawler.crawl_for_metrics
                        for metric in metrics:
                            mname = metric.get("name")
                            try:
                                metric_data = await crawler.crawl_for_metrics(name, mname, urls[:5])
                                # metric_data.values is a list of extracted JSONs
                                vals = metric_data.get("values", [])
                                if vals:
                                    first = vals[0]
                                    # If the extraction was a dict with 'value'
                                    if isinstance(first, dict) and first.get("value") is not None:
                                        ent[mname] = first.get("value")
                                        if first.get("unit"):
                                            ent[f"{mname}_unit"] = first.get("unit")
                                    else:
                                        # Otherwise store raw
                                        ent[mname] = first
                            except Exception as e:
                                print(f"Error extracting metric '{mname}' for {name}: {e}")
                    else:
                        print(f"No search URLs found for '{name}'")
                except Exception as e:
                    print(f"Error searching/crawling for entity '{name}': {e}")

            state["entities"] = entities_list
            
            # If sources provided, attempt to crawl
            if sources:
                urls = [s.get("url") for s in sources if s.get("url")]
                if urls:
                    print(f"Crawling {len(urls)} URLs")
                    try:
                        crawled_data = await crawler.crawl_multiple(urls[:5])
                        
                        # Store in vector DB
                        for data in crawled_data:
                            if data.get("success"):
                                await vector_db.store_crawled_data(
                                    url=data["url"],
                                    content=data.get("markdown", ""),
                                    metadata=data.get("metadata", {})
                                )
                        print(f"Crawled {len(crawled_data)} sources")
                    except Exception as e:
                        print(f"Error crawling sources: {str(e)}")

            # If we have entities (e.g., from preview) but no metric values, attempt to fetch metrics via LLM
            entities = state.get("entities", [])
            metrics = state.get("metrics", [])
            if entities and metrics:
                # Check if entities already have metric fields
                need_fetch = False
                for ent in entities:
                    for m in metrics:
                        if m.get("name") not in ent or ent.get(m.get("name")) in (None, "", []):
                            need_fetch = True
                            break
                    if need_fetch:
                        break

                if need_fetch:
                    print(f"Fetching metric values for {len(entities)} entities via LLM...")
                    try:
                        fetched = await ranking_llm.fetch_entity_metrics(entities, metrics, context=state.get("query", ""))
                        # Merge fetched metric values into entities by name
                        fetched_map = {f.get("name"): f for f in fetched if f.get("name")}
                        new_entities = []
                        for ent in entities:
                            name = ent.get("name")
                            fm = fetched_map.get(name, {})
                            merged = ent.copy()
                            for k, v in fm.items():
                                if k == "name":
                                    continue
                                merged[k] = v
                            new_entities.append(merged)
                        state["entities"] = new_entities
                        print(f"Fetched metrics for {len(new_entities)} entities")
                    except Exception as e:
                        print(f"Error fetching metrics via LLM: {str(e)}")
        
        return state
    
    async def normalize_data(self, state: RankingState) -> RankingState:
        """Normalize and clean data"""
        # This step ensures all entities have values for all metrics
        entities = state.get("entities", [])
        metrics = state.get("metrics", [])
        
        # Fill missing values, handle inconsistencies
        for entity in entities:
            for metric in metrics:
                metric_name = metric["name"]
                if metric_name not in entity:
                    # Set default value
                    if metric.get("type") == "numerical":
                        entity[metric_name] = 0
                    else:
                        entity[metric_name] = "Unknown"
        
        state["entities"] = entities
        return state
    
    async def compute_ranking(self, state: RankingState) -> RankingState:
        """Compute the ranking"""
        entities = state.get("entities", [])
        metrics = state.get("metrics", [])
        
        # Create default weights
        weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        state["feature_weights"] = weights
        
        # Compute ranking
        ranking = ranking_engine.rank_entities(
            entities=entities,
            metrics=metrics,
            weights=weights,
            normalization="minmax"
        )
        
        state["ranking_result"] = ranking
        
        return state
    
    async def optimize_ranking(self, state: RankingState) -> RankingState:
        """
        NEW: Optimize ranking quality (Option 1 - Post-processing)
        This runs AFTER compute_ranking as a final optimization step
        """
        print("\n" + "="*60)
        print("RANKING OPTIMIZATION (Post-Processing)")
        print("="*60)
        
        rankings = state.get("ranking_result", [])
        metrics = state.get("metrics", [])
        feature_weights = state.get("feature_weights", {})
        
        # Skip if no rankings
        if not rankings:
            print("⚠️  No rankings to optimize, skipping optimization")
            state["optimization_report"] = {}
            state["optimized_rankings"] = []
            state["used_optimization"] = False
            return state
        
        try:
            # Run optimization analysis
            print("📊 Analyzing ranking quality...")
            result = self.optimizer.analyze_and_optimize(
                rankings=rankings,
                metrics=metrics,
                current_weights=feature_weights,
                ground_truth=None  # Could be provided if available
            )
            
            # Store optimization report
            state["optimization_report"] = result["analysis"]
            
            # Log results
            print(f"\n📈 Overall Health: {result['analysis']['overall_health'].upper()}")
            print(f"🎯 Confidence: {result['analysis']['confidence_score']:.2f}")
            
            # Show metric analysis
            for metric_analysis in result["analysis"]["metric_analyses"]:
                status_icon = {
                    "excellent": "✓",
                    "good": "👍",
                    "needs_improvement": "⚠️",
                    "critical": "🚨"
                }
                icon = status_icon.get(metric_analysis["status"], "•")
                print(f"  {icon} {metric_analysis['metric']}: {metric_analysis['value']:.3f} ({metric_analysis['status']})")
            
            # Decide if we should apply optimization
            if result["should_optimize"] and result.get("optimized_rankings"):
                print(f"\n🔧 Optimization recommended - applying improvements...")
                state["optimized_rankings"] = result["optimized_rankings"]
                state["used_optimization"] = True
                
                # Update feature weights
                if result.get("optimized_weights"):
                    state["feature_weights"] = result["optimized_weights"]
                
                # Log weight changes
                if result.get("weight_changes"):
                    print("\n📊 Weight Adjustments:")
                    for feature, changes in result["weight_changes"].items():
                        change_icon = "📈" if changes["change"] > 0 else "📉"
                        print(f"  {change_icon} {feature}: {changes['old']:.3f} → {changes['new']:.3f} ({changes['change']:+.3f})")
                
                print(f"\n✅ Optimization applied - Rankings improved")
            else:
                print(f"\n✅ Rankings are already good - No optimization needed")
                state["optimized_rankings"] = []
                state["used_optimization"] = False
            
        except Exception as e:
            print(f"\n❌ Error during optimization: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Continue with original rankings on error
            state["optimization_report"] = {"error": str(e)}
            state["optimized_rankings"] = []
            state["used_optimization"] = False
        
        print("="*60 + "\n")
        
        return state
    
    async def generate_insights(self, state: RankingState) -> RankingState:
        """Generate insights for the ranking"""
        # Use optimized rankings if available, otherwise use original
        ranking = state.get("optimized_rankings") or state.get("ranking_result", [])
        
        # Store in vector DB with optimization info
        await vector_db.store_ranking({
            "query": state["query"],
            "query_id": state.get("query_id", ""),
            "intent": state["intent"],
            "metrics": state["metrics"],
            "ranking": ranking,
            "optimization_report": state.get("optimization_report", {}),
            "used_optimization": state.get("used_optimization", False),
            "feature_weights": state.get("feature_weights", {})
        })
        
        # Store knowledge base entry
        await vector_db.store_knowledge_base({
            "query": state["query"],
            "entity_type": state["intent"].get("entity_type"),
            "domain": state["intent"].get("domain"),
            "metrics": [m["name"] for m in state["metrics"]],
            "ranking_summary": f"Top entity: {ranking[0].get('name') if ranking else 'None'}",
            "optimization_applied": state.get("used_optimization", False)
        })
        
        # Create final message
        optimization_note = " (optimized)" if state.get("used_optimization") else ""
        state["messages"].append(
            AIMessage(content=f"Ranking complete{optimization_note}! Top entity: {ranking[0].get('name') if ranking else 'None'}")
        )
        
        return state
    
    async def run(self, query: str, query_type: str = "crawler", 
                  entities: List[Dict[str, Any]] = None,
                  metrics: List[Dict[str, Any]] = None,
                  sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the ranking agent
        
        Args:
            query: User query
            query_type: "dataset" or "crawler"
            entities: Optional pre-loaded entities (for dataset version)
            metrics: Optional user-specified metrics
            sources: Optional user-specified sources
            
        Returns:
            Ranking results with optimization info
        """
        import uuid
        
        query_id = str(uuid.uuid4())
        print(f"\n{'='*60}")
        print(f"Starting ranking workflow with optimization")
        print(f"Query ID: {query_id}")
        print(f"Query: {query}")
        print(f"Type: {query_type}")
        print(f"{'='*60}\n")
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "query_type": query_type,
            "query_id": query_id,
            "intent": {},
            "metrics": metrics or [],
            "sources": sources or [],
            "entities": entities or [],
            "ranking_result": [],
            "optimization_report": {},
            "optimized_rankings": [],
            "used_optimization": False,
            "feature_weights": {},
            "error": ""
        }
        
        try:
            # Run the workflow
            print("Executing LangGraph workflow...")
            final_state = await self.app.ainvoke(initial_state)
            
            # Use optimized rankings if available, otherwise original
            final_rankings = final_state.get("optimized_rankings") or final_state.get("ranking_result", [])
            
            print(f"\n{'='*60}")
            print(f"Workflow completed successfully")
            print(f"Entities ranked: {len(final_rankings)}")
            print(f"Optimization applied: {final_state.get('used_optimization', False)}")
            print(f"{'='*60}\n")
            
            return {
                "ranking": final_rankings,
                "intent": final_state.get("intent", {}),
                "metrics": final_state.get("metrics", []),
                "messages": [m.content for m in final_state.get("messages", [])],
                "query_id": query_id,
                "optimization": {
                    "applied": final_state.get("used_optimization", False),
                    "report": final_state.get("optimization_report", {}),
                    "weights": final_state.get("feature_weights", {})
                }
            }
        except Exception as e:
            print(f"\n{'!'*60}")
            print(f"ERROR in ranking workflow: {str(e)}")
            print(f"{'!'*60}\n")
            import traceback
            traceback.print_exc()
            
            # Return error response
            return {
                "ranking": [],
                "intent": initial_state.get("intent", {}),
                "metrics": initial_state.get("metrics", []),
                "messages": [f"Error: {str(e)}"],
                "query_id": query_id,
                "error": str(e),
                "optimization": {
                    "applied": False,
                    "report": {},
                    "weights": {}
                }
            }


# Global instance
ranking_agent = RankingAgent()