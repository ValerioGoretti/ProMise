import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.patches as mpatches

# Nomi delle cartelle per ciascun log
log_folders = {
    "BPIC12": "./bpic12Ram",
    "BPIC13": "./bpic13Ram",
    "Sepsis": "./sepsisRam",
}

# File CSV da leggere
csv_files = [
    "scalability_10.csv",
    "scalability_20.csv",
    "scalability_30.csv",
    "scalability_40.csv",
    "scalability_50.csv",
    "scalability_60.csv",
    "scalability_70.csv",
    "scalability_80.csv",
    "scalability_90.csv",
    "scalability_100.csv",
]

# Colori per ciascun log
log_colors = {
    "BPIC12": "blue",
    "BPIC13": "green",
    "Sepsis": "red",
}

# Dizionario per memorizzare i dati di latenza per ogni log
log_latency_data = {}

for log_name, folder in log_folders.items():
    latency_per_users = defaultdict(list)

    for filename in csv_files:
        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    num_users = int(row["num_users"])
                    start = float(row["start_time"])
                    end = float(row["end_time"])
                    status = row["status"]
                    if status == "SUCCESS" and end > start:
                        latency_ms = (end - start) * 1000  # in ms
                        latency_per_users[num_users].append(latency_ms)
                except Exception as e:
                    print(f"Errore nella riga {row}: {e}")

    avg_latency = {
        k: sum(v) / len(v) if v else 0
        for k, v in latency_per_users.items()
    }

    q1 = {}
    q3 = {}
    for k, values in latency_per_users.items():
        if values:
            q1[k] = np.percentile(values, 25)
            q3[k] = np.percentile(values, 75)
        else:
            q1[k] = 0.0
            q3[k] = 0.0

    avg_latency[0] = 0.0
    q1[0] = 0.0
    q3[0] = 0.0

    sorted_x = sorted(avg_latency.keys())
    sorted_avg = [avg_latency[x] for x in sorted_x]
    sorted_q1 = [q1[x] for x in sorted_x]
    sorted_q3 = [q3[x] for x in sorted_x]

    log_latency_data[log_name] = (sorted_x, sorted_avg, sorted_q1, sorted_q3)

# --- Preparo la tabella solo con Log e B̂₁ % decimale ---
#lines = ["Log           β"]
lines = []

for log_name, data in log_latency_data.items():
    x_vals, y_vals, _, _ = data

    x_np = np.array(x_vals[1:]).reshape(-1, 1)
    y_np = np.array(y_vals[1:])

    # Regressione lineare su valori normalizzati (percentuali decimali)
    y_pct = y_np / y_np[0]
    model_pct = LinearRegression().fit(x_np, y_pct)
    slope_pct = model_pct.coef_[0]
    lines.append(f"{log_name:<10} βhat={slope_pct:.4f}")

box_text = "\n".join(lines)

# === PLOT ===
plt.figure(figsize=(10, 6))

for log_name, (x_vals, avg_vals, q1_vals, q3_vals) in log_latency_data.items():
    color = log_colors.get(log_name, None)

    # Curva media
    plt.plot(x_vals, avg_vals, marker='o', linewidth=2, markersize=6,
             label=log_name, color=color)

    # Banda Q1–Q3
    plt.fill_between(x_vals, q1_vals, q3_vals, color=color, alpha=0.2)

# Box testuale con tabella (solo log e slope decimale)
# --- Nel plot ---
props = dict(boxstyle='round', facecolor='white', alpha=0.95, edgecolor='gray')
plt.text(0.015, 0.6, box_text,
         transform=plt.gca().transAxes,
         fontsize=12, verticalalignment='bottom',
         horizontalalignment='left', bbox=props)

# Legenda linee + banda unica
lines_legend = [plt.Line2D([], [], color=log_colors[log], marker='o', linestyle='-')
                for log in log_latency_data]
labels_legend = list(log_latency_data.keys())

quartile_patch = mpatches.Patch(color='gray', alpha=0.2, label='Interquartile Range (Q1–Q3)')
lines_legend.append(quartile_patch)
labels_legend.append('Interquartile Range (Q1–Q3)')

plt.legend(lines_legend, labels_legend, loc='upper left', fontsize=9)
plt.xlabel("Number of concurrent users")
plt.ylabel("Average response time (ms)")
plt.grid(True, alpha=0.3)

all_x = set()
for data in log_latency_data.values():
    all_x.update(data[0])
plt.xticks(sorted(all_x))

plt.tight_layout()
plt.savefig("latency_with_slope_table.pdf", dpi=300)
plt.show()
