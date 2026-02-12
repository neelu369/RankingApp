import React, { useState } from 'react';
import axios from 'axios';

const CrawlerRanking = ({ onRankingComplete }) => {
  const [query, setQuery] = useState('');
  const [numResults, setNumResults] = useState(10);
  const [metrics, setMetrics] = useState([]);
  const [previewEntities, setPreviewEntities] = useState([]);
  const [sources, setSources] = useState([]);
  const [useSystemMetrics, setUseSystemMetrics] = useState(true);
  const [useSystemSources, setUseSystemSources] = useState(true);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // 1: query, 2: metrics, 3: sources

  const handleSubmitQuery = async () => {
    if (!query.trim()) return;
    // Request a preview from backend: suggested metrics and entities
    try {
      const resp = await axios.post('http://localhost:8000/api/preview', {
        query,
        num_results: numResults
      });

      if (resp.data && resp.data.success) {
        const suggested = resp.data.metrics || [];
        // add enabled flag so user can toggle metrics on/off
        setMetrics(suggested.map((m) => ({ ...m, enabled: true })));
        setPreviewEntities(resp.data.entities || []);
      }
      setStep(2);
    } catch (err) {
      console.error('Preview error', err);
      // Fallback: still move to metrics step
      setStep(2);
    }
  };

  const handleSubmitMetrics = () => {
    setStep(3);
  };

  const handleSubmitRanking = async () => {
    setLoading(true);
    try {
      // Prepare metrics to send: only include enabled ones and minimal fields
      const chosenMetrics = metrics && metrics.length > 0
        ? metrics.filter((m) => m.enabled !== false).map((m) => ({
            name: m.name,
            type: m.type || 'numerical',
            higher_is_better: m.higher_is_better !== false
          }))
        : null;

      const response = await axios.post('http://localhost:8000/api/rank/crawler', {
        query,
        num_results: numResults,
        metrics: chosenMetrics,
        sources: useSystemSources ? null : sources,
        entities: previewEntities && previewEntities.length > 0 ? previewEntities : null
      });

      onRankingComplete(response.data);
    } catch (error) {
      console.error('Error creating ranking:', error);
      alert('Error creating ranking: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addMetric = () => {
    setMetrics([...metrics, { name: '', type: 'numerical', higher_is_better: true, enabled: true }]);
  };

  const updateMetric = (index, field, value) => {
    const newMetrics = [...metrics];
    newMetrics[index][field] = value;
    setMetrics(newMetrics);
  };

  const removeMetric = (index) => {
    setMetrics(metrics.filter((_, i) => i !== index));
  };

  const addSource = () => {
    setSources([...sources, '']);
  };

  const updateSource = (index, value) => {
    const newSources = [...sources];
    newSources[index] = value;
    setSources(newSources);
  };

  const removeSource = (index) => {
    setSources(sources.filter((_, i) => i !== index));
  };

  return (
    <div className="crawler-ranking">
      <h2>🌐 Crawler Mode</h2>
      <p>Ask a ranking question and let AI crawl the web for data</p>

      {step === 1 && (
        <div className="step-container">
          <h3>Step 1: What do you want to rank?</h3>
          <div className="form-group">
            <label>Ranking Query:</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Top 10 incubators in India"
              className="query-input"
            />
          </div>
          <div className="form-group">
            <label>Number of Results:</label>
            <input
              type="number"
              value={numResults}
              onChange={(e) => setNumResults(parseInt(e.target.value))}
              min="1"
              max="100"
            />
          </div>
          <button onClick={handleSubmitQuery} className="btn-primary">
            Next: Choose Metrics →
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="step-container">
          <h3>Step 2: Choose Metrics</h3>
          <div className="form-group">
            <label>
              <input
                type="radio"
                checked={useSystemMetrics}
                onChange={() => setUseSystemMetrics(true)}
              />
              Let the system suggest metrics (shown below)
            </label>
            <label>
              <input
                type="radio"
                checked={!useSystemMetrics}
                onChange={() => setUseSystemMetrics(false)}
              />
              I'll specify my own metrics
            </label>
          </div>

          {useSystemMetrics && metrics && metrics.length > 0 && (
            <div className="suggested-metrics">
              <h4>Suggested metrics</h4>
              {metrics.map((metric, index) => (
                <div key={index} className="metric-row">
                  <label>
                    <input
                      type="checkbox"
                      checked={metric.enabled !== false}
                      onChange={(e) => updateMetric(index, 'enabled', e.target.checked)}
                    />
                    <strong>{metric.name}</strong> — {metric.description || ''}
                  </label>
                </div>
              ))}
              <button onClick={() => setUseSystemMetrics(false)} className="btn-secondary">
                Customize metrics →
              </button>
            </div>
          )}

          {!useSystemMetrics && (
            <div className="metrics-editor">
              {metrics.map((metric, index) => (
                <div key={index} className="metric-row">
                  <input
                    type="text"
                    value={metric.name}
                    onChange={(e) => updateMetric(index, 'name', e.target.value)}
                    placeholder="Metric name"
                  />
                  <select
                    value={metric.type}
                    onChange={(e) => updateMetric(index, 'type', e.target.value)}
                  >
                    <option value="numerical">Numerical</option>
                    <option value="categorical">Categorical</option>
                  </select>
                  <label>
                    <input
                      type="checkbox"
                      checked={metric.higher_is_better}
                      onChange={(e) => updateMetric(index, 'higher_is_better', e.target.checked)}
                    />
                    Higher is better
                  </label>
                  <button onClick={() => removeMetric(index)} className="btn-remove">
                    ✕
                  </button>
                </div>
              ))}
              <button onClick={addMetric} className="btn-secondary">
                + Add Metric
              </button>
            </div>
          )}

          <div className="button-group">
            <button onClick={() => setStep(1)} className="btn-secondary">
              ← Back
            </button>
            <button onClick={handleSubmitMetrics} className="btn-primary">
              Next: Choose Sources →
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="step-container">
          <h3>Step 3: Choose Data Sources</h3>
          <div className="form-group">
            <label>
              <input
                type="radio"
                checked={useSystemSources}
                onChange={() => setUseSystemSources(true)}
              />
              Let the system find sources
            </label>
            <label>
              <input
                type="radio"
                checked={!useSystemSources}
                onChange={() => setUseSystemSources(false)}
              />
              I'll provide source URLs
            </label>
          </div>

          {!useSystemSources && (
            <div className="sources-editor">
              {sources.map((source, index) => (
                <div key={index} className="source-row">
                  <input
                    type="text"
                    value={source}
                    onChange={(e) => updateSource(index, e.target.value)}
                    placeholder="https://example.com"
                  />
                  <button onClick={() => removeSource(index)} className="btn-remove">
                    ✕
                  </button>
                </div>
              ))}
              <button onClick={addSource} className="btn-secondary">
                + Add Source
              </button>
            </div>
          )}

          <div className="button-group">
            <button onClick={() => setStep(2)} className="btn-secondary">
              ← Back
            </button>
            <button onClick={handleSubmitRanking} className="btn-primary" disabled={loading}>
              {loading ? 'Creating Ranking...' : '🚀 Create Ranking'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrawlerRanking;
