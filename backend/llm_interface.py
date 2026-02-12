"""
LLM Interface with Token Tracking
Monitors API usage and costs in real-time
"""
from typing import List, Dict, Any, Optional
import os
import replicate
from config.settings import settings
from config.incubator_metrics import (
    get_all_incubator_metrics,
    get_top_metrics,
    format_metric_for_llm
)
import json
import re
from token_tracking import token_tracker


class RankingLLM:
    """LLM interface with integrated token tracking"""
    
    def __init__(self):
        self.model = settings.default_llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        # Set API token
        if settings.replicate_api_key:
            os.environ["REPLICATE_API_TOKEN"] = settings.replicate_api_key
        
        print(f"💰 Budget: ${token_tracker.budget_usd:.2f}")
        print(f"💵 Remaining: ${token_tracker.get_remaining_budget():.4f}")
    
    def _call_llm(self, prompt: str, request_type: str = "general") -> str:
        """Call Replicate API with token tracking"""
        try:
            if not os.environ.get("REPLICATE_API_TOKEN"):
                return json.dumps({"error": "Replicate API key not set"})
            
            # Check budget before making request
            if not token_tracker.can_make_request(self.max_tokens, self.model):
                print(f"\n🚨 BUDGET LIMIT REACHED!")
                token_tracker.print_status()
                return json.dumps({"error": "Budget limit reached"})
            
            print(f"🤖 LLM Call: {request_type}")
            
            # Estimate input tokens (rough: 4 chars per token)
            estimated_input_tokens = len(prompt) // 4
            
            output = replicate.run(
                self.model,
                input={
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "top_p": 0.9,
                }
            )
            
            # Handle streaming response
            if hasattr(output, '__iter__') and not isinstance(output, str):
                result = "".join(str(item) for item in output)
            else:
                result = str(output)
            
            # Track token usage
            estimated_output_tokens = len(result) // 4
            token_tracker.track_request(
                model=self.model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                request_type=request_type
            )
            
            # Show remaining budget
            remaining = token_tracker.get_remaining_budget()
            print(f"💵 Remaining: ${remaining:.4f}")
            
            return result
            
        except Exception as e:
            print(f"❌ LLM Error: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from LLM response"""
        try:
            return json.loads(text)
        except:
            json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return None
        
    async def extract_ranking_intent(self, query: str) -> Dict[str, Any]:
        """Extract ranking intent from user query"""
        prompt = f"""Analyze this ranking query and extract information in JSON format.

Query: "{query}"

Extract:
1. entity_type: What is being ranked (incubators, companies, products, people)
2. domain: The domain/industry (technology, healthcare, finance)
3. location: Geographic scope (India, USA, global)
4. number: How many items to rank (default: 10)
5. suggested_metrics: List of 3-5 relevant metrics
6. time_period: Any time constraints

Return ONLY a JSON object with these fields. No other text.

Example:
{{"entity_type": "incubator", "domain": "technology", "location": "India", "number": 10, "suggested_metrics": ["Total Funding", "Success Rate", "Portfolio Size"], "time_period": null}}
"""
        
        response = self._call_llm(prompt, request_type="intent_extraction")
        result = self._extract_json(response)
        
        if result and isinstance(result, dict):
            return result
        
        # Fallback
        query_lower = query.lower()
        
        entity_type = "entity"
        if "incubator" in query_lower or "accelerator" in query_lower:
            entity_type = "incubator"
        elif "startup" in query_lower or "company" in query_lower:
            entity_type = "startup"
        
        location = None
        if "india" in query_lower:
            location = "India"
        elif "usa" in query_lower or "america" in query_lower:
            location = "USA"
        
        numbers = re.findall(r'\d+', query)
        number = int(numbers[0]) if numbers else 10
        
        return {
            "entity_type": entity_type,
            "domain": "general",
            "location": location,
            "number": number,
            "suggested_metrics": [],
            "time_period": None
        }
    
    async def suggest_metrics(self, entity_type: str, domain: str, context: str = "") -> List[Dict[str, Any]]:
        """Suggest appropriate metrics for ranking"""
        
        # If entity_type is incubator, use research-based metrics (no LLM call needed!)
        if entity_type.lower() in ["incubator", "accelerator"]:
            print(f"✓ Using research-based incubator metrics (no LLM cost)")
            metrics = get_top_metrics(top_n=10)
            return [format_metric_for_llm(m) for m in metrics]
        
        # For other types, use LLM
        prompt = f"""Suggest 5 metrics for ranking {entity_type} in {domain}.

Return ONLY a JSON array like:
[
  {{"name": "Metric Name", "type": "numerical", "higher_is_better": true, "description": "Brief description"}},
  ...
]
"""
        
        response = self._call_llm(prompt, request_type="metric_suggestion")
        result = self._extract_json(response)
        
        if result and isinstance(result, list):
            return result
        
        # Fallback
        return [
            {"name": "Score", "type": "numerical", "higher_is_better": True},
            {"name": "Rating", "type": "numerical", "higher_is_better": True}
        ]
    
    async def suggest_sources(self, entity_type: str, domain: str, metrics: List[str]) -> List[Dict[str, Any]]:
        """Suggest data sources"""
        return []
    
    async def suggest_entities(self, query: str, number: int = 10) -> List[Dict[str, Any]]:
        """Suggest actual entity names - use cache when possible"""
        
        # Cached Indian incubators (no LLM cost!)
        indian_incubators = [
            {"name": "T-Hub (Hyderabad)", "url": "https://t-hub.co"},
            {"name": "SINE IIT Bombay", "url": "https://www.sineiitb.org"},
            {"name": "NSRCEL IIM Bangalore", "url": "https://nsrcel.org"},
            {"name": "AIC-IIITH", "url": "https://aic-iiith.in"},
            {"name": "CIIE.CO IIM Ahmedabad", "url": "https://ciie.co"},
            {"name": "NIDHI PRAYAS", "url": "https://www.nidhiprayas.com"},
            {"name": "Atal Incubation Centre", "url": "https://aim.gov.in"},
            {"name": "91Springboard", "url": "https://www.91springboard.com"},
            {"name": "Zone Startups India", "url": "https://zonestartups.com"},
            {"name": "Startup Village", "url": "https://www.sv.co"}
        ]
        
        query_lower = query.lower()
        
        # Check cache first
        if ("incubator" in query_lower or "accelerator" in query_lower) and "india" in query_lower:
            print(f"✓ Using cached Indian incubators (no LLM cost)")
            return indian_incubators[:number]
        
        # Use LLM for other queries
        prompt = f"""List {number} real, well-known entities for: "{query}"

Return ONLY a JSON array of objects with name and optional URL:
[
  {{"name": "Entity Name", "url": "https://example.com"}},
  ...
]

Be specific and use real entity names.
"""
        
        response = self._call_llm(prompt, request_type="entity_discovery")
        result = self._extract_json(response)
        
        if result and isinstance(result, list) and len(result) > 0:
            valid_entities = []
            for e in result:
                if isinstance(e, dict) and e.get("name"):
                    valid_entities.append(e)
                elif isinstance(e, str):
                    valid_entities.append({"name": e})
            
            if valid_entities:
                return valid_entities[:number]
        
        # Fallback
        return indian_incubators[:number]
    
    async def fetch_entity_metrics(self, entities: List[Dict[str, Any]], metrics: List[Dict[str, Any]], context: str = "") -> List[Dict[str, Any]]:
        """Fetch metric values - SINGLE LLM CALL for all entities"""
        
        entity_names = [e.get("name") for e in entities]
        metric_names = [m.get("name") for m in metrics]
        metric_descriptions = [m.get("description", "") for m in metrics]
        
        prompt = f"""You are analyzing Indian startup incubators. Provide CURRENT, REAL data for each metric.

Incubators: {json.dumps(entity_names)}
Metrics: {json.dumps(list(zip(metric_names, metric_descriptions)))}

IMPORTANT:
1. Use ONLY real, recent data from 2024-2025
2. For "Funds Attracted" - total funding raised by ALL portfolio companies
3. For "Survival Rate" - percentage of companies still operating vs graduated
4. For "Graduation Rate" - percentage completing the program
5. For ratings (1-5 scale) - use reputation and reviews
6. Use realistic values based on incubator tier

Return JSON array:
[
  {{
    "name": "T-Hub (Hyderabad)", 
    "Funds Attracted": 450.5,
    "Survival Rate": 82.3,
    ...
  }},
  ...
]

ONLY numeric values. NO text.
"""
        
        response = self._call_llm(prompt, request_type="metric_fetching")
        result = self._extract_json(response)
        
        if result and isinstance(result, list):
            cleaned = []
            for entity_data in result:
                if not isinstance(entity_data, dict):
                    continue
                
                cleaned_entity = {"name": entity_data.get("name", "Unknown")}
                
                for metric in metrics:
                    metric_name = metric.get("name")
                    value = entity_data.get(metric_name, 0)
                    
                    try:
                        if isinstance(value, str):
                            value = re.sub(r'[^\d.]', '', value)
                            value = float(value) if value else 0
                        cleaned_entity[metric_name] = float(value)
                    except:
                        cleaned_entity[metric_name] = 0
                
                cleaned.append(cleaned_entity)
            
            print(f"✓ Fetched metrics for {len(cleaned)} entities")
            return cleaned
        
        # Fallback
        result = []
        for entity in entities:
            entity_data = {"name": entity.get("name")}
            for metric in metrics:
                entity_data[metric.get("name")] = 0
            result.append(entity_data)
        
        return result
    
    async def generate_insight(self, entity_name: str, metrics: Dict[str, Any], rank: int, context: Dict[str, Any]) -> str:
        """Generate insights"""
        prompt = f"""Provide insights about {entity_name} (ranked #{rank}).

Metrics: {json.dumps(metrics)}

2-3 sentences covering strengths and improvements.
"""
        
        return self._call_llm(prompt, request_type="insight_generation")
    
    async def explain_rank_change(self, entity_name: str, old_rank: int, new_rank: int, metric_changes: Dict[str, Any]) -> str:
        """Explain rank changes"""
        direction = "improved" if new_rank < old_rank else "declined"
        
        prompt = f"""{entity_name}'s ranking {direction} from #{old_rank} to #{new_rank}.

Metric changes: {json.dumps(metric_changes)}

Explain key factors in 2-3 sentences.
"""
        
        return self._call_llm(prompt, request_type="rank_explanation")
    
    def get_token_status(self) -> Dict[str, Any]:
        """Get current token usage status"""
        return token_tracker.get_summary()
    
    def print_token_status(self):
        """Print token usage status"""
        token_tracker.print_status()


# Global instance
ranking_llm = RankingLLM()