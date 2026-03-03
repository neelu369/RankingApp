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
  const [step, setStep] = useState(1);
  const [isIncubatorQuery, setIsIncubatorQuery] = useState(false);

  const handleSubmitQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const resp = await axios.post('http://localhost:8000/api/preview', { query, num_results: numResults });
      if (resp.data?.success) {
        const suggested = resp.data.metrics || [];
        const intent = resp.data.intent || {};
        const isIncubator = intent.entity_type === 'incubator' || intent.entity_type === 'accelerator';
        setIsIncubatorQuery(isIncubator);
        setMetrics(suggested.map((m) => ({ ...m, enabled: true })));
        setPreviewEntities(resp.data.entities || []);
      }
      setStep(2);
    } catch (err) {
      console.error('Preview error', err);
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRanking = async () => {
    setLoading(true);
    try {
      const chosenMetrics = metrics?.length > 0
        ? metrics.filter((m) => m.enabled !== false).map((m) => ({
            name: m.name, type: m.type || 'numerical',
            higher_is_better: m.higher_is_better !== false,
            description: m.description || '', unit: m.unit || '', benchmark: m.benchmark || 0
          }))
        : null;

      const response = await axios.post('http://localhost:8000/api/rank/crawler', {
        query, num_results: numResults, metrics: chosenMetrics,
        sources: useSystemSources ? null : sources,
        entities: previewEntities?.length > 0 ? previewEntities : null
      });
      onRankingComplete(response.data);
    } catch (error) {
      console.error('Error creating ranking:', error);
      alert('Error creating ranking: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addMetric = () => setMetrics([...metrics, { name: '', type: 'numerical', higher_is_better: true, enabled: true }]);
  const updateMetric = (i, field, value) => { const n = [...metrics]; n[i][field] = value; setMetrics(n); };
  const removeMetric = (i) => setMetrics(metrics.filter((_, idx) => idx !== i));
  const addSource = () => setSources([...sources, '']);
  const updateSource = (i, value) => { const n = [...sources]; n[i] = value; setSources(n); };
  const removeSource = (i) => setSources(sources.filter((_, idx) => idx !== i));

  return (
    <div className="crawler-ranking">

      {/* ── STEP 1 ── */}
      {step === 1 && (
        <div className="step-container">
          <p className="form-section-label">Step 1 / 3</p>
          <h2 className="step-title">What do<br />you want<br />to rank?</h2>

          <div className="form-group">
            <label>Your query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !loading && query.trim() && handleSubmitQuery()}
              placeholder="e.g. Top 10 incubators in India"
              className="query-input"
            />
          </div>

          <div className="form-group">
            <label>Number of results</label>
            <input
              type="number"
              value={numResults}
              onChange={(e) => setNumResults(parseInt(e.target.value))}
              min="1"
              max="100"
            />
          </div>

          <button onClick={handleSubmitQuery} className="btn-primary" disabled={loading || !query.trim()}>
            {loading ? 'Analysing…' : 'Continue →'}
          </button>
        </div>
      )}

      {/* ── STEP 2 ── */}
      {step === 2 && (
        <div className="step-container">
          <p className="form-section-label">Step 2 / 3</p>
          <h2 className="step-title">Choose<br />your<br />metrics</h2>

          {isIncubatorQuery && (
            <div className="info-banner">
              Research-based incubator metrics selected
            </div>
          )}

          <div className="form-group">
            <label>
              <input type="radio" checked={useSystemMetrics} onChange={() => setUseSystemMetrics(true)} />
              {isIncubatorQuery ? 'Use validated research metrics' : 'AI-suggested metrics'}
            </label>
            <label>
              <input type="radio" checked={!useSystemMetrics} onChange={() => setUseSystemMetrics(false)} />
              Define my own
            </label>
          </div>

          {useSystemMetrics && metrics?.length > 0 && (
            <div className="suggested-metrics">
              <h4>
                {isIncubatorQuery ? 'Research metrics' : 'Suggested metrics'}
                {isIncubatorQuery && <span className="badge">Validated</span>}
              </h4>
              {metrics.map((metric, index) => (
                <div key={index} className="metric-row">
                  <label className="metric-checkbox">
                    <input
                      type="checkbox"
                      checked={metric.enabled !== false}
                      onChange={(e) => updateMetric(index, 'enabled', e.target.checked)}
                    />
                    <div className="metric-details">
                      <strong>{metric.name}</strong>
                      {metric.description && <p className="metric-desc">{metric.description}</p>}
                      {metric.unit && <span className="metric-unit">{metric.unit}</span>}
                      {metric.benchmark && <span className="metric-benchmark">Benchmark: {metric.benchmark}</span>}
                    </div>
                  </label>
                </div>
              ))}
            </div>
          )}

          {!useSystemMetrics && (
            <div className="metrics-editor">
              {metrics.map((metric, index) => (
                <div key={index} className="metric-row">
                  <input type="text" value={metric.name}
                    onChange={(e) => updateMetric(index, 'name', e.target.value)}
                    placeholder="Metric name" />
                  <select value={metric.type} onChange={(e) => updateMetric(index, 'type', e.target.value)}>
                    <option value="numerical">Numerical</option>
                    <option value="categorical">Categorical</option>
                  </select>
                  <label>
                    <input type="checkbox" checked={metric.higher_is_better}
                      onChange={(e) => updateMetric(index, 'higher_is_better', e.target.checked)} />
                    Higher is better
                  </label>
                  <button onClick={() => removeMetric(index)} className="btn-remove">✕</button>
                </div>
              ))}
              <button onClick={addMetric} className="btn-secondary" style={{ marginTop: 10, alignSelf: 'stretch', textAlign: 'center' }}>
                + Add metric
              </button>
            </div>
          )}

          <div className="button-group" style={{ marginTop: 'auto', paddingTop: 20 }}>
            <button onClick={() => setStep(1)} className="btn-secondary">← Back</button>
            <button onClick={() => setStep(3)} className="btn-primary">Continue →</button>
          </div>
        </div>
      )}

      {/* ── STEP 3 ── */}
      {step === 3 && (
        <div className="step-container">
          <p className="form-section-label">Step 3 / 3</p>
          <h2 className="step-title">Data<br />sources</h2>

          <div className="form-group">
            <label>
              <input type="radio" checked={useSystemSources} onChange={() => setUseSystemSources(true)} />
              Live web (recommended)
            </label>
            <label>
              <input type="radio" checked={!useSystemSources} onChange={() => setUseSystemSources(false)} />
              Provide source URLs
            </label>
          </div>

          {!useSystemSources && (
            <div className="sources-editor">
              {sources.map((source, index) => (
                <div key={index} className="source-row">
                  <input type="text" value={source}
                    onChange={(e) => updateSource(index, e.target.value)}
                    placeholder="https://example.com" />
                  <button onClick={() => removeSource(index)} className="btn-remove">✕</button>
                </div>
              ))}
              <button onClick={addSource} className="btn-secondary" style={{ marginTop: 6 }}>
                + Add source
              </button>
            </div>
          )}

          <div className="button-group" style={{ marginTop: 'auto', paddingTop: 20 }}>
            <button onClick={() => setStep(2)} className="btn-secondary">← Back</button>
            <button onClick={handleSubmitRanking} className="btn-primary" disabled={loading}>
              {loading ? 'Ranking…' : 'Create ranking'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrawlerRanking;