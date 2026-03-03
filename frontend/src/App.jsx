import React, { useState } from 'react';
import './App.css';
import CrawlerRanking from './components/CrawlerRanking';
import RankingDisplay from './components/RankingDisplay';
import InsightsPanel from './components/InsightsPanel';
import ReRankingPanel from './components/RerankingPanel';
import TokenUsage from './components/TokenUsage';

function App() {
  const [rankingResult, setRankingResult] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [showReRankPanel, setShowReRankPanel] = useState(false);

  const handleRankingComplete = (result) => {
    setRankingResult(result);
    setShowReRankPanel(false);
    setSelectedEntity(null);
  };

  const handleReRankComplete = (result) => {
    setRankingResult({
      ...rankingResult,
      ranking: result.ranking,
      ranking_id: result.new_ranking_id,
      optimization: result.optimization_report,
    });
    setShowReRankPanel(false);
    const msg = result.changes?.length > 0
      ? `Re-ranking complete — ${result.changes.length} positions changed.`
      : 'Re-ranking complete — rankings remain similar.';
    alert(msg);
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-brand">
            <h1>rank<span className="dot">.</span></h1>
            <p className="subtitle">rank anything · anywhere · by any metric</p>
          </div>
          <TokenUsage />
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <CrawlerRanking onRankingComplete={handleRankingComplete} />
        </aside>

        <main className="content">
          {rankingResult ? (
            <div className="results-wrapper">
              <div className="results-actions">
                <button
                  className="btn-toggle-rerank"
                  onClick={() => setShowReRankPanel(!showReRankPanel)}
                >
                  {showReRankPanel ? 'Hide controls' : 'Re-rank →'}
                </button>
              </div>

              {showReRankPanel && (
                <ReRankingPanel
                  rankingResult={rankingResult}
                  onReRankComplete={handleReRankComplete}
                />
              )}

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
          ) : (
            <div className="empty-card">
              <p className="empty-eyebrow">Universal Ranking Engine</p>
              <h2>Rank<br /><em>anything.</em></h2>
              <p>Enter a query in the panel — the AI crawls the web, scores entities across your chosen metrics, and surfaces ranked results.</p>
            </div>
          )}
        </main>
      </div>

      <footer className="App-footer">
        <div className="footer-content">
          <p>Powered by Replicate · LangChain · LangGraph · Crawl4AI · MongoDB</p>
          <p>rank. — Universal Ranking App</p>
        </div>
      </footer>
    </div>
  );
}

export default App;