import React from 'react';
import './RankingDisplay.css';

const RankingDisplay = ({ ranking, metrics, onEntitySelect }) => {
  // Add safety checks
  if (!ranking) {
    return (
      <div className="ranking-display">
        <div className="no-data">
          <p>No ranking data available</p>
        </div>
      </div>
    );
  }

  // Ensure ranking is an array
  const rankingArray = Array.isArray(ranking) ? ranking : [];

  if (rankingArray.length === 0) {
    return (
      <div className="ranking-display">
        <div className="no-data">
          <p>No entities to display</p>
        </div>
      </div>
    );
  }

  // Ensure metrics is an array
  const metricsArray = Array.isArray(metrics) ? metrics : [];

  return (
    <div className="ranking-display">
      <h2>🏆 Ranking Results</h2>
      
      <div className="ranking-table-container">
        <table className="ranking-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Name</th>
              {metricsArray.map((metric, idx) => (
                <th key={idx}>{metric.name || metric}</th>
              ))}
              <th>Score</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rankingArray.map((entity, index) => {
              const entityName = entity.name || entity.entity || entity.title || 'Unknown';
              const rank = entity.rank || index + 1;
              const score = entity.final_score || entity.score || 0;

              return (
                <tr key={index} className={index < 3 ? `top-${index + 1}` : ''}>
                  <td className="rank-cell">
                    <span className="rank-badge">{rank}</span>
                    {index === 0 && <span className="trophy">🥇</span>}
                    {index === 1 && <span className="trophy">🥈</span>}
                    {index === 2 && <span className="trophy">🥉</span>}
                  </td>
                  <td className="name-cell">
                    <strong>{entityName}</strong>
                  </td>
                  {metricsArray.map((metric, idx) => {
                    const metricName = metric.name || metric;
                    const value = entity[metricName];
                    
                    return (
                      <td key={idx} className="metric-cell">
                        {value !== null && value !== undefined 
                          ? typeof value === 'number' 
                            ? value.toLocaleString() 
                            : value
                          : '-'}
                      </td>
                    );
                  })}
                  <td className="score-cell">
                    <div className="score-bar-container">
                      <div 
                        className="score-bar" 
                        style={{ width: `${(score * 100).toFixed(0)}%` }}
                      />
                      <span className="score-text">
                        {(score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="actions-cell">
                    {onEntitySelect && (
                      <button
                        className="btn-details"
                        onClick={() => onEntitySelect(entity)}
                      >
                        View Details
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="ranking-summary">
        <p>Showing {rankingArray.length} entities</p>
        {metricsArray.length > 0 && (
          <p>Ranked by: {metricsArray.map(m => m.name || m).join(', ')}</p>
        )}
      </div>
    </div>
  );
};

export default RankingDisplay;