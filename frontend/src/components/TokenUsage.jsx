import React, { useState, useEffect } from 'react';
import './TokenUsage.css';

const TokenUsage = () => {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('month');
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    fetchUsage();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
  }, [period]);

  const fetchUsage = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/tokens/usage?period=${period}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Token usage data:', data);
      
      // Check if we got valid data
      if (!data.tokens || !data.cost || !data.budget) {
        throw new Error('Invalid data format received');
      }
      
      setUsage(data);
      setError(null);
    } catch (err) {
      console.error('Token usage error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'critical': return '#dc3545';
      case 'warning': return '#ffc107';
      default: return '#28a745';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'critical': return '🚨';
      case 'warning': return '⚠️';
      default: return '✅';
    }
  };

  if (loading && !usage) {
    return (
      <div className="token-usage-compact loading">
        <span className="spinner">⏳</span> Loading token usage...
      </div>
    );
  }

  if (error) {
    return (
      <div className="token-usage-compact error">
        <div className="error-content">
          <span className="error-icon">❌</span>
          <div className="error-message">
            <strong>Token Tracker Error</strong>
            <p>{error}</p>
            <button className="btn-retry" onClick={fetchUsage}>
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!usage) return null;

  const { tokens, cost, budget, queries, connected } = usage;

  // Show warning if not connected to MongoDB
  const notConnected = connected === false;

  return (
    <div className="token-usage-compact">
      <div className="token-header" onClick={() => setShowDetails(!showDetails)}>
        <div className="token-summary">
          <span className="token-icon">🪙</span>
          <div className="token-info">
            <div className="token-main">
              <span className="token-count">{formatNumber(tokens?.total || 0)}</span>
              <span className="token-label">tokens</span>
              <span className="token-cost">${(cost?.total || 0).toFixed(2)}</span>
            </div>
            <div className="token-budget">
              <span className={`budget-status ${budget?.status || 'normal'}`}>
                {getStatusIcon(budget?.status || 'normal')}
                ${(budget?.remaining || budget?.monthly_limit || 0).toFixed(2)} / ${(budget?.monthly_limit || 0).toFixed(2)} left
              </span>
            </div>
          </div>
        </div>
        <button className="toggle-details">
          {showDetails ? '▼' : '▶'}
        </button>
      </div>

      {showDetails && (
        <div className="token-details">
          {/* Connection Warning */}
          {notConnected && (
            <div className="connection-warning">
              ⚠️ Token tracking is not connected to database. Data shown may be incomplete.
            </div>
          )}

          {/* Period Selector */}
          <div className="period-selector">
            <button
              className={period === 'today' ? 'active' : ''}
              onClick={() => setPeriod('today')}
            >
              Today
            </button>
            <button
              className={period === 'week' ? 'active' : ''}
              onClick={() => setPeriod('week')}
            >
              Week
            </button>
            <button
              className={period === 'month' ? 'active' : ''}
              onClick={() => setPeriod('month')}
            >
              Month
            </button>
          </div>

          {/* Token Breakdown */}
          <div className="usage-stats">
            <div className="stat-item">
              <div className="stat-label">Input Tokens</div>
              <div className="stat-value">{formatNumber(tokens?.input || 0)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Output Tokens</div>
              <div className="stat-value">{formatNumber(tokens?.output || 0)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Queries</div>
              <div className="stat-value">{queries || 0}</div>
            </div>
          </div>

          {/* Budget Progress Bar */}
          <div className="budget-progress">
            <div className="progress-label">
              <span>Budget Usage</span>
              <span>{(budget?.percentage || 0).toFixed(1)}%</span>
            </div>
            <div className="progress-bar">
              <div
                className={`progress-fill ${budget?.status || 'normal'}`}
                style={{
                  width: `${Math.min(budget?.percentage || 0, 100)}%`,
                  backgroundColor: getStatusColor(budget?.status || 'normal')
                }}
              />
            </div>
            <div className="progress-stats">
              <span>Used: ${(budget?.used || 0).toFixed(2)}</span>
              <span>Remaining: ${(budget?.remaining || budget?.monthly_limit || 0).toFixed(2)}</span>
            </div>
          </div>

          {/* Warnings */}
          {budget?.status === 'warning' && (
            <div className="budget-alert warning">
              ⚠️ Warning: You've used {(budget.percentage || 0).toFixed(0)}% of your monthly budget
            </div>
          )}
          {budget?.status === 'critical' && (
            <div className="budget-alert critical">
              🚨 Critical: You've used {(budget.percentage || 0).toFixed(0)}% of your monthly budget!
            </div>
          )}

          {/* Refresh Button */}
          <button className="btn-refresh" onClick={fetchUsage} disabled={loading}>
            {loading ? '⏳' : '🔄'} Refresh
          </button>
        </div>
      )}
    </div>
  );
};

export default TokenUsage;