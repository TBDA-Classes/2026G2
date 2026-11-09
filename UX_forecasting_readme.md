# ⚡ Multi-Zone Building Energy Forecasting Dashboard (Mockup)

An interactive **Streamlit** dashboard designed to visualize, monitor, and compare energy consumption predictions across four distinct building zones in real time.

## 📌 Mockup Purpose

This application serves as an interactive user interface for navigating multi-zone building energy predictions. It dynamically connects to zone-specific pre-trained models and continuously refreshes real-time consumption records.

---

## 🛠️ Dashboard Architecture & Navigation

The interface is structured into simple, intuitive control areas and analytical sections to make decision-making immediate.

### 1. ⚙️ Control Sidebar (Navigation & Settings)
Located on the left side of the app, this panel allows users to adjust filters and trigger actions:
* **🔄 Manual Data Refresh Button**: Instantly clears the local data cache and pulls the latest available sensor readings.
* **🌐 Zone Selector**: Switch between **Zone 1, Zone 2, Zone 3, and Zone 4**. Changing the zone dynamically loads the corresponding pre-trained model into memory.
* **⏳ Horizon Selector**: Choose the prediction timeframe:
  * Short-term: **+1 hour**
  * Medium-term: **+24 hours**
  * Long-term: **+7 days (+168 hours)**
* **🚨 Surconsumption Threshold Slider**: Set a percentage threshold ($5\%$ to $50\%$) to automatically flag forecasted hours that exceed historical average consumption.

---

### 2. 📊 Main View (Analytics & Predictions)

The main dashboard screen is split into four key visualization sections:

#### A. Active Model Banner
* Positioned at the top of the main screen.
* Displays the model loaded in cache for the currently selected zone along with its overall accuracy metrics (e.g., $MAE$, $RMSE$, $R^2$).

#### B. Quick KPI Cards
Four summary metrics providing an instant overview:
1. **Latest Real Consumption**: The most recent recorded consumption reading ($\text{kWh}$).
2. **Predicted Average**: The mean projected energy consumption over the selected horizon ($\text{kWh}$).
3. **Peak Projected Load**: The highest expected consumption value during the forecast period ($\text{kWh}$).
4. **Surconsumption Alerts**: Total number of hours where predictions exceed historical norms beyond the threshold set in the sidebar.

#### C. Interactive Time-Series Graph (Plotly)
A interactive chart comparing three key data streams on the same timeline:
* 🟦 **Actual Consumption**: Recent historical energy usage (last 48 hours).
* 🟧 **Model Predictions**: Forecasted consumption for the chosen horizon.
* ⬜ **Historical Baseline**: Benchmark average consumption calculated for each hour of the day.

#### D. Prediction Table & Automated Alerts
* Detailed tabular breakdown of forecasted values hour-by-hour.
* Displays: *Date & Time*, *Predicted Consumption ($\text{kWh}$)*, *Historical Benchmark ($\text{kWh}$)*, and *Percentage Difference ($\%$)*.
* **Conditional Highlighting**: Any row where the predicted consumption exceeds the historical average by more than the user's defined $X\%$ threshold is **automatically highlighted in red**.

---

## 🔄 Live Data & Caching Strategy

To ensure seamless performance and real-time synchronization:
* **Data Refresh (`@st.cache_data`)**: Real-time consumption data is cached with an automatic expiration (`ttl = 60s`). Users can force an immediate update at any time using the sidebar refresh button.
* **Model Caching (`@st.cache_resource`)**: Machine learning models are loaded into memory on demand when a user selects a zone, avoiding redundant reloads and ensuring fast UI transitions.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.9+

### Installation & Execution

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/building-energy-dashboard.git
   cd building-energy-dashboard
   ```

2. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit app**:
   ```bash
   streamlit run app.py
   ```

4. Open `http://localhost:8501` in your web browser to view the mockup.