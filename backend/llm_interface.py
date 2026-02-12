"""
LLM Interface using Replicate and LangChain
"""
from typing import List, Dict, Any, Optional
import os
import replicate
from config.settings import settings
import json
import re


class RankingLLM:
    """LLM interface for ranking operations"""
    
    def __init__(self):
        self.model = settings.default_llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        # Set API token
        if settings.replicate_api_key:
            os.environ["REPLICATE_API_TOKEN"] = settings.replicate_api_key
    
    def _call_llm(self, prompt: str) -> str:
        """Call Replicate API directly"""
        try:
            if not os.environ.get("REPLICATE_API_TOKEN"):
                return json.dumps({"error": "Replicate API key not set"})
            
            print(f"🤖 Calling Replicate: {self.model}")
            
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
            
            return result
        except Exception as e:
            print(f"❌ LLM Error: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from LLM response"""
        try:
            # Try direct parse
            return json.loads(text)
        except:
            # Try to find JSON in text
            json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # Return None if no valid JSON found
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
        
        response = self._call_llm(prompt)
        result = self._extract_json(response)
        
        if result and isinstance(result, dict):
            return result
        
        # Fallback: extract from query using keywords
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
        
        # Predefined metrics for common entity types
        metric_library = {
            "incubator": [
                {"name": "Total Funding", "type": "numerical", "higher_is_better": True, "description": "Total funding provided to startups"},
                {"name": "Success Rate", "type": "numerical", "higher_is_better": True, "description": "Percentage of successful exits"},
                {"name": "Portfolio Size", "type": "numerical", "higher_is_better": True, "description": "Number of startups in portfolio"},
                {"name": "Reputation Score", "type": "numerical", "higher_is_better": True, "description": "Industry reputation rating"},
                {"name": "Mentorship Quality", "type": "numerical", "higher_is_better": True, "description": "Quality of mentorship programs"}
            ],
            "startup": [
                {"name": "Funding", "type": "numerical", "higher_is_better": True},
                {"name": "Revenue", "type": "numerical", "higher_is_better": True},
                {"name": "Team Size", "type": "numerical", "higher_is_better": True},
                {"name": "Growth Rate", "type": "numerical", "higher_is_better": True}
            ]
        }
        
        # Return predefined metrics if available
        if entity_type.lower() in metric_library:
            print(f"✓ Using predefined metrics for {entity_type}")
            return metric_library[entity_type.lower()]
        
        # Otherwise try LLM
        prompt = f"""Suggest 5 metrics for ranking {entity_type} in {domain}.

Return ONLY a JSON array like:
[
  {{"name": "Metric Name", "type": "numerical", "higher_is_better": true, "description": "Brief description"}},
  ...
]
"""
        
        response = self._call_llm(prompt)
        result = self._extract_json(response)
        
        if result and isinstance(result, list):
            return result
        
        # Fallback to generic metrics
        return [
            {"name": "Score", "type": "numerical", "higher_is_better": True},
            {"name": "Rating", "type": "numerical", "higher_is_better": True}
        ]
    
    async def suggest_sources(self, entity_type: str, domain: str, metrics: List[str]) -> List[Dict[str, Any]]:
        """Suggest data sources - return empty for now since we'll use LLM for data"""
        return []
    
    async def suggest_entities(self, query: str, number: int = 10) -> List[Dict[str, Any]]:
        """Suggest actual entity names based on the query"""
        
        # Hardcoded list of Indian incubators for reliability
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
        
        # Check if query is about Indian incubators
        if ("incubator" in query_lower or "accelerator" in query_lower) and "india" in query_lower:
            print(f"✓ Using predefined Indian incubators list")
            return indian_incubators[:number]
        
        # Try LLM for other queries
        prompt = f"""List {number} real, well-known entities for: "{query}"

Return ONLY a JSON array of objects with name and optional URL:
[
  {{"name": "Entity Name", "url": "https://example.com"}},
  ...
]

Be specific and use real entity names, not generic placeholders.
"""
        
        response = self._call_llm(prompt)
        result = self._extract_json(response)
        
        if result and isinstance(result, list) and len(result) > 0:
            # Validate results have names
            valid_entities = []
            for e in result:
                if isinstance(e, dict) and e.get("name"):
                    valid_entities.append(e)
                elif isinstance(e, str):
                    valid_entities.append({"name": e})
            
            if valid_entities:
                return valid_entities[:number]
        
        # Fallback to generic list
        return indian_incubators[:number]
    
    async def fetch_entity_metrics(self, entities: List[Dict[str, Any]], metrics: List[Dict[str, Any]], context: str = "") -> List[Dict[str, Any]]:
        """Fetch metric values for entities using LLM knowledge"""
        
        entity_names = [e.get("name") for e in entities]
        metric_names = [m.get("name") for m in metrics]
        
        prompt = f"""For each of these entities, provide estimated values for the given metrics based on your knowledge.

Entities: {json.dumps(entity_names)}
Metrics: {json.dumps(metric_names)}

Return a JSON array where each object has:
- "name": entity name
- One key for each metric with a NUMERIC value (use 0 if unknown)

Example:
[
  {{"name": "T-Hub", "Total Funding": 12000000, "Success Rate": 75, "Portfolio Size": 150}},
  ...
]

Important: 
- Use only numeric values (no currency symbols, no text like "Unknown")
- If you don't know a value, use 0
- Return ONLY valid JSON
"""
        
        response = self._call_llm(prompt)
        result = self._extract_json(response)
        
        if result and isinstance(result, list):
            # Clean the data - ensure numeric values
            cleaned = []
            for entity_data in result:
                if not isinstance(entity_data, dict):
                    continue
                
                cleaned_entity = {"name": entity_data.get("name", "Unknown")}
                
                for metric in metrics:
                    metric_name = metric.get("name")
                    value = entity_data.get(metric_name, 0)
                    
                    # Convert to numeric
                    try:
                        if isinstance(value, str):
                            # Remove currency symbols and commas
                            value = re.sub(r'[^\d.]', '', value)
                            value = float(value) if value else 0
                        cleaned_entity[metric_name] = float(value)
                    except:
                        cleaned_entity[metric_name] = 0
                
                cleaned.append(cleaned_entity)
            
            return cleaned
        
        # Fallback: return entities with zero values
        result = []
        for entity in entities:
            entity_data = {"name": entity.get("name")}
            for metric in metrics:
                entity_data[metric.get("name")] = 0
            result.append(entity_data)
        
        return result
    
    async def generate_insight(self, entity_name: str, metrics: Dict[str, Any], rank: int, context: Dict[str, Any]) -> str:
        """Generate insights about an entity"""
        prompt = f"""Provide insights about {entity_name} (ranked #{rank}).

Metrics: {json.dumps(metrics)}

Provide a brief 2-3 sentence analysis covering strengths and areas for improvement.
"""
        
        return self._call_llm(prompt)
    
    async def explain_rank_change(self, entity_name: str, old_rank: int, new_rank: int, metric_changes: Dict[str, Any]) -> str:
        """Explain rank changes"""
        direction = "improved" if new_rank < old_rank else "declined"
        
        prompt = f"""{entity_name}'s ranking {direction} from #{old_rank} to #{new_rank}.

Metric changes: {json.dumps(metric_changes)}

Explain the key factors in 2-3 sentences.
"""
        
        return self._call_llm(prompt)


# Global instance
ranking_llm = RankingLLM()