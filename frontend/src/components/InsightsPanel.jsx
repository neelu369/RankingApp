import React, { useState, useEffect } from "react";
import axios from "axios";

const InsightsPanel = ({ entity, rankingId }) => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 🔹 Resolve entity name safely
  const resolveEntityName = () => {
    if (!entity) return null;

    return (
      entity.name ||
      entity.entity ||
      entity.title ||
      entity.label ||
      null
    );
  };

  const entityName = resolveEntityName();

  // 🔹 Only fetch when data is ready
  useEffect(() => {
    if (!rankingId || !entityName) return;

    fetchInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rankingId, entityName]);

  const fetchInsights = async () => {
    if (!rankingId || !entityName) {
      console.warn("Insights skipped: missing rankingId or entityName", {
        rankingId,
        entityName,
      });
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      ranking_id: rankingId,
      entity_name: entityName,
    };

    console.log("📡 Fetching insights:", payload);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/insights",
        payload,
        {
          headers: {
            "Content-Type": "application/json",
          },
          timeout: 30000, // 30s timeout for LLM
        }
      );

      console.log("✅ Insights received:", response.data);

      setInsights(response.data);
    } catch (err) {
      console.error("❌ Insights error:", err);

      const backendMsg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message;

      setError("Failed to fetch insights: " + backendMsg);
    } finally {
      setLoading(false);
    }
  };

  // =============================
  // UI STATES
  // =============================

  if (!rankingId || !entityName) {
    return (
      <div className="insights-panel empty">
        <p>ℹ️ Select an entity to view insights.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="insights-panel loading">
        <div>⏳ Generating insights...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="insights-panel error">
        <h3>⚠️ Error</h3>
        <p>{error}</p>

        <button onClick={fetchInsights} className="btn-retry">
          🔄 Retry
        </button>
      </div> 
    );
  }

  if (!insights) {
    return (
      <div className="insights-panel empty">
        <p>ℹ️ No insights available.</p>
      </div>
    );
  }

  // =============================
  // MAIN RENDER
  // =============================

  return (
    <div className="insights-panel">
      {/* Header */}
      <div className="insights-header">
        <h3>💡 Insights for {insights.entity}</h3>

        {insights.rank !== undefined && (
          <div className="entity-rank">Rank: #{insights.rank}</div>
        )}
      </div>

      {/* Content */}
      <div className="insights-content">
        {/* Metrics */}
        <div className="metrics-overview">
          <h4>📊 Metrics Overview</h4>

          <div className="metrics-grid">
            {insights.metrics &&
              Object.entries(insights.metrics).map(([key, value]) => (
                <div key={key} className="metric-card">
                  <div className="metric-label">
                    {key.replace(/_/g, " ")}
                  </div>

                  <div className="metric-value">
                    {typeof value === "number"
                      ? value.toFixed(2)
                      : String(value)}
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* AI Insights */}
        <div className="ai-insights">
          <h4>🤖 AI Analysis</h4>

          <div className="insights-text">
            {insights.insights || "No analysis generated."}
          </div>
        </div>

        {/* Actions */}
        <div className="insights-actions">
          <button onClick={fetchInsights} className="btn-secondary">
            🔄 Refresh Insights
          </button>
        </div>
      </div>
    </div>
  );
};

export default InsightsPanel;
