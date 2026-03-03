import React, { useState } from 'react';
import './App.css';
import CrawlerRanking from './components/CrawlerRanking';
import DatasetRanking from './components/DatasetRanking';
import RankingDisplay from './components/RankingDisplay';
import InsightsPanel from './components/InsightsPanel';
import ReRankingPanel from './components/RerankingPanel';
import TokenUsage from './components/TokenUsage';


function App() {
  const [mode, setMode] = useState('crawler'); // 'crawler' or 'dataset'
  const [rankingResult, setRankingResult] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [showReRankPanel, setShowReRankPanel] = useState(false);

  const handleRankingComplete = (result) => {
    setRankingResult(result);
    setShowReRankPanel(false); // Hide re-rank panel for new ranking
    setSelectedEntity(null);
  };

  const handleReRankComplete = (result) => {
    // Update with new ranking
    setRankingResult({
      ...rankingResult,
      ranking: result.ranking,
      ranking_id: result.new_ranking_id,
      optimization: result.optimization_report
    });
    setShowReRankPanel(false); // Close panel after re-ranking
    
    // Show notification
    if (result.changes && result.changes.length > 0) {
      alert(`✅ Re-ranking complete! ${result.changes.length} positions changed.`);
    } else {
      alert(`✅ Re-ranking complete! Rankings remain similar.`);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🏆 Universal Ranking App</h1>
        <p>Rank anything, anywhere, by any metric</p>
      </header>

      <div className="mode-selector">
        <button
          className={mode === 'crawler' ? 'active' : ''}
          onClick={() => setMode('crawler')}
        >
          🌐 Crawler Mode
        </button>
        <button
          className={mode === 'dataset' ? 'active' : ''}
          onClick={() => setMode('dataset')}
        >
          📊 Dataset Mode
        </button>
      </div>

      <div className="main-content">
        {mode === 'crawler' ? (
          <CrawlerRanking onRankingComplete={handleRankingComplete} />
        ) : (
          <DatasetRanking onRankingComplete={handleRankingComplete} />
        )}

        {rankingResult && (
          <div className="results-section">
            {/* Re-ranking Control Button */}
            <div className="rerank-control">
              <button
                className="btn-toggle-rerank"
                onClick={() => setShowReRankPanel(!showReRankPanel)}
              >
                {showReRankPanel ? '🔼 Hide Re-Ranking Controls' : '🔄 Not Happy? Re-Rank!'}
              </button>
            </div>

            {/* Re-Ranking Panel */}
            {showReRankPanel && (
              <ReRankingPanel
                rankingResult={rankingResult}
                onReRankComplete={handleReRankComplete}
              />
            )}

            {/* Ranking Display */}
            <RankingDisplay
              ranking={rankingResult.ranking}
              metrics={rankingResult.metrics_used}
              onEntitySelect={setSelectedEntity}
            />

            {/* Insights Panel */}
            {selectedEntity && (
              <InsightsPanel
                entity={selectedEntity}
                rankingId={rankingResult.ranking_id}
              />
            )}
          </div>
        )}
      </div>

      <footer className="App-footer">
        <div className="footer-content">
          <p>Powered by Replicate, LangChain, LangGraph, Crawl4AI & MongoDB</p>
          <TokenUsage />
        </div>
      </footer>
    </div>
  );
}

export default App;