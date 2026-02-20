# AI-Powered Smart Microgrid Controller

A cyber-physical simulation and optimization system for residential energy management using Deep Reinforcement Learning.

## Overview

This project models a residential microgrid integrating photovoltaic solar generation, battery storage, and time-of-use electricity pricing. Three control strategies are evaluated across a full year of real data to minimize weekly electricity cost and reduce grid dependency.

## System Architecture
```
Real Weather Data (Open-Meteo API)
        +
Real Demand Data (UCI Dataset)
        ↓
  Microgrid Simulator
  ├── Solar PV generation (20m², 20% efficiency)
  ├── Battery storage (10 kWh, 95% round-trip efficiency)
  ├── TOU pricing ($0.15 / $0.25 / $0.45 per kWh)
  └── Energy flow logic (solar → demand → battery → grid)
        ↓
  Control Strategies
  ├── No Battery (baseline)
  ├── Rule-Based Policy
  └── Deep Q-Network (DQN)
        ↓
  Interactive Dashboard (Streamlit + Plotly)
```

## Results

| Controller | Avg Weekly Cost | vs Rule-Based |
|---|---|---|
| No Battery | $34.75 ± $26.91 | — |
| Rule-Based | $31.76 ± $26.30 | Baseline |
| DQN (Optimized) | $28.09 ± $23.84 | **▼ 11.5%** |

Evaluated across 10 fixed weekly windows spanning all seasons of 2023.

The DQN agent learned time-of-use arbitrage without any explicit pricing rules — charging during off-peak periods ($0.15/kWh) and discharging during on-peak hours ($0.45/kWh) purely from the reward signal.

## Technical Stack

- **RL Framework:** Stable-Baselines3 (DQN)
- **Environment:** OpenAI Gymnasium (custom)
- **Forecasting:** Scikit-learn Gradient Boosting
- **Data:** Open-Meteo API + UCI Household Power Consumption
- **Dashboard:** Streamlit + Plotly
- **Language:** Python 3.12

## Hyperparameter Experiment Grid

| Parameter | Values Tested | Best |
|---|---|---|
| Degradation penalty (λ) | 0.01, 0.02, 0.03, 0.05 | 0.03 |
| Grid penalty (α) | 0.00, 0.01, 0.02 | 0.02 |
| Discount factor (γ) | 0.99, 0.995 | 0.99 |

Best configuration selected using composite score balancing cost reduction and battery wear.

## How to Run

**Install dependencies:**
```bash
pip install streamlit plotly pandas numpy scikit-learn stable-baselines3 gymnasium joblib
```

**Launch dashboard:**
```bash
streamlit run app.py
```

The dashboard loads real data automatically on startup and allows interactive simulation across any week of the year.

## Project Structure
```
smart-microgrid-controller/
├── app.py                        # Streamlit dashboard
├── smart_microgrid_notebook.ipynb # Full training pipeline
└── README.md
```

## Key Design Decisions

- **Episode length:** 168 hours (1 week) — captures full weekly demand cycles
- **State space:** 8 features including battery SoC, solar generation, demand forecast, hour encoding, and current price
- **Action space:** 5 discrete actions (idle, charge 1kW, charge 2kW, discharge 1kW, discharge 2kW)
- **Reward:** Negative electricity cost normalized by maximum possible hourly cost
- **Training:** 300,000 timesteps, 1,784 episodes

## Author

**Kassahun Aweke**  
Electrical Engineering Undergraduate  
[GitHub](https://github.com/kassahunenyew) · [LinkedIn](https://www.linkedin.com/in/kassahunenyew)
