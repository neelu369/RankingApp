import React, { useState } from 'react';

const RankingDisplay = ({ ranking, metrics, onEntitySelect }) => {
  const [sortBy, setSortBy] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');

  const sortedRanking = [...ranking].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    
    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const getRankBadge = (rank) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return rank;
  };

  return (
    <div className="ranking-display">
      <h2>📊 Ranking Results</h2>
      <p className="results-count">{ranking.length} entities ranked</p>

      <div className="table-container">
        <table className="ranking-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('rank')} className="sortable">
                Rank {sortBy === 'rank' && (sortOrder === 'asc' ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('name')} className="sortable">
                Entity {sortBy === 'name' && (sortOrder === 'asc' ? '▲' : '▼')}
              </th>
              {/* Score column removed per user request - only show chosen metrics */}
              {metrics.map((metric) => (
                <th
                  key={metric.name}
                  onClick={() => handleSort(metric.name)}
                  className="sortable"
                >
                  {metric.name} {sortBy === metric.name && (sortOrder === 'asc' ? '▲' : '▼')}
                </th>
              ))}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedRanking.map((entity, index) => (
              <tr
                key={index}
                className={entity.rank <= 3 ? 'top-three' : ''}
              >
                <td className="rank-cell">{getRankBadge(entity.rank)}</td>
                <td className="entity-name">{entity.name}</td>
                {/* final_score intentionally omitted; show only entity name and selected metrics */}
                {metrics.map((metric) => (
                  <td key={metric.name} className="metric-cell">
                    {typeof entity[metric.name] === 'number'
                      ? entity[metric.name].toFixed(2)
                      : entity[metric.name]}
                  </td>
                ))}
                <td>
                  <button
                    onClick={() => onEntitySelect(entity)}
                    className="btn-insight"
                  >
                    💡 Insights
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ranking-summary">
        <h3>Top Performers</h3>
        <div className="top-performers">
          {sortedRanking.slice(0, 3).map((entity) => (
            <div key={entity.rank} className="performer-card">
              <div className="performer-rank">{getRankBadge(entity.rank)}</div>
              <div className="performer-name">{entity.name}</div>
              {/* Score omitted */}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RankingDisplay;
