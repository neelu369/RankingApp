# 🏆 Universal Ranking App

A comprehensive, dynamic ranking application that can rank **anything** by **any metrics** using AI-powered web crawling and data analysis.

## 🌟 Features

### Two Powerful Modes

#### 📊 Dataset Mode
- Upload CSV files with your data
- Auto-detect or manually specify metrics
- Configure metric weights and normalization
- Get instant rankings with detailed scores

#### 🌐 Crawler Mode
- Ask natural language ranking queries (e.g., "Top 10 incubators in India")
- AI automatically understands your intent
- Crawls the web for relevant data
- Suggests appropriate metrics and sources
- Creates comprehensive rankings from live data

### Core Capabilities

✅ **Universal Ranking** - Rank any entity type (companies, products, people, teams, etc.)  
✅ **Dynamic Metrics** - Use any combination of numerical or categorical metrics  
✅ **Smart Normalization** - Multiple normalization strategies (MinMax, Standard, Robust)  
✅ **AI-Powered Insights** - Get detailed analysis for any ranked entity    
✅ **Live Data Integration** - Connect to real-time data sources and APIs  
✅ **Reranking** - Update metrics and see rankings change in real-time  
✅ **Comparison Engine** - Compare entities side-by-side  
✅ **Bias Detection** - Detect outliers and ensure fair rankings

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              User Interface (React)              │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         FastAPI Backend (Python)                 │
│  ┌─────────────────────────────────────────┐   │
│  │  LangGraph Agent (Orchestration)        │   │
│  └─────┬───────────────────────────┬───────┘   │
│        │                           │             │
│  ┌─────▼──────┐           ┌────────▼────────┐  │
│  │  LLM       │           │  Ranking        │  │
│  │ Interface  │           │  Engine         │  │
│  │ (Replicate)│           │ (Algorithms)    │  │
│  └─────┬──────┘           └────────┬────────┘  │
│        │                           │             │
│  ┌─────▼──────┐           ┌────────▼────────┐  │
│  │  Crawler   │           │  Vector DB      │  │
│  │ (Crawl4AI) │           │  (MongoDB)      │  │
│  └────────────┘           └─────────────────┘  │
└─────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: React 18, Axios
- **AI/ML**: 
  - Replicate (LLM inference)
  - LangChain (LLM orchestration)
  - LangGraph (Agent workflows)
- **Web Crawling**: Crawl4AI
- **Database**: MongoDB (Vector storage)
- **Data Processing**: Pandas, NumPy, scikit-learn

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 16 or higher
- MongoDB (local or Atlas)
- Replicate API key
- OpenAI API key (for Crawl4AI)

### Backend Setup

```bash
# Navigate to project directory
cd ranking-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys:
# REPLICATE_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# MONGODB_URI=mongodb://localhost:27017

# Install Playwright browsers (for Crawl4AI)
playwright install

# Run the backend
cd backend
python main.py
```

Backend will run at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd ranking-app/frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will run at `http://localhost:3000`

## 🚀 Usage

### Dataset Mode Example

1. **Prepare your CSV file**
   ```csv
   name,funding,employees,revenue,rating
   Startup A,5000000,50,2000000,4.5
   Startup B,10000000,100,5000000,4.8
   Startup C,2000000,25,1000000,4.2
   ```

2. **Upload and Configure**
   - Click "Dataset Mode"
   - Upload your CSV
   - Choose "Auto-detect metrics" or specify manually
   - Click "Rank Dataset"

3. **View Results**
   - See ranked table with all metrics
   - Click "Insights" on any entity for detailed analysis
   - Compare entities side-by-side

### Crawler Mode Example

1. **Ask a Ranking Question**
   ```
   "Top 10 AI startups in India by funding and innovation"
   ```

2. **Configure Metrics** (or let AI suggest)
   - Total Funding
   - Team Size
   - Innovation Score
   - Market Presence

3. **Specify Sources** (optional)
   - Let AI find sources automatically
   - Or provide specific URLs/domains

4. **Get Results**
   - AI crawls the web for data
   - Creates comprehensive ranking
   - Provides insights for each entity

## 📊 API Endpoints

### Ranking Endpoints

```bash
# Crawler-based ranking
POST /api/rank/crawler
Body: {
  "query": "Top 10 incubators in India",
  "num_results": 10,
  "metrics": [...],  # Optional
  "sources": [...]   # Optional
}

# Dataset-based ranking
POST /api/rank/dataset
Form Data: file (CSV)
Body: {
  "metrics": [...],
  "weights": {...},
  "sources": [...]
}

# Get insights for an entity
POST /api/insights
Body: {
  "entity_name": "Example Inc",
  "ranking_id": "uuid"
}

# Rerank with updated metrics
POST /api/rerank
Body: {
  "ranking_id": "uuid",
  "updated_metrics": {
    "Entity A": {"metric1": 100, "metric2": 50}
  }
}

# Compare entities
POST /api/compare
Body: {
  "ranking_id": "uuid",
  "entity1": "Entity A",
  "entity2": "Entity B"
}

# Get recent rankings
GET /api/rankings/recent?limit=10

# Suggest metrics
POST /api/suggest/metrics
Body: {
  "entity_type": "startup",
  "domain": "technology"
}
```

## 🔧 Configuration

### Ranking Algorithm Options

The ranking engine supports multiple normalization methods:

```python
# In your API call or code
{
  "normalization": "minmax",  # Options: "minmax", "standard", "robust"
  "constraints": {
    "detect_outliers": true,
    "min_values": {...},
    "max_values": {...}
  }
}
```

### Metric Configuration

```python
{
  "name": "funding",
  "type": "numerical",  # or "categorical"
  "higher_is_better": true,
  "weight": 0.3  # Optional, defaults to equal weights
}
```

## 📁 Project Structure

```
ranking-app/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── agent.py                # LangGraph agent
│   ├── llm_interface.py        # Replicate/LangChain integration
│   ├── crawler.py              # Crawl4AI web crawler
│   ├── ranking_engine.py       # Core ranking algorithms
│   └── vector_db.py            # MongoDB integration
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── components/
│   │       ├── CrawlerRanking.jsx
│   │       ├── DatasetRanking.jsx
│   │       ├── RankingDisplay.jsx
│   │       └── InsightsPanel.jsx
│   └── package.json
├── config/
│   └── settings.py             # Configuration management
├── requirements.txt
├── .env.example
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with Replicate, LangChain, LangGraph, Crawl4AI, and MongoDB
- Inspired by the need for a universal, dynamic ranking system

## 📧 Support

For issues and questions, please open an issue on the GitHub repository.

---

**Made with ❤️ for data-driven decision making**
