"""
Ranking Optimizer Module
Integrates with the existing ranking system to optimize and verify ranking quality
"""
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json


class MetricStatus(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    CRITICAL = "critical"


@dataclass
class MetricAnalysis:
    """Structured analysis result for a single metric"""
    metric_name: str
    current_value: float
    status: MetricStatus
    trend: str  # "improving", "declining", "stable"
    recommendation: str
    priority: int  # 1-5, 5 being highest


@dataclass
class ComprehensiveAnalysis:
    """Complete analysis report"""
    overall_health: MetricStatus
    metric_analyses: List[MetricAnalysis]
    suggested_actions: List[Dict[str, Any]]
    confidence_score: float


class RankingMetricsAnalyzer:
    """
    Analyzes ranking quality using multiple metrics
    """
    
    def __init__(self):
        # Define thresholds for different metrics
        self.thresholds = {
            "ndcg": {"excellent": 0.9, "good": 0.75, "acceptable": 0.6},
            "precision_at_k": {"excellent": 0.85, "good": 0.7, "acceptable": 0.55},
            "map": {"excellent": 0.85, "good": 0.7, "acceptable": 0.55},
            "mrr": {"excellent": 0.9, "good": 0.75, "acceptable": 0.6},
            "recall_at_k": {"excellent": 0.8, "good": 0.65, "acceptable": 0.5},
        }
        
        self.metric_weights = {
            "ndcg": 0.3,
            "precision_at_k": 0.25,
            "map": 0.2,
            "mrr": 0.15,
            "recall_at_k": 0.1,
        }
    
    def analyze_single_metric(
        self, 
        metric_name: str, 
        current_value: float,
        historical_values: List[float] = None
    ) -> MetricAnalysis:
        """Analyze a single metric with historical context"""
        thresholds = self.thresholds.get(metric_name, {
            "excellent": 0.9, "good": 0.75, "acceptable": 0.6
        })
        
        # Determine status
        if current_value >= thresholds["excellent"]:
            status = MetricStatus.EXCELLENT
            priority = 1
            recommendation = f"Maintain current approach for {metric_name}"
        elif current_value >= thresholds["good"]:
            status = MetricStatus.GOOD
            priority = 2
            recommendation = f"Minor optimization possible for {metric_name}"
        elif current_value >= thresholds["acceptable"]:
            status = MetricStatus.NEEDS_IMPROVEMENT
            priority = 4
            recommendation = f"Moderate adjustment needed for {metric_name}"
        else:
            status = MetricStatus.CRITICAL
            priority = 5
            recommendation = f"Urgent adjustment required for {metric_name}"
        
        # Analyze trend
        trend = "stable"
        if historical_values and len(historical_values) >= 2:
            recent_avg = np.mean(historical_values[-3:]) if len(historical_values) >= 3 else historical_values[-1]
            older_avg = np.mean(historical_values[:-3]) if len(historical_values) > 3 else historical_values[0]
            
            if recent_avg > older_avg * 1.05:
                trend = "improving"
                priority = max(1, priority - 1)
            elif recent_avg < older_avg * 0.95:
                trend = "declining"
                priority = min(5, priority + 1)
                recommendation += " (declining trend detected)"
        
        return MetricAnalysis(
            metric_name=metric_name,
            current_value=current_value,
            status=status,
            trend=trend,
            recommendation=recommendation,
            priority=priority
        )
    
    def comprehensive_analysis(
        self,
        current_metrics: Dict[str, float],
        feature_weights: Dict[str, float],
        historical_metrics: List[Dict[str, float]] = None
    ) -> ComprehensiveAnalysis:
        """Perform comprehensive analysis of all metrics"""
        metric_analyses = []
        
        # Analyze each metric
        for metric_name, current_value in current_metrics.items():
            historical_values = None
            if historical_metrics:
                historical_values = [m.get(metric_name, 0) for m in historical_metrics]
            
            analysis = self.analyze_single_metric(
                metric_name, 
                current_value, 
                historical_values
            )
            metric_analyses.append(analysis)
        
        # Determine overall health
        if not metric_analyses:
            overall_health = MetricStatus.GOOD
            avg_priority = 2
        else:
            avg_priority = np.mean([m.priority for m in metric_analyses])
            if avg_priority <= 2:
                overall_health = MetricStatus.EXCELLENT
            elif avg_priority <= 3:
                overall_health = MetricStatus.GOOD
            elif avg_priority <= 4:
                overall_health = MetricStatus.NEEDS_IMPROVEMENT
            else:
                overall_health = MetricStatus.CRITICAL
        
        # Generate suggested actions
        suggested_actions = self._generate_actions(metric_analyses, feature_weights)
        
        # Calculate confidence
        confidence_score = self._calculate_confidence(current_metrics, historical_metrics)
        
        return ComprehensiveAnalysis(
            overall_health=overall_health,
            metric_analyses=metric_analyses,
            suggested_actions=suggested_actions,
            confidence_score=confidence_score
        )
    
    def _generate_actions(
        self, 
        metric_analyses: List[MetricAnalysis],
        feature_weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        actions = []
        
        # Sort by priority (highest first)
        sorted_analyses = sorted(metric_analyses, key=lambda x: x.priority, reverse=True)
        
        for analysis in sorted_analyses[:5]:  # Top 5 priorities
            if analysis.status in [MetricStatus.NEEDS_IMPROVEMENT, MetricStatus.CRITICAL]:
                actions.append({
                    "metric": analysis.metric_name,
                    "current_value": analysis.current_value,
                    "status": analysis.status.value,
                    "priority": analysis.priority,
                    "recommendation": analysis.recommendation,
                    "type": "adjust_weights"
                })
        
        # Analyze weight distribution
        if feature_weights:
            weight_values = list(feature_weights.values())
            avg_weight = np.mean(weight_values)
            std_weight = np.std(weight_values)
            
            for feature, weight in feature_weights.items():
                if weight > avg_weight + std_weight:
                    actions.append({
                        "feature": feature,
                        "weight": weight,
                        "priority": 3,
                        "recommendation": f"Feature '{feature}' may be over-weighted",
                        "type": "rebalance"
                    })
        
        return actions
    
    def _calculate_confidence(
        self,
        current_metrics: Dict[str, float],
        historical_metrics: List[Dict[str, float]] = None
    ) -> float:
        """Calculate confidence score based on data quality"""
        base_confidence = 0.7
        
        # Increase confidence if we have historical data
        if historical_metrics and len(historical_metrics) >= 3:
            base_confidence += 0.2
        
        # Increase confidence if metrics are consistent
        if historical_metrics and len(historical_metrics) >= 2:
            variances = []
            for metric_name in current_metrics.keys():
                values = [m.get(metric_name, 0) for m in historical_metrics]
                if len(values) > 1:
                    variances.append(np.std(values))
            
            if variances and np.mean(variances) < 0.1:
                base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def format_analysis_report(self, analysis: ComprehensiveAnalysis) -> str:
        """Format analysis as readable report"""
        lines = []
        lines.append("=" * 60)
        lines.append("RANKING QUALITY ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append(f"\nOverall Health: {analysis.overall_health.value.upper()}")
        lines.append(f"Confidence Score: {analysis.confidence_score:.2f}")
        lines.append(f"\n📊 METRIC ANALYSIS:")
        lines.append("-" * 60)
        
        for m in analysis.metric_analyses:
            status_icon = {
                "excellent": "✓",
                "good": "👍",
                "needs_improvement": "⚠️",
                "critical": "🚨"
            }.get(m.status.value, "•")
            
            lines.append(f"\n{status_icon} {m.metric_name.upper()}")
            lines.append(f"   Current Value: {m.current_value:.4f}")
            lines.append(f"   Status: {m.status.value}")
            lines.append(f"   Trend: {m.trend}")
            lines.append(f"   Priority: {m.priority}/5")
            lines.append(f"   Recommendation: {m.recommendation}")
        
        if analysis.suggested_actions:
            lines.append(f"\n\n🎯 SUGGESTED ACTIONS:")
            lines.append("-" * 60)
            for i, action in enumerate(analysis.suggested_actions, 1):
                lines.append(f"\n{i}. {action.get('recommendation', 'No recommendation')}")
                lines.append(f"   Priority: {action.get('priority', 0)}/5")
                lines.append(f"   Type: {action.get('type', 'unknown')}")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


class RankingOptimizer:
    """
    Optimizer that integrates with your ranking engine
    """
    
    def __init__(self, ranking_engine):
        self.ranking_engine = ranking_engine
        self.analyzer = RankingMetricsAnalyzer()
        self.metrics_history = []
        self.max_history = 20
    
    def calculate_ranking_metrics(
        self,
        rankings: List[Dict[str, Any]],
        ground_truth: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Calculate ranking quality metrics
        
        Args:
            rankings: List of ranked entities
            ground_truth: Optional list of ideal rankings for comparison
            
        Returns:
            Dict of metric scores
        """
        if not rankings:
            return {
                "ndcg": 0.5,
                "precision_at_k": 0.5,
                "map": 0.5,
                "mrr": 0.5,
                "recall_at_k": 0.5
            }
        
        # If no ground truth, use proxy metrics
        if not ground_truth:
            return self._calculate_proxy_metrics(rankings)
        
        # Calculate real metrics with ground truth
        ranked_items = [item.get("name") or item.get("entity") for item in rankings]
        
        return {
            "ndcg": self._calculate_ndcg(ranked_items, ground_truth),
            "precision_at_k": self._calculate_precision_at_k(ranked_items, ground_truth, k=5),
            "map": self._calculate_map(ranked_items, ground_truth),
            "mrr": self._calculate_mrr(ranked_items, ground_truth),
            "recall_at_k": self._calculate_recall_at_k(ranked_items, ground_truth, k=10)
        }
    
    def _calculate_proxy_metrics(self, rankings: List[Dict]) -> Dict[str, float]:
        """Calculate proxy metrics based on score distribution"""
        scores = [item.get("final_score", 0) for item in rankings]
        
        if not scores or all(s == 0 for s in scores):
            return {
                "ndcg": 0.5,
                "precision_at_k": 0.5,
                "map": 0.5,
                "mrr": 0.5,
                "recall_at_k": 0.5
            }
        
        # Analyze score distribution
        score_range = max(scores) - min(scores) if len(scores) > 1 else 0
        score_std = np.std(scores) if len(scores) > 1 else 0
        score_mean = np.mean(scores)
        
        # Heuristic metrics
        top_score_quality = min(1.0, scores[0] / max(scores)) if scores else 0.5
        separation_quality = min(1.0, score_range * 2)
        diversity_quality = min(1.0, score_std * 3)
        consistency_quality = min(1.0, score_mean)
        
        return {
            "ndcg": (top_score_quality + separation_quality) / 2,
            "precision_at_k": top_score_quality,
            "map": (top_score_quality + diversity_quality) / 2,
            "mrr": top_score_quality,
            "recall_at_k": (separation_quality + consistency_quality) / 2
        }
    
    def _calculate_ndcg(self, ranked_items: List[str], ground_truth: List[str], k: int = 10) -> float:
        """Calculate Normalized Discounted Cumulative Gain"""
        def dcg(relevances):
            return sum(rel / np.log2(idx + 2) for idx, rel in enumerate(relevances[:k]))
        
        relevances = [1 if item in ground_truth else 0 for item in ranked_items]
        ideal_relevances = [1] * min(len(ground_truth), k) + [0] * max(0, k - len(ground_truth))
        
        actual_dcg = dcg(relevances)
        ideal_dcg = dcg(ideal_relevances)
        
        return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0
    
    def _calculate_precision_at_k(self, ranked_items: List[str], ground_truth: List[str], k: int = 5) -> float:
        """Calculate Precision@K"""
        top_k = ranked_items[:k]
        relevant = sum(1 for item in top_k if item in ground_truth)
        return relevant / k if k > 0 else 0.0
    
    def _calculate_map(self, ranked_items: List[str], ground_truth: List[str]) -> float:
        """Calculate Mean Average Precision"""
        precisions = []
        relevant_count = 0
        
        for i, item in enumerate(ranked_items):
            if item in ground_truth:
                relevant_count += 1
                precision = relevant_count / (i + 1)
                precisions.append(precision)
        
        return np.mean(precisions) if precisions else 0.0
    
    def _calculate_mrr(self, ranked_items: List[str], ground_truth: List[str]) -> float:
        """Calculate Mean Reciprocal Rank"""
        for i, item in enumerate(ranked_items):
            if item in ground_truth:
                return 1.0 / (i + 1)
        return 0.0
    
    def _calculate_recall_at_k(self, ranked_items: List[str], ground_truth: List[str], k: int = 10) -> float:
        """Calculate Recall@K"""
        top_k = ranked_items[:k]
        relevant = sum(1 for item in top_k if item in ground_truth)
        return relevant / len(ground_truth) if ground_truth else 0.0
    
    def analyze_and_optimize(
        self,
        rankings: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        current_weights: Optional[Dict[str, float]] = None,
        ground_truth: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze ranking quality and optionally optimize
        
        Returns:
            Dict containing analysis, optimized weights, and optionally re-ranked results
        """
        # Calculate current metrics
        current_metric_scores = self.calculate_ranking_metrics(rankings, ground_truth)
        
        # Get feature weights (or create defaults)
        if current_weights is None:
            current_weights = {m["name"]: 1.0 / len(metrics) for m in metrics}
        
        # Perform analysis
        analysis = self.analyzer.comprehensive_analysis(
            current_metrics=current_metric_scores,
            feature_weights=current_weights,
            historical_metrics=self._get_historical_metrics()
        )
        
        # Store metrics for future trend analysis
        self._store_metrics(current_metric_scores, current_weights)
        
        # Prepare result
        result = {
            "current_metrics": current_metric_scores,
            "analysis": {
                "overall_health": analysis.overall_health.value,
                "confidence_score": analysis.confidence_score,
                "metric_analyses": [
                    {
                        "metric": m.metric_name,
                        "value": m.current_value,
                        "status": m.status.value,
                        "trend": m.trend,
                        "recommendation": m.recommendation,
                        "priority": m.priority
                    }
                    for m in analysis.metric_analyses
                ],
                "suggested_actions": analysis.suggested_actions
            },
            "should_optimize": analysis.overall_health in [MetricStatus.NEEDS_IMPROVEMENT, MetricStatus.CRITICAL],
            "optimized_weights": None,
            "optimized_rankings": None
        }
        
        # If optimization is recommended, calculate new weights
        if result["should_optimize"] and current_weights:
            new_weights = self._calculate_optimized_weights(
                current_weights,
                analysis.suggested_actions
            )
            result["optimized_weights"] = new_weights
            
            # Re-rank with new weights
            entities = [
                {k: v for k, v in item.items() if k not in ["rank", "final_score"]}
                for item in rankings
            ]
            
            optimized_rankings = self.ranking_engine.rank_entities(
                entities=entities,
                metrics=metrics,
                weights=new_weights
            )
            
            result["optimized_rankings"] = optimized_rankings
            result["weight_changes"] = {
                feature: {
                    "old": current_weights.get(feature, 0),
                    "new": new_weights.get(feature, 0),
                    "change": new_weights.get(feature, 0) - current_weights.get(feature, 0)
                }
                for feature in current_weights.keys()
            }
        
        return result
    
    def _calculate_optimized_weights(
        self,
        current_weights: Dict[str, float],
        suggested_actions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate optimized weights based on analysis"""
        new_weights = current_weights.copy()
        
        # Count critical issues
        critical_count = sum(1 for action in suggested_actions if action.get("status") == "critical")
        
        # Adjust based on severity
        adjustment_factor = 0.1 if critical_count > 2 else 0.15
        
        # Find dominant feature
        if new_weights:
            max_weight_feature = max(new_weights.items(), key=lambda x: x[1])[0]
            
            # Adjust weights
            for feature in new_weights:
                if feature == max_weight_feature:
                    new_weights[feature] *= (1 - adjustment_factor)
                else:
                    new_weights[feature] *= (1 + adjustment_factor / (len(new_weights) - 1))
        
        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        return new_weights
    
    def _get_historical_metrics(self) -> List[Dict[str, float]]:
        """Get historical metrics for trend analysis"""
        return [m["metrics"] for m in self.metrics_history]
    
    def _store_metrics(self, metrics: Dict[str, float], weights: Dict[str, float]):
        """Store metrics and weights for historical analysis"""
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "weights": weights
        })
        
        # Keep only last N entries
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]


# Global instance will be created when needed
_optimizer_instance = None

def get_optimizer(ranking_engine):
    """Get or create the global optimizer instance"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = RankingOptimizer(ranking_engine)
    return _optimizer_instance