import React from 'react';
// Styles live in App.css — no separate import needed

const RankingDisplay = ({ ranking, metrics, onEntitySelect }) => {
  if (!ranking) {
    return (
      <div className="ranking-display">
        <div className="no-data"><p>No ranking data available</p></div>
      </div>
    );
  }

  const rankingArray = Array.isArray(ranking) ? ranking : [];
  if (rankingArray.length === 0) {
    return (
      <div className="ranking-display">
        <div className="no-data"><p>No entities to display</p></div>
      </div>
    );
  }

  const metricsArray = Array.isArray(metrics) ? metrics : [];

  return (
    <div className="ranking-display">
      <div className="ranking-display-header">
        <div>
          <span className="ranking-eyebrow">Results</span>
          <h2>Ranking</h2>
        </div>
        <span className="ranking-count-pill">{rankingArray.length} entities</span>
      </div>

      <div className="ranking-table-container">
        <table className="ranking-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              {metricsArray.map((metric, idx) => (
                <th key={idx}>{metric.name || metric}</th>
              ))}
              <th>Score</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rankingArray.map((entity, index) => {
              const entityName = entity.name || entity.entity || entity.title || 'Unknown';
              const rank = entity.rank || index + 1;
              const score = entity.final_score || entity.score || 0;
              const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : null;

              return (
                <tr key={index} className={index < 3 ? `top-${index + 1}` : ''}>
                  <td>
                    <div className="rank-cell">
                      <span className="rank-badge">{rank}</span>
                      {medal && <span className="trophy">{medal}</span>}
                    </div>
                  </td>
                  <td className="name-cell"><strong>{entityName}</strong></td>
                  {metricsArray.map((metric, idx) => {
                    const metricName = metric.name || metric;
                    const value = entity[metricName];
                    return (
                      <td key={idx} className="metric-cell">
                        {value !== null && value !== undefined
                          ? typeof value === 'number' ? value.toLocaleString() : value
                          : '—'}
                      </td>
                    );
                  })}
                  <td className="score-cell">
                    <div className="score-bar-container">
                      <div className="score-bar" style={{ width: `${(score * 100).toFixed(0)}%` }} />
                    </div>
                    <span className="score-text">{(score * 100).toFixed(1)}%</span>
                  </td>
                  <td>
                    {onEntitySelect && (
                      <button className="btn-details" onClick={() => onEntitySelect(entity)}>
                        Details
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
        <p>{rankingArray.length} entities ranked</p>
        {metricsArray.length > 0 && (
          <p>By: {metricsArray.map(m => m.name || m).join(' · ')}</p>
        )}
      </div>
    </div>
  );
};

export default RankingDisplay;