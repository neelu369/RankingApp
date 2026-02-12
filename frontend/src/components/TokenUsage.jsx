import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TokenUsage.css';

const TokenUsage = () => {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchUsage = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/token-usage');
      if (response.data.success) {
        setUsage(response.data);
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch token usage');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();

    // Auto-refresh every 10 seconds if enabled
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchUsage, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const handleReset = async () => {
    if (!window.confirm('Are you sure you want to reset token usage tracking?')) {
      return;
    }

    try {
      await axios.post('http://localhost:8000/api/token-usage/reset');
      fetchUsage();
      alert('Token usage reset successfully');
    } catch (err) {
      alert('Failed to reset token usage');
    }
  };

  if (loading) {
    return (
      <div className="token-usage loading">
        <div className="spinner">⏳ Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="token-usage error">
        <p>{error}</p>
        <button onClick={fetchUsage} className="btn-retry">
          🔄 Retry
        </button>
      </div>
    );
  }

  if (!usage) return null;

  const { budget, tokens, requests, models, timeline } = usage;
  const percentUsed = budget.percent_used;

  // Determine alert level
  let alertClass = 'normal';
  if (percentUsed >= 90) alertClass = 'critical';
  else if (percentUsed >= 75) alertClass = 'warning';
  else if (percentUsed >= 50) alertClass = 'caution';

  return (
    <div className={`token-usage ${alertClass}`}>
      <div className="token-usage-header">
        <h3>💰 Token Usage & Budget</h3>
        <div className="controls">
          <label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button onClick={fetchUsage} className="btn-refresh">
            🔄
          </button>
        </div>
      </div>

      {/* Budget Section */}
      <div className="budget-section">
        <div className="budget-amounts">
          <div className="budget-item">
            <span className="label">Total Budget:</span>
            <span className="value">${budget.total_usd.toFixed(2)}</span>
          </div>
          <div className="budget-item">
            <span className="label">Spent:</span>
            <span className="value spent">${budget.spent_usd.toFixed(4)}</span>
          </div>
          <div className="budget-item">
            <span className="label">Remaining:</span>
            <span className="value remaining">${budget.remaining_usd.toFixed(4)}</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="progress-bar-container">
          <div 
            className="progress-bar-fill" 
            style={{ width: `${Math.min(percentUsed, 100)}%` }}
          />
          <span className="progress-label">{percentUsed.toFixed(1)}% Used</span>
        </div>

        {/* Alert Messages */}
        {percentUsed >= 90 && (
          <div className="alert alert-critical">
            🚨 CRITICAL: Budget 90% used! Please monitor usage carefully.
          </div>
        )}
        {percentUsed >= 75 && percentUsed < 90 && (
          <div className="alert alert-warning">
            ⚠️ WARNING: Budget 75% used. Approaching limit.
          </div>
        )}
      </div>

      {/* Tokens Section */}
      <div className="tokens-section">
        <h4>🔢 Token Statistics</h4>
        <div className="tokens-grid">
          <div className="token-stat">
            <span className="stat-label">Input</span>
            <span className="stat-value">{tokens.input.toLocaleString()}</span>
          </div>
          <div className="token-stat">
            <span className="stat-label">Output</span>
            <span className="stat-value">{tokens.output.toLocaleString()}</span>
          </div>
          <div className="token-stat">
            <span className="stat-label">Total</span>
            <span className="stat-value">{tokens.total.toLocaleString()}</span>
          </div>
          <div className="token-stat">
            <span className="stat-label">Requests</span>
            <span className="stat-value">{requests.total}</span>
          </div>
        </div>
      </div>

      {/* Models Section */}
      {models && Object.keys(models).length > 0 && (
        <div className="models-section">
          <h4>🤖 Models Used</h4>
          {Object.entries(models).map(([model, stats]) => {
            const modelName = model.split('/').pop();
            return (
              <div key={model} className="model-card">
                <div className="model-name">{modelName}</div>
                <div className="model-stats">
                  <span>Requests: {stats.requests}</span>
                  <span>Tokens: {(stats.input_tokens + stats.output_tokens).toLocaleString()}</span>
                  <span>Cost: ${stats.cost_usd.toFixed(4)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Timeline */}
      <div className="timeline-section">
        <div className="timeline-item">
          <span className="timeline-label">Started:</span>
          <span className="timeline-value">
            {new Date(timeline.started_at).toLocaleString()}
          </span>
        </div>
        <div className="timeline-item">
          <span className="timeline-label">Last Updated:</span>
          <span className="timeline-value">
            {new Date(timeline.last_updated).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="actions-section">
        <button onClick={handleReset} className="btn-reset">
          🔄 Reset Tracking
        </button>
      </div>
    </div>
  );
};

export default TokenUsage;