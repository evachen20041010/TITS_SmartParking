import os, glob
import pandas as pd
import xml.etree.ElementTree as ET

FACTOR_KG_PER_S = 0.0031  # 3.1 g/s => 0.0031 kg/s

def _get_tripinfos_root(path: str):
    # tripinfo 檔前面可能混入 config，保險起見只抓 <tripinfos> 後半段
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    i = text.find("<tripinfos")
    if i == -1:
        return None
    return ET.fromstring(text[i:])

def extract():
    results = []
    for t_file in glob.glob("outputs/tripinfo_*.xml"):
        base = os.path.basename(t_file).replace(".xml", "")
        _, strategy, occupancy, seed = base.split("_")

        root = _get_tripinfos_root(t_file)
        if root is None:
            continue

        cruise_list = []
        for trip in root.findall("tripinfo"):
            # 排除被 traci.remove 的車（不然會灌水 N 且扭曲平均）
            if trip.get("vaporized") == "traci":
                continue
            if float(trip.get("routeLength", "0")) <= 0:
                continue

            duration = float(trip.get("duration", "0"))
            stop_time = float(trip.get("stopTime", "0"))
            cruising = max(0.0, duration - stop_time)  # 不含停妥後的停車時間
            cruise_list.append(cruising)

        n = len(cruise_list)
        avg_cruise = sum(cruise_list) / n if n else 0.0
        total_co2 = sum(cruise_list) * FACTOR_KG_PER_S

        results.append({
            "Strategy": strategy,
            "Occupancy": occupancy,
            "Seed": int(seed),
            "N_Trips": n,
            "Avg_Cruising_Time (s)": round(avg_cruise, 2),
            "Total_CO2 (kg)": round(total_co2, 2),
        })

    df = pd.DataFrame(results)
    summary = df.groupby(["Strategy", "Occupancy"]).mean(numeric_only=True).reset_index()
    print(summary.to_string(index=False))

if __name__ == "__main__":
    extract()