import React, { useState, useEffect } from 'react';
// Styles live in App.css — no separate import needed

const TokenUsage = () => {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('month');
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    fetchUsage();
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      if (!data.tokens || !data.cost || !data.budget) throw new Error('Invalid data format received');
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
      case 'critical': return '#ff4d4d';
      case 'warning': return '#ffc107';
      default: return '#4dff91';
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
        <span className="spinner">⏳</span>
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
            <button className="btn-retry" onClick={fetchUsage}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  if (!usage) return null;

  const { tokens, cost, budget, queries, connected } = usage;
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
          </div>
        </div>
        <button className="toggle-details">{showDetails ? '▾' : '▸'}</button>
      </div>

      {showDetails && (
        <div className="token-details">
          {notConnected && (
            <div className="connection-warning">
              ⚠️ Token tracking not connected to database.
            </div>
          )}

          <div className="period-selector">
            {['today', 'week', 'month'].map((p) => (
              <button key={p} className={period === p ? 'active' : ''} onClick={() => setPeriod(p)}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          <div className="usage-stats">
            <div className="stat-item">
              <span className="stat-label">Input</span>
              <span className="stat-value">{formatNumber(tokens?.input || 0)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Output</span>
              <span className="stat-value">{formatNumber(tokens?.output || 0)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Queries</span>
              <span className="stat-value">{queries || 0}</span>
            </div>
          </div>

          <div className="budget-progress">
            <div className="progress-label">
              <span>Budget</span>
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
              <span>Left: ${(budget?.remaining || budget?.monthly_limit || 0).toFixed(2)}</span>
            </div>
          </div>

          {budget?.status === 'warning' && (
            <div className="budget-alert warning">
              ⚠️ {(budget.percentage || 0).toFixed(0)}% of monthly budget used
            </div>
          )}
          {budget?.status === 'critical' && (
            <div className="budget-alert critical">
              🚨 {(budget.percentage || 0).toFixed(0)}% of monthly budget used!
            </div>
          )}

          <button className="btn-refresh" onClick={fetchUsage} disabled={loading}>
            {loading ? '⏳' : '↻'} Refresh
          </button>
        </div>
      )}
    </div>
  );
};

export default TokenUsage;