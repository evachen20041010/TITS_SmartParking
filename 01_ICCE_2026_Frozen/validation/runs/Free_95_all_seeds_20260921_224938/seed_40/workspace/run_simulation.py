import os
import sys
import traci
import random
import math
import pandas as pd

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("請宣告環境變數 'SUMO_HOME'")

# ==========================================
# 1. 實驗參數與情境設定
# ==========================================
SCENARIOS = [
    {"name": "Free_85", "occupancy": 85, "strategy": "free"},
    {"name": "Free_95", "occupancy": 95, "strategy": "free"},
    {"name": "Assigned_85", "occupancy": 85, "strategy": "assigned"},
    {"name": "Assigned_95", "occupancy": 95, "strategy": "assigned"}
]
SEEDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

PARKING_ZONES = {
    "Zone_1": {"G": "PA_Z1_G", "cap_G": 40, "F": "PA_Z1_F", "cap_F": 10, "D": "PA_Z1_D", "cap_D": 5, "walk_dist": 50},
    "Zone_2": {"G": "PA_Z2_G", "cap_G": 50, "F": "PA_Z2_F", "cap_F": 10, "D": "PA_Z2_D", "cap_D": 5, "walk_dist": 150},
    "Zone_3": {"G": "PA_Z3_G", "cap_G": 80, "walk_dist": 250} 
}
TOTAL_CAPACITY = 200 # 停車場總容量

# ==========================================
# 2. 核心決策邏輯函數
# ==========================================
def get_zone_score(zone_id, veh_type, w_drive, w_walk, w_occ):
    zone_info = PARKING_ZONES[zone_id]
    available_spots = 0
    if veh_type == "family" and "F" in zone_info:
        available_spots += zone_info["cap_F"] - traci.parkingarea.getVehicleCount(zone_info["F"])
    elif veh_type == "disabled" and "D" in zone_info:
        available_spots += zone_info["cap_D"] - traci.parkingarea.getVehicleCount(zone_info["D"])
    if "G" in zone_info:
        available_spots += zone_info["cap_G"] - traci.parkingarea.getVehicleCount(zone_info["G"])
        
    occ_proxy = 1.0 / (max(available_spots, 0) + 1) 
    eta_drive = zone_info["walk_dist"] * 0.5 
    noise = random.gauss(0, 0.5)
    
    score = (w_drive * eta_drive) + (w_walk * zone_info["walk_dist"]) + (w_occ * occ_proxy) + noise
    return score, available_spots

def execute_assigned_strategy(veh_id, veh_type):
    """提出方法：系統指派車位 (加入動態負載平衡，避免車流堵死)"""
    special_candidates = []
    g_candidates = []
    g_weights = []
    
    for z_id, z_info in PARKING_ZONES.items():
        # 1. 優先尋找特殊車位
        if veh_type == "family" and "F" in z_info:
            if traci.parkingarea.getVehicleCount(z_info["F"]) < z_info["cap_F"]:
                special_candidates.append(z_info["F"])
        elif veh_type == "disabled" and "D" in z_info:
            if traci.parkingarea.getVehicleCount(z_info["D"]) < z_info["cap_D"]:
                special_candidates.append(z_info["D"])
                
        # 2. 收集一般車位 (G) 的空位狀態
        if "G" in z_info:
            cap = z_info["cap_G"]
            count = traci.parkingarea.getVehicleCount(z_info["G"])
            if count < cap:
                avail_ratio = (cap - count) / cap # 計算空位比例
                g_candidates.append(z_info["G"])
                g_weights.append(avail_ratio) # 越空的區域權重越高
                
    # 決策執行
    if special_candidates:
        # 有特殊車位就直接給
        traci.vehicle.setParkingAreaStop(veh_id, special_candidates[0], duration=600)
    elif g_candidates:
        # 一般車位：使用輪盤抽籤 (依據空位比例分配)，將車流完美打散到 Z1, Z2, Z3
        target_pa = random.choices(g_candidates, weights=g_weights, k=1)[0]
        traci.vehicle.setParkingAreaStop(veh_id, target_pa, duration=600)

def execute_free_search_strategy(veh_id, veh_info):
    candidates = []
    for z_id in PARKING_ZONES.keys():
        # 移除 veh_info['w_fam'] 與 veh_info['familiar_zones']
        score, avail = get_zone_score(z_id, veh_info['type'], veh_info['w_drive'], veh_info['w_walk'], veh_info['w_occ'])
        candidates.append((z_id, score, avail))
        
    candidates.sort(key=lambda x: x[1])
    top_candidates = candidates[:2] 
    
    chosen_zone = top_candidates[0][0] 
    for cand_z, cand_score, cand_avail in top_candidates:
        if cand_avail > 0 and random.random() < veh_info['p_accept']:
            chosen_zone = cand_z
            break
            
    z_info = PARKING_ZONES[chosen_zone]
    target_pa = None
    
    # 【關鍵修復】：確保真的有空位才指派，避免車輛停在單線道上當路障造成死鎖
    if veh_info['type'] == "family" and "F" in z_info and traci.parkingarea.getVehicleCount(z_info["F"]) < z_info["cap_F"]:
        target_pa = z_info["F"]
    elif veh_info['type'] == "disabled" and "D" in z_info and traci.parkingarea.getVehicleCount(z_info["D"]) < z_info["cap_D"]:
        target_pa = z_info["D"]
    elif "G" in z_info and traci.parkingarea.getVehicleCount(z_info["G"]) < z_info["cap_G"]:
        target_pa = z_info["G"]
        
    if target_pa:
        traci.vehicle.setParkingAreaStop(veh_id, target_pa, duration=600)

# ==========================================
# 3. 主模擬迴圈
# ==========================================
def run():
    all_results = []
    if not os.path.exists("outputs"): os.makedirs("outputs")

    for scenario in SCENARIOS:
        target_veh_count = int(TOTAL_CAPACITY * (scenario["occupancy"] / 100.0))
        
        for seed in SEEDS:
            # 【關鍵修復】：將 Python 端的亂數種子與 SUMO 同步，確保每次執行軌跡一致！
            random.seed(seed)
            
            print(f"🚀 開始執行: {scenario['name']} | Seed: {seed} | 目標車數: {target_veh_count}")
            
            sumo_cmd = [
                "sumo", "-c", "your_config.sumocfg", 
                "--seed", str(seed),
                "--emission-output", f"outputs/emissions_{scenario['name']}_{seed}.xml",
                "--tripinfo-output", f"outputs/tripinfo_{scenario['name']}_{seed}.xml",
                "--no-step-log", "true"
            ]
            
            traci.start(sumo_cmd)
            veh_states = {}
            kpi_tracker = {"total_departed": 0, "family_total": 0, "disabled_total": 0}

            step = 0
            # 加入 step < 2500 作為安全跳脫機制，避免任何意外的死鎖
            while traci.simulation.getMinExpectedNumber() > 0 and step < 2500:
                traci.simulationStep()
                
                if step % 500 == 0 and step > 0:
                    print(f"   ... 模擬進行中 (Step {step})")

                departed = traci.simulation.getDepartedIDList()
                for veh_id in departed:
                    # 控制總發車量，達到占用率目標後，立刻移除多餘車輛
                    if kpi_tracker["total_departed"] >= target_veh_count:
                        traci.vehicle.remove(veh_id)
                        continue
                        
                    kpi_tracker["total_departed"] += 1
                    rand_type = random.random()
                    v_type = "normal"
                    if rand_type < 0.03: v_type = "disabled"
                    elif rand_type < 0.13: v_type = "family"
                    
                    if v_type == "family": kpi_tracker["family_total"] += 1
                    if v_type == "disabled": kpi_tracker["disabled_total"] += 1
                        
                    veh_states[veh_id] = {
                        "type": v_type,
                        "w_walk": random.uniform(0.5, 2.0),
                        "w_drive": random.uniform(0.5, 2.0),
                        "w_occ": random.uniform(1.0, 3.0),
                        # 移除 w_fam 與 familiar_zones，與論文一致
                        "p_accept": random.uniform(0.6, 1.0)
                    }
                    
                    if scenario["strategy"] == "assigned":
                        execute_assigned_strategy(veh_id, v_type)
                    else:
                        execute_free_search_strategy(veh_id, veh_states[veh_id])

                step += 1

            # 檢查是否是因為塞車超時而被截斷
            # 在迴圈結束後檢查是否超時
            is_truncated = True if step >= 2500 else False
            if is_truncated:
                print(f"   ⚠️ 警告: {scenario['name']} (Seed: {seed}) 達到 2500 步上限被強制截斷！")

            traci.close()
            all_results.append({
                "Strategy": scenario["strategy"],
                "Occupancy": scenario["occupancy"],
                "Seed": seed,
                "Is_Truncated": is_truncated
            })

    df = pd.DataFrame(all_results)
    df.to_csv("sumo_results_summary.csv", index=False)
    print("✅ 所有模擬執行完畢！")

if __name__ == "__main__":
    run()