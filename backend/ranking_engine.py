"""
Dynamic Ranking Algorithm Engine
Supports multiple ranking methodologies and normalization strategies
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from datetime import datetime
import json


class RankingEngine:
    """
    Universal ranking engine that can rank any entity by any metrics
    """
    
    def __init__(self):
        self.normalization_methods = {
            "minmax": MinMaxScaler(),
            "standard": StandardScaler(),
            "robust": RobustScaler()
        }
    
    def rank_entities(
        self,
        entities: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
        normalization: str = "minmax",
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank entities based on metrics and weights
        
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
        
        # Convert to DataFrame
        df = pd.DataFrame(entities)
        
        # Initialize weights if not provided
        if weights is None:
            weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # Process each metric
        scores = np.zeros(len(df))
        metric_scores = {}
        
        for metric in metrics:
            metric_name = metric["name"]
            
            if metric_name not in df.columns:
                continue
            
            # Handle missing values (safe for mixed types)
            if pd.api.types.is_numeric_dtype(df[metric_name]):
                df[metric_name] = df[metric_name].fillna(df[metric_name].median())
            else:
                df[metric_name] = df[metric_name].fillna("UNKNOWN")
            
            # Get metric type
            metric_type = metric.get("type", "numerical")
            higher_is_better = metric.get("higher_is_better", True)
            
            if metric_type == "numerical":
                # Numerical metric processing
                df[metric_name] = pd.to_numeric(df[metric_name], errors="coerce")

                values = df[metric_name].values.reshape(-1, 1)
                
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
                
                # Normalize
                if normalization in self.normalization_methods:
                    scaler = self.normalization_methods[normalization]
                    normalized = scaler.fit_transform(values).flatten()
                else:
                    # Default min-max normalization
                    min_val, max_val = values.min(), values.max()
                    if max_val > min_val:
                        normalized = (values - min_val) / (max_val - min_val)
                        normalized = normalized.flatten()
                    else:
                        normalized = np.ones(len(values))
                
                # Invert if lower is better
                if not higher_is_better:
                    normalized = 1 - normalized
                
                # Apply weight and add to total score
                weighted_score = normalized * weights.get(metric_name, 0)
                scores += weighted_score
                metric_scores[metric_name] = normalized.tolist()
                
            elif metric_type == "categorical":
                # Categorical metric processing
                # Convert categories to scores
                category_scores = self._score_categorical(df[metric_name], higher_is_better)
                weighted_score = category_scores * weights.get(metric_name, 0)
                scores += weighted_score
                metric_scores[metric_name] = category_scores.tolist()
        
        # Create results
        df["final_score"] = scores
        df["final_score"] = df["final_score"].replace([np.inf, -np.inf], np.nan)

        # Fill NaN with lowest possible value
        df["final_score"] = df["final_score"].fillna(df["final_score"].min() - 1)
        df["rank"] = df["final_score"].rank(ascending=False, method="min").astype(int)
        
        # Add individual metric scores
        for metric_name, scores_list in metric_scores.items():
            df[f"{metric_name}_normalized"] = scores_list
        
        # Sort by rank
        df = df.sort_values("rank")
        
        # Convert to list of dicts
        results = df.to_dict("records")
        
        return results
    
    def _handle_outliers(self, values: np.ndarray, method: str = "clip") -> np.ndarray:
        """
        Handle outliers in data
        
        Args:
            values: Array of values
            method: Method to handle outliers (clip, remove, winsorize)
            
        Returns:
            Processed values
        """
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
        """
        Score categorical values
        
        Args:
            categories: Series of categorical values
            higher_is_better: Whether higher categories are better
            
        Returns:
            Numerical scores
        """
        # Create mapping of categories to scores
        unique_categories = categories.unique()
        n_categories = len(unique_categories)
        
        if n_categories == 0:
            return np.zeros(len(categories))
        
        # Assign scores based on frequency or alphabetical order
        category_scores = {cat: i / (n_categories - 1) if n_categories > 1 else 0.5 
                          for i, cat in enumerate(sorted(unique_categories))}
        
        if not higher_is_better:
            category_scores = {k: 1 - v for k, v in category_scores.items()}
        
        return categories.map(category_scores).fillna(0.5).values
    
    def compare_entities(self, entity1: Dict[str, Any], entity2: Dict[str, Any], 
                        metrics: List[str]) -> Dict[str, Any]:
        """
        Compare two entities across metrics
        
        Args:
            entity1: First entity
            entity2: Second entity
            metrics: List of metrics to compare
            
        Returns:
            Comparison results
        """
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
                    # Categorical comparison
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
        """
        Rerank entities with updated metrics
        
        Args:
            current_ranking: Current ranking
            updated_metrics: Updated metric values {entity_name: {metric: value}}
            metric_definitions: Metric definitions
            weights: Metric weights
            
        Returns:
            Tuple of (new_ranking, changes)
        """
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
