import React, { useState, useEffect } from 'react';
import './RerankingPanel.css';

const ReRankingPanel = ({ rankingResult, onReRankComplete }) => {
  const [metrics, setMetrics] = useState([]);
  const [weights, setWeights] = useState({});
  const [isReRanking, setIsReRanking] = useState(false);
  const [showWeightEditor, setShowWeightEditor] = useState(false);
  const [showMetricEditor, setShowMetricEditor] = useState(false);

  useEffect(() => {
    if (rankingResult?.metrics_used) {
      // Initialize metrics and weights from current ranking
      setMetrics(rankingResult.metrics_used);
      
      // Calculate current weights (equal by default)
      const initialWeights = {};
      rankingResult.metrics_used.forEach(metric => {
        initialWeights[metric.name] = 1.0 / rankingResult.metrics_used.length;
      });
      setWeights(initialWeights);
    }
  }, [rankingResult]);

  const handleWeightChange = (metricName, value) => {
    setWeights(prev => ({
      ...prev,
      [metricName]: parseFloat(value)
    }));
  };

  const normalizeWeights = () => {
    const total = Object.values(weights).reduce((sum, w) => sum + w, 0);
    if (total === 0) return;
    
    const normalized = {};
    Object.keys(weights).forEach(key => {
      normalized[key] = weights[key] / total;
    });
    setWeights(normalized);
  };

  const handleReRank = async () => {
    setIsReRanking(true);
    
    try {
      // Normalize weights before sending
      normalizeWeights();
      
      const response = await fetch(`http://localhost:8000/api/rerank/custom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ranking_id: rankingResult.ranking_id,
          new_weights: weights,
          new_metrics: metrics
        })
      });

      if (!response.ok) throw new Error('Re-ranking failed');

      const data = await response.json();
      onReRankComplete(data);
    } catch (error) {
      console.error('Re-ranking error:', error);
      alert('Failed to re-rank. Please try again.');
    } finally {
      setIsReRanking(false);
    }
  };

  const handleAutoOptimize = async () => {
    setIsReRanking(true);
    
    try {
      const response = await fetch(`http://localhost:8000/api/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ranking_id: rankingResult.ranking_id
        })
      });

      if (!response.ok) throw new Error('Auto-optimization failed');

      const data = await response.json();
      
      // Update weights with optimized values
      if (data.weight_changes) {
        const newWeights = {};
        Object.keys(data.weight_changes).forEach(key => {
          newWeights[key] = data.weight_changes[key].new;
        });
        setWeights(newWeights);
      }
      
      onReRankComplete(data);
    } catch (error) {
      console.error('Auto-optimization error:', error);
      alert('Failed to auto-optimize. Please try again.');
    } finally {
      setIsReRanking(false);
    }
  };

  const addMetric = () => {
    const newMetric = {
      name: `New Metric ${metrics.length + 1}`,
      type: 'numerical',
      higher_is_better: true
    };
    setMetrics([...metrics, newMetric]);
    setWeights({
      ...weights,
      [newMetric.name]: 0.1
    });
  };

  const removeMetric = (metricName) => {
    setMetrics(metrics.filter(m => m.name !== metricName));
    const newWeights = { ...weights };
    delete newWeights[metricName];
    setWeights(newWeights);
  };

  const updateMetric = (index, field, value) => {
    const updated = [...metrics];
    updated[index] = { ...updated[index], [field]: value };
    
    // If name changed, update weights key
    if (field === 'name') {
      const oldName = metrics[index].name;
      const newWeights = { ...weights };
      newWeights[value] = newWeights[oldName];
      delete newWeights[oldName];
      setWeights(newWeights);
    }
    
    setMetrics(updated);
  };

  const resetToDefault = () => {
    if (rankingResult?.metrics_used) {
      setMetrics(rankingResult.metrics_used);
      const defaultWeights = {};
      rankingResult.metrics_used.forEach(metric => {
        defaultWeights[metric.name] = 1.0 / rankingResult.metrics_used.length;
      });
      setWeights(defaultWeights);
    }
  };

  const getTotalWeight = () => {
    return Object.values(weights).reduce((sum, w) => sum + w, 0);
  };

  const isWeightValid = () => {
    const total = getTotalWeight();
    return Math.abs(total - 1.0) < 0.01; // Allow small floating point errors
  };

  return (
    <div className="reranking-panel">
      <div className="panel-header">
        <h3>🔄 Re-Ranking Controls</h3>
        <p>Not satisfied? Adjust weights or metrics and re-rank!</p>
      </div>

      <div className="control-buttons">
        <button 
          className="btn-primary"
          onClick={() => setShowWeightEditor(!showWeightEditor)}
        >
          ⚖️ Adjust Weights
        </button>
        <button 
          className="btn-secondary"
          onClick={() => setShowMetricEditor(!showMetricEditor)}
        >
          📊 Edit Metrics
        </button>
        <button 
          className="btn-success"
          onClick={handleAutoOptimize}
          disabled={isReRanking}
        >
          ✨ Auto-Optimize
        </button>
      </div>

      {/* Weight Editor */}
      {showWeightEditor && (
        <div className="weight-editor">
          <h4>Adjust Feature Weights</h4>
          <p className="help-text">
            Control how much each metric matters. Higher weight = more important.
          </p>
          
          <div className="weight-list">
            {metrics.map((metric) => (
              <div key={metric.name} className="weight-item">
                <label>{metric.name}</label>
                <div className="weight-controls">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={weights[metric.name] || 0}
                    onChange={(e) => handleWeightChange(metric.name, e.target.value)}
                  />
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={(weights[metric.name] || 0).toFixed(2)}
                    onChange={(e) => handleWeightChange(metric.name, e.target.value)}
                    className="weight-input"
                  />
                  <span className="weight-percentage">
                    {((weights[metric.name] || 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="weight-bar">
                  <div 
                    className="weight-fill"
                    style={{ width: `${(weights[metric.name] || 0) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="weight-summary">
            <div className={`total-weight ${isWeightValid() ? 'valid' : 'invalid'}`}>
              Total: {getTotalWeight().toFixed(2)}
              {!isWeightValid() && <span className="warning"> ⚠️ Must equal 1.0</span>}
            </div>
            <button onClick={normalizeWeights} className="btn-normalize">
              Normalize Weights
            </button>
          </div>
        </div>
      )}

      {/* Metric Editor */}
      {showMetricEditor && (
        <div className="metric-editor">
          <h4>Edit Metrics</h4>
          <p className="help-text">
            Add, remove, or modify metrics used for ranking.
          </p>

          <div className="metric-list">
            {metrics.map((metric, index) => (
              <div key={index} className="metric-item">
                <input
                  type="text"
                  value={metric.name}
                  onChange={(e) => updateMetric(index, 'name', e.target.value)}
                  placeholder="Metric name"
                  className="metric-name-input"
                />
                <select
                  value={metric.type}
                  onChange={(e) => updateMetric(index, 'type', e.target.value)}
                  className="metric-type-select"
                >
                  <option value="numerical">Numerical</option>
                  <option value="categorical">Categorical</option>
                </select>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={metric.higher_is_better}
                    onChange={(e) => updateMetric(index, 'higher_is_better', e.target.checked)}
                  />
                  Higher is better
                </label>
                <button
                  onClick={() => removeMetric(metric.name)}
                  className="btn-remove"
                  disabled={metrics.length <= 1}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <button onClick={addMetric} className="btn-add-metric">
            + Add Metric
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        <button
          onClick={resetToDefault}
          className="btn-reset"
          disabled={isReRanking}
        >
          ↺ Reset to Default
        </button>
        <button
          onClick={handleReRank}
          className="btn-rerank"
          disabled={isReRanking || !isWeightValid()}
        >
          {isReRanking ? '⏳ Re-ranking...' : '🚀 Re-Rank Now'}
        </button>
      </div>

      {/* Optimization Info */}
      {rankingResult?.optimization?.applied && (
        <div className="optimization-info">
          <h4>Previous Optimization Applied</h4>
          <p>
            Overall Health: <strong>{rankingResult.optimization.report.overall_health}</strong>
          </p>
          <p>
            Confidence: <strong>{(rankingResult.optimization.report.confidence_score * 100).toFixed(0)}%</strong>
          </p>
        </div>
      )}
    </div>
  );
};

export default ReRankingPanel;