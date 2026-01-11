# 🔮 Project Glitch: AI-Powered Football Prediction Bot

> **Status:** 🟢 Active | **Version:** 1.0.0 | **Accuracy:** ~52% (Multi-Market Average)

Project Glitch is a machine learning-powered Telegram bot that predicts football match outcomes for the English Premier League (EPL) and La Liga. It uses historical data, form analysis, and Random Forest algorithms to identify value bets in three key markets:
1.  **Match Result** (Home/Draw/Away)
2.  **Over/Under 2.5 Goals**
3.  **Both Teams to Score (BTTS)**

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from @BotFather)
- RapidAPI Key (API-Football)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/HarperKollins/Project-Glitch.git
    cd Project-Glitch
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```env
    TELEGRAM_TOKEN=your_telegram_token_here
    RAPIDAPI_KEY=your_rapidapi_key_here
    USE_MOCK_DATA=false  # Set to true to save API credits during dev
    ```

4.  **Run the Bot:**
    ```bash
    python main.py
    ```

---

## 🧠 Model Documentation

### The "Glitch" Engine (`glitch_engine.py`)
The core prediction logic is powered by **Random Forest Classifiers** (`sklearn.ensemble.RandomForestClassifier`). We train separate models for each betting market to maximize specificity.

### Data Pipeline
-   **Source:** Historical CSV data (`master_data.csv`) merged from EPL and La Liga seasons.
-   **Features:**
    -   **Rolling Form (5 games):** Points accumulated (W=3, D=1, L=0).
    -   **Goal Expectancy:** Avg goals scored/conceded (Last 5 home/away).
    -   **BTTS Rate:** Percentage of recent games where both teams scored.
-   **Preprocessing:** Time-based train/test split (80/20) to prevent data leakage (predicting past games using future data).

### Performance Metrics (Test Set)
| Market | Algorithm | Accuracy | ROI estimate |
| :--- | :--- | :--- | :--- |
| **Match Result** | Random Forest (n=200) | ~53% | +5% (Value Betting) |
| **Over/Under 2.5** | Random Forest (n=200) | ~55% | +8% |
| **BTTS** | Random Forest (n=200) | ~51% | Neutral |

> *Note: ROI depends heavily on odds availability. The model identifies probability; value is found where Model Probability > Implied Odds.*

---

## 📂 Project Structure

```
project-glitch/
├── data/                   # Raw CSV data files
├── tests/                  # Unit and smoke tests
├── data_manager.py         # API handling & Caching logic
├── glitch_engine.py        # Core ML prediction logic & feature engineering
├── main.py                 # Telegram Bot Interface (Async)
├── train_glitch.py         # Model training pipeline
├── requirements.txt        # Python dependencies
└── README.md               # You are here
```

---

## 🧪 Running Tests
We use `pytest` for ensuring system stability.

```bash
pytest tests/
```

---

## 📓 Reproducibility & Analysis
Check `analysis_notebook.ipynb` for a detailed Exploratory Data Analysis (EDA) and feature importance visualization.

**Key Findings:**
-   *Home Advantage* is a significant predictor in EPL.
-   *Recent Form* (last 5 games) correlates strongly with Match Result but weakly with Over/Under.
-   *Defensive stats* (Avg Conceded) are the best predictor for "Over 2.5 Goals".

---

## 📜 License
MIT License. Created by [Harper Kollins].
