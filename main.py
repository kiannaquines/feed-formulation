from fastapi import FastAPI, Request
import time
import socket
import psutil
import numpy as np

app = FastAPI(
        title="Feed Formulation API",
        description="API for feed formulation and management",
        version="1.0.0"
    )

start_time = time.time()
hostname = socket.gethostname()

@app.get("/")
def index_page(request: Request):
    return {
        "message": "Welcome to the Feed Formulation API!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": hostname
    }

@app.get("/health")
def health_check():
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)

    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory_usage = psutil.virtual_memory().percent

    if cpu_usage < 85 and memory_usage < 90:
        status = "healthy"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "details": {
            "uptime_seconds": uptime_seconds,
            "hostname": hostname,
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": memory_usage,
        }
    }

@app.get("/feed/formulate")
def feed_formulator():
    
    from scipy.optimize import linprog

    ingredients = [
        'Corn', 'Soybean Meal', 'Skimmilk', 'Rice bran D1', 'Fish Meal',
        'Coconut Oil', 'Limestone', 'Monodical Phosphate', 'Vitamin Premix',
        'Choline', 'Salt', 'L-lysine', 'DL-Methionine', 'Antioxidant', 'Azolla'
    ]

    c = np.array([75, 100, 250, 80, 150, 50, 6.3, 80, 185, 640,
                  28, 1279, 120, 200, 350])

    A_nutrients = np.array([
        [7.8, 43.1, 33.5, 12.4, 58.7, 0, 0, 0, 0, 0, 0, 74, 58, 0, 21.3],
        [3.3, 2.24, 2.51, 2.4, 2.8, 8.6, 0, 0, 0, 0, 0, 3.625, 3.6, 0, 1.0513],
        [0.07, 0.45, 1.25, 0.07, 4.68, 0, 38, 16, 0, 0, 0, 0, 0, 0, 0.45],
        [0.06, 0.19, 0.95, 0.23, 2.86, 0, 0, 18, 0, 0, 0, 0, 0, 0, 0.35]
    ])

    nutrient_req = np.array([22.3, 2.9, 0.87, 0.48])

    ingredient_min = np.array([
        0.45, 0.25, 0.02, 0.05, 0.01, 0, 0, 0, 0.0025,
        0.0025, 0.0025, 0.0025, 0, 0.0025, 0.010
    ])

    ingredient_max = np.array([
        0.70, 0.30, 1, 0.5, 0.5, 1, 1, 1, 0.0025,
        0.0025, 0.0025, 0.0025, 1, 0.0025, 0.010
    ])

    sum_constraint = np.ones((1, len(ingredients)))
    A_eq = np.vstack((sum_constraint, A_nutrients))
    b_eq = np.hstack(([1.0], nutrient_req))
    bounds = list(zip(ingredient_min, ingredient_max))

    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if result.success:
        ingredient_percentages = result.x * 100
        nutrient_values = A_nutrients @ result.x
        costs = c * result.x

        return {
            "status": "success",
            "message": "Optimal feed formulation found.",
            "total_cost_per_kg": round(result.fun, 2),
            "ingredient_composition_percent": {
                ingredients[i]: round(ingredient_percentages[i], 4)
                for i in range(len(ingredients))
                if ingredient_percentages[i] > 0
            },
            "nutrient_achievement": {
                "Protein (% CP)": round(nutrient_values[0], 4),
                "Energy (ME)": round(nutrient_values[1], 4),
                "Calcium (% Ca)": round(nutrient_values[2], 4),
                "Phosphorus (% P)": round(nutrient_values[3], 4),
            },
            "nutrient_requirements": {
                "Protein (% CP)": round(nutrient_req[0], 4),
                "Energy (ME)": round(nutrient_req[1], 4),
                "Calcium (% Ca)": round(nutrient_req[2], 4),
                "Phosphorus (% P)": round(nutrient_req[3], 4),
            },
            "cost_breakdown_per_ingredient": {
                ingredients[i]: round(costs[i], 4)
                for i in range(len(ingredients))
                if costs[i] > 0
            },
            "total_ingredient_percentage": round(sum(result.x) * 100, 6)
        }
    else:
        return {
            "status": "failure",
            "message": "No optimal solution found.",
            "solver_status_code": result.status,
            "solver_message": result.message
        }