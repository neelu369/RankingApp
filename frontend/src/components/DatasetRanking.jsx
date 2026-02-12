import React, { useState } from 'react';
import axios from 'axios';

const DatasetRanking = ({ onRankingComplete }) => {
  const [file, setFile] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [weights, setWeights] = useState({});
  const [useAutoMetrics, setUseAutoMetrics] = useState(true);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(10);


  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      alert('Please upload a CSV file');
      return;
    }

    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const requestData = {
        top_k: topK,
        metrics: useAutoMetrics ? null : metrics,
        weights: Object.keys(weights).length > 0 ? weights : null,
        sources: null
      };
      
      formData.append('request_data', JSON.stringify(requestData));

      const response = await axios.post('http://localhost:8000/api/rank/dataset', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      onRankingComplete(response.data);
    } catch (error) {
      console.error('Error ranking dataset:', error);
      alert('Error ranking dataset: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addMetric = () => {
    setMetrics([...metrics, { name: '', type: 'numerical', higher_is_better: true }]);
  };

  const updateMetric = (index, field, value) => {
    const newMetrics = [...metrics];
    newMetrics[index][field] = value;
    setMetrics(newMetrics);
  };

  const removeMetric = (index) => {
    setMetrics(metrics.filter((_, i) => i !== index));
  };

  const updateWeight = (metricName, weight) => {
    setWeights({ ...weights, [metricName]: parseFloat(weight) });
  };

  return (
    <div className="dataset-ranking">
      <h2>📊 Dataset Mode</h2>
      <p>Upload your CSV and rank the data by custom metrics</p>

      <div className="form-group">
        <label>Show Top Results:</label>
        <input
          type="number"
          min="1"
          max="100"
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value))}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Upload CSV File:</label>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="file-input"
          />
          {file && <span className="file-name">✓ {file.name}</span>}
        </div>

        <div className="form-group">
          <label>
            <input
              type="radio"
              checked={useAutoMetrics}
              onChange={() => setUseAutoMetrics(true)}
            />
            Auto-detect metrics from CSV
          </label>
          <label>
            <input
              type="radio"
              checked={!useAutoMetrics}
              onChange={() => setUseAutoMetrics(false)}
            />
            Specify metrics manually
          </label>
        </div>

        {!useAutoMetrics && (
          <div className="metrics-editor">
            <h3>Define Metrics</h3>
            {metrics.map((metric, index) => (
              <div key={index} className="metric-row">
                <input
                  type="text"
                  value={metric.name}
                  onChange={(e) => updateMetric(index, 'name', e.target.value)}
                  placeholder="Metric name (must match CSV column)"
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
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  placeholder="Weight (0-1)"
                  onChange={(e) => updateWeight(metric.name, e.target.value)}
                  className="weight-input"
                />
                <button
                  type="button"
                  onClick={() => removeMetric(index)}
                  className="btn-remove"
                >
                  ✕
                </button>
              </div>
            ))}
            <button type="button" onClick={addMetric} className="btn-secondary">
              + Add Metric
            </button>
          </div>
        )}

        <button type="submit" className="btn-primary" disabled={loading || !file}>
          {loading ? 'Ranking...' : '🚀 Rank Dataset'}
        </button>
      </form>

      <div className="info-box">
        <h4>CSV Format:</h4>
        <p>Your CSV should have:</p>
        <ul>
          <li>A column for entity names (e.g., "name", "company", "incubator")</li>
          <li>Columns for each metric you want to rank by</li>
          <li>Example: name, funding, employees, revenue, rating</li>
        </ul>
      </div>
    </div>
  );
};

export default DatasetRanking;
