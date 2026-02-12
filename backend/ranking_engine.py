"""
Dynamic Ranking Algorithm Engine - FIXED VERSION
Fixes incorrect ranking calculations
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from datetime import datetime
import json


class RankingEngine:
    """
    Universal ranking engine - FIXED to prevent ranking errors
    """
    
    def __init__(self):
        self.normalization_methods = {
            "minmax": MinMaxScaler(),
            "standard": StandardScaler(),
            "robust": RobustScaler()
        }
        self.debug = True  # Enable debug logging
    
    def rank_entities(
        self,
        entities: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
        normalization: str = "minmax",
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank entities based on metrics and weights - FIXED VERSION
        
        Args:
            entities: List of entities with metric values
            metrics: List of metric definitions (name, type, higher_is_better)
            weights: Optional weights for each metric (defaults to equal weights)
            normalization: Normalization method (minmax, standard, robust)
            constraints: Optional constraints (min/max values, outlier detection)
            
        Returns:
            List of ranked entities with scores
        """
        if not entities:
            return []
        
        print("\n" + "="*60)
        print("🔧 RANKING ENGINE - DEBUG MODE")
        print("="*60)
        
        # Convert to DataFrame
        df = pd.DataFrame(entities)
        
        # Initialize weights if not provided
        if weights is None:
            weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        print(f"\n📊 Input Summary:")
        print(f"  Entities: {len(df)}")
        print(f"  Metrics: {len(metrics)}")
        print(f"  Weights: {weights}")
        
        # Process each metric
        scores = np.zeros(len(df))
        metric_scores = {}
        
        for metric in metrics:
            metric_name = metric["name"]
            
            if metric_name not in df.columns:
                print(f"⚠️  Metric '{metric_name}' not found in data, skipping")
                continue
            
            # Handle missing values
            if pd.api.types.is_numeric_dtype(df[metric_name]):
                df[metric_name] = df[metric_name].fillna(df[metric_name].median())
            else:
                df[metric_name] = df[metric_name].fillna("UNKNOWN")
            
            metric_type = metric.get("type", "numerical")
            higher_is_better = metric.get("higher_is_better", True)
            metric_weight = weights.get(metric_name, 0)
            
            print(f"\n📈 Processing: {metric_name}")
            print(f"   Type: {metric_type}")
            print(f"   Higher is better: {higher_is_better}")
            print(f"   Weight: {metric_weight:.4f}")
            
            if metric_type == "numerical":
                # Numerical metric processing
                df[metric_name] = pd.to_numeric(df[metric_name], errors="coerce")
                df[metric_name] = df[metric_name].fillna(0)
                
                values = df[metric_name].values.reshape(-1, 1)
                
                print(f"   Range: [{values.min():.2f}, {values.max():.2f}]")
                
                # Apply constraints if specified
                if constraints and metric_name in constraints:
                    constraint = constraints[metric_name]
                    if "min" in constraint:
                        values = np.maximum(values, constraint["min"])
                    if "max" in constraint:
                        values = np.minimum(values, constraint["max"])
                
                # Detect and handle outliers
                if constraints and constraints.get("detect_outliers", False):
                    values = self._handle_outliers(values)
                
                # Normalize - FIXED: Use proper scaling
                min_val, max_val = values.min(), values.max()
                
                if max_val > min_val:
                    # Proper min-max normalization
                    normalized = (values - min_val) / (max_val - min_val)
                    normalized = normalized.flatten()
                else:
                    # All values are the same
                    normalized = np.ones(len(values)) * 0.5
                
                # Invert if lower is better
                if not higher_is_better:
                    normalized = 1 - normalized
                
                print(f"   Normalized range: [{normalized.min():.4f}, {normalized.max():.4f}]")
                
                # Apply weight and add to total score
                weighted_score = normalized * metric_weight
                scores += weighted_score
                metric_scores[metric_name] = normalized.tolist()
                
                print(f"   Contribution to total: [{weighted_score.min():.4f}, {weighted_score.max():.4f}]")
                
            elif metric_type == "categorical":
                # Categorical metric processing
                category_scores = self._score_categorical(df[metric_name], higher_is_better)
                weighted_score = category_scores * metric_weight
                scores += weighted_score
                metric_scores[metric_name] = category_scores.tolist()
        
        # Create results - FIXED: Proper ranking
        df["final_score"] = scores
        
        # Handle infinite and NaN values
        df["final_score"] = df["final_score"].replace([np.inf, -np.inf], np.nan)
        df["final_score"] = df["final_score"].fillna(0)
        
        print(f"\n🏆 Final Scores:")
        print(f"   Range: [{df['final_score'].min():.4f}, {df['final_score'].max():.4f}]")
        print(f"   Mean: {df['final_score'].mean():.4f}")
        print(f"   Std: {df['final_score'].std():.4f}")
        
        # FIXED: Proper ranking (1 = best, higher score = better rank)
        df["rank"] = df["final_score"].rank(ascending=False, method="min").astype(int)
        
        # Add individual metric scores
        for metric_name, scores_list in metric_scores.items():
            df[f"{metric_name}_normalized"] = scores_list
        
        # Sort by rank
        df = df.sort_values("rank")
        
        # Debug: Print top 5
        print(f"\n🥇 Top 5 Rankings:")
        for idx, row in df.head(5).iterrows():
            print(f"   #{row['rank']}: {row.get('name', 'Unknown')} - Score: {row['final_score']:.4f}")
        
        print("="*60 + "\n")
        
        # Convert to list of dicts
        results = df.to_dict("records")
        
        return results
    
    def _handle_outliers(self, values: np.ndarray, method: str = "clip") -> np.ndarray:
        """Handle outliers in data"""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        if method == "clip":
            return np.clip(values, lower_bound, upper_bound)
        else:
            return values
    
    def _score_categorical(self, categories: pd.Series, higher_is_better: bool = True) -> np.ndarray:
        """Score categorical values"""
        unique_categories = categories.unique()
        n_categories = len(unique_categories)
        
        if n_categories == 0:
            return np.zeros(len(categories))
        
        # Create mapping of categories to scores
        category_scores = {cat: i / (n_categories - 1) if n_categories > 1 else 0.5 
                          for i, cat in enumerate(sorted(unique_categories))}
        
        if not higher_is_better:
            category_scores = {k: 1 - v for k, v in category_scores.items()}
        
        return categories.map(category_scores).fillna(0.5).values
    
    def compare_entities(self, entity1: Dict[str, Any], entity2: Dict[str, Any], 
                        metrics: List[str]) -> Dict[str, Any]:
        """Compare two entities across metrics"""
        comparison = {
            "entity1": entity1.get("name", "Entity 1"),
            "entity2": entity2.get("name", "Entity 2"),
            "metrics": {}
        }
        
        for metric in metrics:
            val1 = entity1.get(metric)
            val2 = entity2.get(metric)
            
            if val1 is not None and val2 is not None:
                try:
                    val1_num = float(val1)
                    val2_num = float(val2)
                    difference = val1_num - val2_num
                    percent_diff = (difference / val2_num * 100) if val2_num != 0 else 0
                    
                    comparison["metrics"][metric] = {
                        "entity1_value": val1,
                        "entity2_value": val2,
                        "difference": difference,
                        "percent_difference": percent_diff,
                        "winner": comparison["entity1"] if val1_num > val2_num else comparison["entity2"]
                    }
                except (ValueError, TypeError):
                    comparison["metrics"][metric] = {
                        "entity1_value": val1,
                        "entity2_value": val2,
                        "same": val1 == val2
                    }
        
        return comparison
    
    def rerank(self, current_ranking: List[Dict[str, Any]], 
               updated_metrics: Dict[str, Dict[str, Any]],
               metric_definitions: List[Dict[str, Any]],
               weights: Optional[Dict[str, float]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Rerank entities with updated metrics"""
        # Update entities with new metrics
        updated_entities = []
        for entity in current_ranking:
            entity_copy = entity.copy()
            entity_name = entity.get("name")
            
            if entity_name in updated_metrics:
                entity_copy.update(updated_metrics[entity_name])
            
            updated_entities.append(entity_copy)
        
        # Rerank
        new_ranking = self.rank_entities(updated_entities, metric_definitions, weights)
        
        # Track changes
        changes = []
        old_ranks = {e.get("name"): e.get("rank") for e in current_ranking}
        
        for entity in new_ranking:
            entity_name = entity.get("name")
            old_rank = old_ranks.get(entity_name)
            new_rank = entity.get("rank")
            
            if old_rank and old_rank != new_rank:
                changes.append({
                    "entity": entity_name,
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                    "change": old_rank - new_rank,
                    "direction": "up" if new_rank < old_rank else "down"
                })
        
        return new_ranking, changes


# Global instance
ranking_engine = RankingEngine()