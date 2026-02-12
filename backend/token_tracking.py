"""
Token and Cost Tracking System for Replicate API
Monitors usage and alerts when approaching budget limits
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import threading


class TokenTracker:
    """Track token usage and costs for Replicate API"""
    
    # Replicate pricing (approximate - check official pricing)
    PRICING = {
        "meta/llama-2-70b-chat": {
            "input": 0.00065 / 1000,   # $0.00065 per 1K tokens
            "output": 0.00275 / 1000    # $0.00275 per 1K tokens
        },
        "meta/llama-2-13b-chat": {
            "input": 0.0001 / 1000,
            "output": 0.0005 / 1000
        },
        "meta/llama-2-7b-chat": {
            "input": 0.00005 / 1000,
            "output": 0.00025 / 1000
        }
    }
    
    def __init__(self, budget_usd: float = 2.0, tracking_file: str = "token_usage.json"):
        """
        Initialize token tracker
        
        Args:
            budget_usd: Total budget in USD
            tracking_file: File to persist tracking data
        """
        self.budget_usd = budget_usd
        self.tracking_file = tracking_file
        self.lock = threading.Lock()
        
        # Load existing data or initialize
        self.data = self._load_data()
        
        # Initialize if needed
        if not self.data:
            self.data = {
                "budget_usd": budget_usd,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "requests": [],
                "models_used": {},
                "started_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            self._save_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Load tracking data from file"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading tracking data: {e}")
                return {}
        return {}
    
    def _save_data(self):
        """Save tracking data to file"""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving tracking data: {e}")
    
    def track_request(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int,
        request_type: str = "general"
    ):
        """
        Track a single API request
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            request_type: Type of request (intent, metrics, entities, etc.)
        """
        with self.lock:
            # Get pricing for model
            pricing = self.PRICING.get(model, self.PRICING["meta/llama-2-70b-chat"])
            
            # Calculate cost
            input_cost = input_tokens * pricing["input"]
            output_cost = output_tokens * pricing["output"]
            total_cost = input_cost + output_cost
            
            # Update totals
            self.data["total_input_tokens"] += input_tokens
            self.data["total_output_tokens"] += output_tokens
            self.data["total_cost_usd"] += total_cost
            self.data["last_updated"] = datetime.now().isoformat()
            
            # Track by model
            if model not in self.data["models_used"]:
                self.data["models_used"][model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "requests": 0
                }
            
            self.data["models_used"][model]["input_tokens"] += input_tokens
            self.data["models_used"][model]["output_tokens"] += output_tokens
            self.data["models_used"][model]["cost_usd"] += total_cost
            self.data["models_used"][model]["requests"] += 1
            
            # Log request
            request_log = {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "type": request_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": total_cost
            }
            self.data["requests"].append(request_log)
            
            # Save to disk
            self._save_data()
            
            # Check budget and alert
            self._check_budget_alert()
    
    def _check_budget_alert(self):
        """Check if approaching budget limits and alert"""
        remaining = self.get_remaining_budget()
        percent_used = (self.data["total_cost_usd"] / self.budget_usd) * 100
        
        if percent_used >= 90:
            print(f"\n{'='*60}")
            print(f"🚨 CRITICAL: Budget 90% Used!")
            print(f"Used: ${self.data['total_cost_usd']:.4f} / ${self.budget_usd:.2f}")
            print(f"Remaining: ${remaining:.4f}")
            print(f"{'='*60}\n")
        elif percent_used >= 75:
            print(f"\n{'='*60}")
            print(f"⚠️  WARNING: Budget 75% Used")
            print(f"Used: ${self.data['total_cost_usd']:.4f} / ${self.budget_usd:.2f}")
            print(f"Remaining: ${remaining:.4f}")
            print(f"{'='*60}\n")
        elif percent_used >= 50:
            print(f"💰 Budget 50% used - ${remaining:.4f} remaining")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary"""
        remaining = self.get_remaining_budget()
        percent_used = (self.data["total_cost_usd"] / self.budget_usd) * 100
        
        return {
            "budget_usd": self.budget_usd,
            "spent_usd": self.data["total_cost_usd"],
            "remaining_usd": remaining,
            "percent_used": percent_used,
            "total_input_tokens": self.data["total_input_tokens"],
            "total_output_tokens": self.data["total_output_tokens"],
            "total_tokens": self.data["total_input_tokens"] + self.data["total_output_tokens"],
            "total_requests": len(self.data["requests"]),
            "models_used": self.data["models_used"],
            "started_at": self.data.get("started_at"),
            "last_updated": self.data["last_updated"]
        }
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget in USD"""
        return max(0, self.budget_usd - self.data["total_cost_usd"])
    
    def can_make_request(self, estimated_tokens: int = 2000, model: str = None) -> bool:
        """Check if there's budget for another request"""
        if model is None:
            model = list(self.PRICING.keys())[0]
        
        pricing = self.PRICING.get(model, self.PRICING["meta/llama-2-70b-chat"])
        
        # Estimate cost (assume 50/50 input/output)
        estimated_cost = (estimated_tokens / 2) * pricing["input"] + (estimated_tokens / 2) * pricing["output"]
        
        remaining = self.get_remaining_budget()
        return remaining >= estimated_cost
    
    def print_status(self):
        """Print current status"""
        summary = self.get_summary()
        
        print(f"\n{'='*60}")
        print(f"💰 TOKEN USAGE & BUDGET STATUS")
        print(f"{'='*60}")
        print(f"\n📊 Budget:")
        print(f"   Total Budget: ${summary['budget_usd']:.2f}")
        print(f"   Spent:        ${summary['spent_usd']:.4f} ({summary['percent_used']:.1f}%)")
        print(f"   Remaining:    ${summary['remaining_usd']:.4f}")
        
        # Progress bar
        bar_length = 40
        filled = int(bar_length * summary['percent_used'] / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"   [{bar}] {summary['percent_used']:.1f}%")
        
        print(f"\n🔢 Tokens:")
        print(f"   Input:  {summary['total_input_tokens']:,}")
        print(f"   Output: {summary['total_output_tokens']:,}")
        print(f"   Total:  {summary['total_tokens']:,}")
        
        print(f"\n📡 Requests:")
        print(f"   Total: {summary['total_requests']}")
        
        if summary['models_used']:
            print(f"\n🤖 Models Used:")
            for model, stats in summary['models_used'].items():
                model_name = model.split('/')[-1]
                print(f"   {model_name}:")
                print(f"      Requests: {stats['requests']}")
                print(f"      Tokens: {stats['input_tokens'] + stats['output_tokens']:,}")
                print(f"      Cost: ${stats['cost_usd']:.4f}")
        
        print(f"\n⏰ Timeline:")
        print(f"   Started: {summary['started_at']}")
        print(f"   Updated: {summary['last_updated']}")
        
        print(f"\n{'='*60}\n")
    
    def reset(self):
        """Reset tracking data"""
        self.data = {
            "budget_usd": self.budget_usd,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "requests": [],
            "models_used": {},
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self._save_data()
        print("✅ Token tracking data reset")


# Global instance
token_tracker = TokenTracker(budget_usd=2.0)


# Decorator to automatically track LLM calls
def track_tokens(request_type: str = "general"):
    """Decorator to track token usage"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Try to extract token info from result
            # This is approximate - adjust based on actual API response
            if isinstance(result, str):
                # Estimate tokens (rough: ~4 chars per token)
                estimated_output = len(result) // 4
                estimated_input = len(str(args)) // 4 if args else 500
                
                # Get model from kwargs or use default
                model = kwargs.get('model', 'meta/llama-2-70b-chat')
                
                token_tracker.track_request(
                    model=model,
                    input_tokens=estimated_input,
                    output_tokens=estimated_output,
                    request_type=request_type
                )
            
            return result
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the tracker
    print("Testing Token Tracker...")
    
    # Simulate some requests
    token_tracker.track_request(
        model="meta/llama-2-70b-chat",
        input_tokens=500,
        output_tokens=1000,
        request_type="intent_extraction"
    )
    
    token_tracker.track_request(
        model="meta/llama-2-70b-chat",
        input_tokens=300,
        output_tokens=800,
        request_type="metric_suggestion"
    )
    
    token_tracker.track_request(
        model="meta/llama-2-70b-chat",
        input_tokens=1000,
        output_tokens=2000,
        request_type="entity_metrics"
    )
    
    # Print status
    token_tracker.print_status()
    
    # Check if can make more requests
    if token_tracker.can_make_request(2000):
        print("✅ Budget available for more requests")
    else:
        print("❌ Budget limit reached")