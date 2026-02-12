import React, { useState } from 'react';
import './App.css';
import CrawlerRanking from './components/CrawlerRanking';
import DatasetRanking from './components/DatasetRanking';
import RankingDisplay from './components/RankingDisplay';
import InsightsPanel from './components/InsightsPanel';

function App() {
  const [mode, setMode] = useState('crawler'); // 'crawler' or 'dataset'
  const [rankingResult, setRankingResult] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);

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
          <CrawlerRanking onRankingComplete={setRankingResult} />
        ) : (
          <DatasetRanking onRankingComplete={setRankingResult} />
        )}

        {rankingResult && (
          <div className="results-section">
            <RankingDisplay
              ranking={rankingResult.ranking}
              metrics={rankingResult.metrics_used}
              onEntitySelect={setSelectedEntity}
            />

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
        <p>Powered by Replicate, LangChain, LangGraph, Crawl4AI & MongoDB</p>
      </footer>
    </div>
  );
}

export default App;
