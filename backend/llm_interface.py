"""
Enhanced LLM Interface with Token Tracking
Replace your llm_interface.py with this version
"""
import os
import json
import replicate
from typing import Dict, Any, List, Optional
import asyncio
from token_tracking import token_tracker


class RankingLLM:
    """LLM interface for ranking operations with token tracking"""
    
    def __init__(self):
        # Import settings
        try:
            from config.settings import settings
            self.model = settings.default_llm_model
            self.temperature = settings.llm_temperature
            self.max_tokens = settings.llm_max_tokens
            
            if settings.replicate_api_key:
                os.environ["REPLICATE_API_TOKEN"] = settings.replicate_api_key
        except ImportError:
            # Fallback if config not available
            self.model = os.getenv("DEFAULT_LLM_MODEL", "meta/meta-llama-3-70b-instruct")
            self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
            self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        
        # Token tracking
        self.current_query_id = None
    
    def set_query_id(self, query_id: str):
        """Set current query ID for token tracking"""
        self.current_query_id = query_id
        print(f"🔖 Set query ID for tracking: {query_id}")
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text
        Rough approximation: 1 token ≈ 4 characters
        For more accuracy, install tiktoken: pip install tiktoken
        """
        return len(text) // 4
    
    async def _track_tokens(self, prompt: str, response: str, operation: str):
        """Track token usage asynchronously"""
        try:
            # Estimate tokens
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(response)
            
            # Extract model name
            model_name = "meta-llama-3-70b"  # Simplified for pricing lookup
            
            # Track usage
            await token_tracker.track_usage(
                query_id=self.current_query_id or "unknown",
                provider="replicate",
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation=operation,
                metadata={
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "full_model": self.model
                }
            )
            
            print(f"💰 Tracked: {input_tokens} in + {output_tokens} out = {input_tokens + output_tokens} total tokens ({operation})")
            
        except Exception as e:
            print(f"⚠️ Token tracking error: {e}")
            # Don't fail the main operation if tracking fails
    
    def _call_llm(self, prompt: str, operation: str = "general") -> str:
        """
        Call Replicate API with token tracking
        
        Args:
            prompt: The prompt to send to the LLM
            operation: Type of operation (for tracking)
            
        Returns:
            LLM response as string
        """
        try:
            if not os.environ.get("REPLICATE_API_TOKEN"):
                print("⚠️ Warning: Replicate API key not set")
                return json.dumps({"error": "Replicate API key not set"})
            
            print(f"🤖 Calling LLM: {operation}")
            
            # Call LLM
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
            
            # Track tokens asynchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task without awaiting
                    asyncio.create_task(self._track_tokens(prompt, result, operation))
                else:
                    # Run sync if no loop
                    loop.run_until_complete(self._track_tokens(prompt, result, operation))
            except Exception as e:
                # If async fails, try sync in background
                print(f"⚠️ Async tracking failed, using sync: {e}")
                try:
                    asyncio.run(self._track_tokens(prompt, result, operation))
                except:
                    pass  # Don't fail main operation
            
            return result
            
        except Exception as e:
            print(f"❌ LLM Error: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from LLM response"""
        try:
            # Remove markdown code blocks
            text = text.strip()
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            # Parse JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in text
            import re
            json_pattern = r'\{[^{}]*\}|\[[^\[\]]*\]'
            matches = re.findall(json_pattern, text)
            if matches:
                try:
                    return json.loads(matches[0])
                except:
                    pass
            
            print(f"⚠️ Could not parse JSON from response: {text[:200]}")
            return {}
    
    async def extract_ranking_intent(self, query: str) -> Dict[str, Any]:
        """Extract ranking intent from query with token tracking"""
        prompt = f"""Analyze this ranking query and extract information in JSON format.

Query: "{query}"

Extract:
1. entity_type: What is being ranked (e.g., "startup", "company", "product")
2. domain: The domain/industry (e.g., "technology", "healthcare")
3. location: Geographic scope if mentioned (e.g., "India", "USA", "global")
4. number: How many items to rank (extract from query or default to 10)
5. suggested_metrics: List of 3-5 relevant metrics for this entity type
6. time_period: Any time constraints (e.g., "2024", "last year")

Return ONLY a JSON object with these fields. No other text.

Example:
{{"entity_type": "startup", "domain": "AI", "location": "India", "number": 10, "suggested_metrics": ["Funding", "Team Size"], "time_period": null}}
"""
        
        response = self._call_llm(prompt, operation="intent_extraction")
        result = self._extract_json(response)
        
        # Ensure required fields
        if not result.get("entity_type"):
            result["entity_type"] = "entity"
        if not result.get("domain"):
            result["domain"] = "general"
        if not result.get("number"):
            result["number"] = 10
            
        return result
    
    async def suggest_metrics(self, entity_type: str, domain: str, context: str = "") -> List[Dict[str, Any]]:
        """Suggest metrics for ranking with token tracking"""
        prompt = f"""Suggest 5 metrics for ranking {entity_type} in {domain}.

Context: {context}

For each metric provide:
- name: Short metric name
- type: "numerical" or "categorical"
- higher_is_better: true or false

Return ONLY a JSON array like:
[
  {{"name": "Revenue", "type": "numerical", "higher_is_better": true}},
  {{"name": "Market Share", "type": "numerical", "higher_is_better": true}}
]

No other text. Just the JSON array.
"""
        
        response = self._call_llm(prompt, operation="metric_suggestion")
        result = self._extract_json(response)
        
        # Ensure it's a list
        if not isinstance(result, list):
            result = []
        
        # Validate metric format
        metrics = []
        for m in result:
            if isinstance(m, dict) and m.get("name"):
                metrics.append({
                    "name": m.get("name"),
                    "type": m.get("type", "numerical"),
                    "higher_is_better": m.get("higher_is_better", True)
                })
        
        return metrics
    
    async def suggest_entities(self, query: str, number: int = 10) -> List[Dict[str, Any]]:
        """Suggest entities to rank with token tracking"""
        prompt = f"""List {number} real entities for this ranking query: "{query}"

Return ONLY a JSON array of entities. Each entity should have:
- name: Entity name
- url: Optional website URL if known

Example:
[
  {{"name": "OpenAI", "url": "https://openai.com"}},
  {{"name": "Anthropic", "url": "https://anthropic.com"}}
]

Return ONLY the JSON array. No other text.
"""
        
        response = self._call_llm(prompt, operation="entity_suggestion")
        result = self._extract_json(response)
        
        # Ensure it's a list
        if not isinstance(result, list):
            result = []
        
        return result[:number]
    
    async def fetch_entity_metrics(
        self, 
        entities: List[Dict[str, Any]], 
        metrics: List[Dict[str, Any]], 
        context: str = ""
    ) -> List[Dict[str, Any]]:
        """Fetch metric values for entities with token tracking"""
        entity_names = [e.get("name") for e in entities]
        metric_names = [m.get("name") for m in metrics]
        
        prompt = f"""Provide metric values for these entities.

Entities: {json.dumps(entity_names)}
Metrics: {json.dumps(metric_names)}
Context: {context}

For each entity, provide numeric values for all metrics.
Only provide values if they are explicitly known from reliable sources.
If unknown, return null.
Do NOT estimate or fabricate.

Return ONLY a JSON array like:
[
  {{"name": "Entity1", "Metric1": 100, "Metric2": 50}},
  {{"name": "Entity2", "Metric1": 200, "Metric2": 75}}
]

Use numeric values only. Return ONLY the JSON array.
"""
        
        response = self._call_llm(prompt, operation="data_fetching")
        result = self._extract_json(response)
        
        # Ensure it's a list
        if not isinstance(result, list):
            result = []
        
        return result
    
    async def suggest_sources(
        self, 
        entity_type: str, 
        domain: str, 
        metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """Suggest data sources with token tracking"""
        prompt = f"""Suggest 3-5 data sources (websites) for finding information about {entity_type} in {domain}.

Metrics needed: {json.dumps(metrics)}

Return ONLY a JSON array like:
[
  {{"name": "Source Name", "url": "https://example.com", "description": "Brief description"}}
]

Return ONLY the JSON array. No other text.
"""
        
        response = self._call_llm(prompt, operation="source_suggestion")
        result = self._extract_json(response)
        
        # Ensure it's a list
        if not isinstance(result, list):
            result = []
        
        return result
    
    async def generate_insight(
        self, 
        entity_name: str, 
        metrics: Dict[str, Any], 
        rank: int, 
        context: Dict[str, Any]
    ) -> str:
        """Generate insights about an entity with token tracking"""
        prompt = f"""Provide insights about {entity_name} which is ranked #{rank}.

Metrics: {json.dumps(metrics)}
Context: {json.dumps(context)}

Write 2-3 sentences explaining why this entity has this rank and what stands out about it.
Be specific and reference the actual metric values.

Respond with ONLY the insight text. No JSON, no extra formatting.
"""
        
        response = self._call_llm(prompt, operation="insight_generation")
        
        # Return the raw text (not JSON for this one)
        return response.strip()


# Global instance
ranking_llm = RankingLLM()


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        ranking_llm.set_query_id("test-123")
        
        print("\n1. Testing intent extraction...")
        intent = await ranking_llm.extract_ranking_intent("Top 10 AI startups in India")
        print(f"Intent: {intent}")
        
        print("\n2. Testing metric suggestion...")
        metrics = await ranking_llm.suggest_metrics("startup", "AI")
        print(f"Metrics: {metrics}")
        
        print("\n3. Testing entity suggestion...")
        entities = await ranking_llm.suggest_entities("Top AI companies", 5)
        print(f"Entities: {entities}")
        
        print("\n4. Checking token usage...")
        summary = await token_tracker.get_usage_summary("today")
        print(f"Tokens used today: {summary['tokens']['total']}")
        print(f"Cost: ${summary['cost']['total']}")
    
    asyncio.run(test())