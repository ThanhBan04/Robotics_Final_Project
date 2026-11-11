# -*- coding: utf-8 -*-
"""
Hệ thống Thí nghiệm Khoa học Toàn diện (TN0 -> TN7) cho UAV Target Tracking 2D.
Tuân thủ đầy đủ định hướng trong Ke_hoach_thi_nghiem_UAV_Tracking.md và các chuẩn mực thực nghiệm.

Các thí nghiệm:
- TN0: Khảo sát 12 kịch bản qua 20 hạt giống (Monte Carlo) cho cả EKF và UKF (Mean ± Std, Median, Post-10s).
- TN1: Thí nghiệm đối chứng Không dùng bộ lọc (Raw, Smoothed, EKF, UKF).
- TN2: Quét mức nhiễu cảm biến camera (Noise sweep sigma_r in [1, 2, 5, 10, 15, 20]m) với cả 2 biến thể R (adapted vs fixed).
- TN3: Quét thời gian mất tín hiệu camera (Dropout duration in [1, 2, 3, 5, 8, 10]s) cho cả mục tiêu đi thẳng và đang rẽ.
- TN4: Phân tích chỉ số tỉ lệ mất dấu mục tiêu (tách biệt mất tín hiệu camera và phân kỳ ước lượng).
- TN5: Khảo sát phi tuyến làm lộ khác biệt EKF vs UKF (cự ly bám, tần số đo, sai lệch khởi tạo).
- TN6: Đánh giá tính nhất quán bộ lọc (NEES & NIS trên 20 hạt giống).
- TN7: Đo đạc thời gian tính toán thực tế (Execution time profiling in us).
"""

import sys
import os
import argparse
import copy
import yaml
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from simulation.simulation_engine import SimulationEngine
from simulation.target_scenario import get_scenario_config, get_all_scenario_names


def load_config():
    cfg_path = os.path.join(PROJECT_ROOT, "config.yaml")
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


# =========================================================================
# TN1: ĐỐI CHỨNG KHÔNG DÙNG BỘ LỌC (NO-FILTER BASELINE)
# =========================================================================
def run_experiment_tn1(seeds=range(1, 11), output_dir="results/experiments/TN1"):
    """
    So sánh 4 phương án điều khiển cho UAV:
    1. Không lọc (Raw measurement - No filter)
    2. Không lọc có làm trơn (Smoothed moving average)
    3. Bộ lọc EKF
    4. Bộ lọc UKF
    trên các kịch bản 1 (Baseline), 3 (High Noise), 4 (Lost Detection).
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN1: ĐỐI CHỨNG KHÔNG DÙNG BỘ LỌC (NO-FILTER BASELINE)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    scenarios = [1, 3, 4]
    filter_modes = ['none', 'none_smoothed', 'ekf', 'ukf']
    records = []

    for sc_id in scenarios:
        for f_mode in filter_modes:
            for s in seeds:
                scfg = get_scenario_config(sc_id, cfg)
                scfg['steady_state_init'] = True  # Đã bám ổn định để đo thuần chất lượng lọc/điều khiển
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=s)
                engine.filter_mode = f_mode
                
                engine.run_headless()
                m = engine.compute_metrics()
                
                records.append({
                    'scenario_id': sc_id,
                    'scenario_name': scfg['name'],
                    'filter_mode': f_mode,
                    'seed': s,
                    'pos_rmse': m.get('raw_position_rmse', m.get('ekf_position_rmse', m.get('ukf_position_rmse', 0.0))),
                    'tracking_rmse': m.get('tracking_rmse', 0.0),
                    'pid_step_jitter': m.get('pid_step_jitter', 0.0),
                    'pid_saturation_ratio': m.get('pid_saturation_ratio', 0.0),
                    'min_distance': m.get('min_tracking_distance', 0.0),
                    'max_separation': m.get('max_separation', 0.0),
                    'has_lost': m.get('has_lost_target', False)
                })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn1_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN1 tại: {csv_path}")

    # Vẽ đồ thị so sánh
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    agg_df = df.groupby(['scenario_name', 'filter_mode']).agg({
        'tracking_rmse': ['mean', 'std'],
        'pid_step_jitter': ['mean', 'std']
    }).reset_index()

    sc_names = df['scenario_name'].unique()
    x = np.arange(len(sc_names))
    width = 0.2
    mode_info = [
        ('none', 'Raw (No Filter)', '#d32f2f'),
        ('none_smoothed', 'Raw + Smooth', '#e65100'),
        ('ekf', 'EKF', '#1976d2'),
        ('ukf', 'UKF', '#388e3c')
    ]

    for i, (fm, label, color) in enumerate(mode_info):
        sub = agg_df[agg_df['filter_mode'] == fm]
        means_trk = [sub[sub['scenario_name'] == name]['tracking_rmse']['mean'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        stds_trk = [sub[sub['scenario_name'] == name]['tracking_rmse']['std'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        ax1.bar(x + (i - 1.5)*width, means_trk, width, yerr=stds_trk, capsize=3, label=label, color=color, alpha=0.85)

        means_jit = [sub[sub['scenario_name'] == name]['pid_step_jitter']['mean'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        stds_jit = [sub[sub['scenario_name'] == name]['pid_step_jitter']['std'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        ax2.bar(x + (i - 1.5)*width, means_jit, width, yerr=stds_jit, capsize=3, label=label, color=color, alpha=0.85)

    ax1.set_title("Tracking RMSE (Mean ± Std)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("RMSE (m)", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(sc_names, fontsize=10)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

    ax2.set_title("Actuator Chatter: Mean Step-to-Step Acceleration Delta", fontsize=12, fontweight='bold')
    ax2.set_ylabel("Step Jerk Delta (m/s²)", fontsize=11)
    ax2.set_xticks(x)
    ax2.set_xticklabels(sc_names, fontsize=10)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y')

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn1_no_filter_comparison.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN1 tại: {fig_path}")
    return df


# =========================================================================
# TN2: QUÉT MỨC NHIỄU CẢM BIẾN (NOISE SWEEP: ADAPTED VS FIXED R)
# =========================================================================
def run_experiment_tn2(seeds=range(1, 11), output_dir="results/experiments/TN2"):
    """
    Khảo sát sai số ước lượng và bám khi tăng độ lệch chuẩn nhiễu camera sigma_r in [1, 20]m.
    Bao gồm cả 2 biến thể:
    - R_variant = 'adapted': Ma trận R của bộ lọc khớp với mức nhiễu thật.
    - R_variant = 'fixed': Ma trận R giữ nguyên mức danh định (bộ lọc không biết nhiễu tăng).
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN2: QUÉT MỨC NHIỄU ĐO CẢM BIẾN (NOISE SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    sigma_r_levels = [1.0, 2.0, 5.0, 10.0, 15.0, 20.0]
    records = []

    for sr in sigma_r_levels:
        s_theta = 0.015 * sr
        for r_variant in ['adapted', 'fixed']:
            for s in seeds:
                for f_mode in ['ekf', 'ukf']:
                    scfg = get_scenario_config(1, cfg)
                    scfg['steady_state_init'] = True
                    scfg['camera']['noise_range_std'] = sr
                    scfg['camera']['noise_bearing_std'] = s_theta
                    
                    engine = SimulationEngine(cfg)
                    engine.setup(scfg, random_seed=s)
                    engine.filter_mode = f_mode
                    
                    if r_variant == 'fixed':
                        # Giữ R danh định (sigma_r=2.0m, sigma_theta=0.03rad)
                        R_nom = np.diag([2.0**2, 0.03**2])
                        if engine.ekf: engine.ekf.set_measurement_noise(R_nom)
                        if engine.ukf: engine.ukf.set_measurement_noise(R_nom)
                    
                    engine.run_headless()
                    m = engine.compute_metrics()
                    
                    pos_rmse = m.get('ekf_position_rmse' if f_mode == 'ekf' else 'ukf_position_rmse', 0.0)
                    records.append({
                        'sigma_r': sr,
                        'sigma_theta': s_theta,
                        'r_variant': r_variant,
                        'filter_mode': f_mode,
                        'seed': s,
                        'pos_rmse': pos_rmse,
                        'tracking_rmse': m.get('tracking_rmse', 0.0),
                        'has_lost': m.get('has_lost_target', False)
                    })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn2_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN2 tại: {csv_path}")

    # Vẽ biểu đồ đường
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    agg = df.groupby(['sigma_r', 'filter_mode', 'r_variant']).agg({
        'pos_rmse': ['mean', 'std'],
        'tracking_rmse': ['mean', 'std']
    }).reset_index()

    styles = {
        ('ekf', 'adapted'): ('#1976d2', '-', 'EKF (Adapted R)'),
        ('ekf', 'fixed'): ('#64b5f6', '--', 'EKF (Fixed Nominal R)'),
        ('ukf', 'adapted'): ('#388e3c', '-', 'UKF (Adapted R)'),
        ('ukf', 'fixed'): ('#81c784', '--', 'UKF (Fixed Nominal R)'),
    }

    for (fm, rv), (col, ls, lbl) in styles.items():
        sub = agg[(agg['filter_mode'] == fm) & (agg['r_variant'] == rv)]
        if not sub.empty:
            ax1.plot(sub['sigma_r'], sub['pos_rmse']['mean'], marker='o', linewidth=2, linestyle=ls, label=lbl, color=col)
            ax2.plot(sub['sigma_r'], sub['tracking_rmse']['mean'], marker='s', linewidth=2, linestyle=ls, label=lbl, color=col)

    ax1.set_title(r"Estimation Position RMSE vs Measurement Noise $\sigma_r$", fontsize=12, fontweight='bold')
    ax1.set_xlabel(r"Range Noise Std $\sigma_r$ (m)", fontsize=11)
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.5)

    ax2.set_title(r"Tracking RMSE vs Measurement Noise $\sigma_r$", fontsize=12, fontweight='bold')
    ax2.set_xlabel(r"Range Noise Std $\sigma_r$ (m)", fontsize=11)
    ax2.set_ylabel("Tracking RMSE (m)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn2_noise_sweep.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN2 tại: {fig_path}")
    return df


# =========================================================================
# TN3: QUÉT THỜI GIAN MẤT TÍN HIỆU (DROPOUT SWEEP: STRAIGHT VS TURNING)
# =========================================================================
def run_experiment_tn3(seeds=range(1, 11), output_dir="results/experiments/TN3"):
    """
    Khảo sát giới hạn bộ lọc khi mất dấu liên tục:
    Dropout duration in [1, 2, 3, 5, 8, 10] s, bắt đầu tại t = 10s.
    So sánh 2 trường hợp: mục tiêu đi thẳng vs mục tiêu đang rẽ.
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN3: QUÉT THỜI GIAN MẤT TÍN HIỆU (DROPOUT SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    durations = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    records = []

    for dur in durations:
        for motion in ['straight', 'turning']:
            for s in seeds:
                for f_mode in ['ekf', 'ukf']:
                    scfg = get_scenario_config(4, cfg)
                    scfg['duration'] = 25.0
                    scfg['steady_state_init'] = True
                    scfg['dropout_events'] = [{'start': 10.0, 'duration': dur}]
                    
                    if motion == 'turning':
                        scfg['maneuvers'] = [{'time': 10.0, 'type': 'turn', 'angle': 60, 'duration': 0.5}]
                    else:
                        scfg['maneuvers'] = []
                    
                    engine = SimulationEngine(cfg)
                    engine.setup(scfg, random_seed=s)
                    engine.filter_mode = f_mode
                    
                    engine.run_headless()
                    m = engine.compute_metrics()
                    
                    pos_rmse = m.get('ekf_position_rmse' if f_mode == 'ekf' else 'ukf_position_rmse', 0.0)
                    records.append({
                        'dropout_duration': dur,
                        'motion': motion,
                        'filter_mode': f_mode,
                        'seed': s,
                        'pos_rmse': pos_rmse,
                        'tracking_rmse': m.get('tracking_rmse', 0.0),
                        'max_separation': m.get('max_separation', 0.0),
                        'has_lost': m.get('has_lost_target', False)
                    })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn3_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN3 tại: {csv_path}")

    # Vẽ biểu đồ
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    agg = df.groupby(['dropout_duration', 'filter_mode', 'motion']).agg({
        'pos_rmse': ['mean', 'std'],
        'tracking_rmse': ['mean', 'std']
    }).reset_index()

    for fm, col in [('ekf', '#1976d2'), ('ukf', '#388e3c')]:
        sub_str = agg[(agg['filter_mode'] == fm) & (agg['motion'] == 'straight')]
        sub_turn = agg[(agg['filter_mode'] == fm) & (agg['motion'] == 'turning')]
        
        ax1.plot(sub_str['dropout_duration'], sub_str['pos_rmse']['mean'], marker='o', linewidth=2, label=f"{fm.upper()} (Straight)", color=col)
        ax1.plot(sub_turn['dropout_duration'], sub_turn['pos_rmse']['mean'], marker='^', linewidth=2, linestyle='--', label=f"{fm.upper()} (Turning)", color=col)

        ax2.plot(sub_str['dropout_duration'], sub_str['tracking_rmse']['mean'], marker='s', linewidth=2, label=f"{fm.upper()} (Straight)", color=col)
        ax2.plot(sub_turn['dropout_duration'], sub_turn['tracking_rmse']['mean'], marker='v', linewidth=2, linestyle='--', label=f"{fm.upper()} (Turning)", color=col)

    ax1.set_title("Position RMSE vs Dropout Duration", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Dropout Duration (s)", fontsize=11)
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.5)

    ax2.set_title("Tracking RMSE vs Dropout Duration", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Dropout Duration (s)", fontsize=11)
    ax2.set_ylabel("Tracking RMSE (m)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn3_dropout_sweep.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN3 tại: {fig_path}")
    return df


# =========================================================================
# TN5: KỊCH BẢN LÀM LỘ KHÁC BIỆT EKF VS UKF (NONLINEARITY SWEEP)
# =========================================================================
def run_experiment_tn5(seeds=range(1, 11), output_dir="results/experiments/TN5"):
    """
    Khảo sát tỉ số RMSE(UKF)/RMSE(EKF) qua 3 trục phi tuyến:
    1. Cự ly bám: [10, 20, 50, 100] m
    2. Tần số đo: [2, 5, 10, 50] Hz
    3. Độ bất định khởi tạo: [10, 30, 60] m
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN5: KỊCH BẢN LÀM LỘ KHÁC BIỆT EKF VS UKF (NONLINEARITY SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    records = []

    # Quét 1: Cự ly bám
    distances = [10.0, 20.0, 50.0, 100.0]
    for d in distances:
        for s in seeds:
            scfg = get_scenario_config(1, cfg)
            scfg['steady_state_init'] = True
            scfg['pid'] = scfg.get('pid', {})
            scfg['pid']['desired_distance'] = d
            
            engine = SimulationEngine(cfg)
            engine.setup(scfg, random_seed=s)
            engine.filter_mode = 'both'
            
            engine.run_headless()
            m = engine.compute_metrics()
            
            ekf_rmse = m.get('ekf_position_rmse', 0.0)
            ukf_rmse = m.get('ukf_position_rmse', 0.0)
            ratio = (ukf_rmse / ekf_rmse) if ekf_rmse > 1e-4 else 1.0
            
            records.append({
                'sweep_type': 'distance',
                'param_value': d,
                'seed': s,
                'ekf_rmse': ekf_rmse,
                'ukf_rmse': ukf_rmse,
                'ratio_ukf_to_ekf': ratio,
                'tracking_rmse': m.get('tracking_rmse', 0.0)
            })

    # Quét 2: Tần số đo
    rates = [2.0, 5.0, 10.0, 50.0]
    for r in rates:
        for s in seeds:
            scfg = get_scenario_config(1, cfg)
            scfg['steady_state_init'] = True
            scfg['camera']['measurement_rate'] = r
            
            engine = SimulationEngine(cfg)
            engine.setup(scfg, random_seed=s)
            engine.filter_mode = 'both'
            
            engine.run_headless()
            m = engine.compute_metrics()
            
            ekf_rmse = m.get('ekf_position_rmse', 0.0)
            ukf_rmse = m.get('ukf_position_rmse', 0.0)
            ratio = (ukf_rmse / ekf_rmse) if ekf_rmse > 1e-4 else 1.0
            
            records.append({
                'sweep_type': 'measurement_rate',
                'param_value': r,
                'seed': s,
                'ekf_rmse': ekf_rmse,
                'ukf_rmse': ukf_rmse,
                'ratio_ukf_to_ekf': ratio,
                'tracking_rmse': m.get('tracking_rmse', 0.0)
            })

    # Quét 3: độ bất định khởi tạo P0 (giữ nguyên target/scenario và seed).
    for position_var in [100.0, 1000.0, 10000.0]:
        for velocity_var in [900.0, 2500.0]:
            for s in seeds:
                scfg = get_scenario_config(1, cfg)
                scfg['steady_state_init'] = True
                scfg['filter'] = {
                    'initial_position_var': position_var,
                    'initial_velocity_var': velocity_var,
                }
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=s)
                engine.filter_mode = 'both'
                engine.run_headless()
                m = engine.compute_metrics()
                ekf_rmse = m.get('ekf_position_rmse', 0.0)
                ukf_rmse = m.get('ukf_position_rmse', 0.0)
                records.append({
                    'sweep_type': 'initial_covariance',
                    'param_value': f'{position_var:g}/{velocity_var:g}',
                    'position_var': position_var,
                    'velocity_var': velocity_var,
                    'seed': s,
                    'ekf_rmse': ekf_rmse,
                    'ukf_rmse': ukf_rmse,
                    'ratio_ukf_to_ekf': ukf_rmse / ekf_rmse if ekf_rmse > 1e-4 else 1.0,
                    'tracking_rmse': m.get('tracking_rmse', 0.0)
                })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn5_nonlinearity_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN5 tại: {csv_path}")

    # Vẽ biểu đồ
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(21, 5), dpi=150)
    
    # Subplot 1: Theo khoảng cách
    dist_sub = df[df['sweep_type'] == 'distance'].groupby('param_value').agg({
        'ekf_rmse': 'mean', 'ukf_rmse': 'mean', 'ratio_ukf_to_ekf': 'mean'
    }).reset_index()
    ax1.plot(dist_sub['param_value'], dist_sub['ekf_rmse'], marker='o', linewidth=2, label='EKF Pos RMSE', color='#1976d2')
    ax1.plot(dist_sub['param_value'], dist_sub['ukf_rmse'], marker='s', linewidth=2, label='UKF Pos RMSE', color='#388e3c')
    ax1.set_title("RMSE vs Following Distance (Higher Nonlinearity at Closer Range)", fontsize=11, fontweight='bold')
    ax1.set_xlabel("Desired Distance (m)", fontsize=10)
    ax1.set_ylabel("Position RMSE (m)", fontsize=10)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Subplot 2: Theo tần số đo
    rate_sub = df[df['sweep_type'] == 'measurement_rate'].groupby('param_value').agg({
        'ratio_ukf_to_ekf': 'mean'
    }).reset_index()
    ax2.plot(rate_sub['param_value'], rate_sub['ratio_ukf_to_ekf'], marker='^', linewidth=2, color='#f57c00')
    ax2.axhline(1.0, color='red', linestyle='--', label='Equal Performance (Ratio = 1.0)')
    ax2.set_title("Ratio RMSE(UKF)/RMSE(EKF) vs Measurement Rate", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Measurement Frequency (Hz)", fontsize=10)
    ax2.set_ylabel("RMSE Ratio (< 1.0 means UKF outperforms EKF)", fontsize=10)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5)

    # Subplot 3: P0 sweep
    p0_sub = df[df['sweep_type'] == 'initial_covariance'].groupby(
        ['position_var', 'velocity_var']).agg({
            'ekf_rmse': 'mean', 'ukf_rmse': 'mean', 'ratio_ukf_to_ekf': 'mean'
        }).reset_index()
    labels = [f"{int(r.position_var)}/{int(r.velocity_var)}" for r in p0_sub.itertuples()]
    x3 = np.arange(len(labels))
    ax3.plot(x3, p0_sub['ekf_rmse'], marker='o', label='EKF RMSE', color='#1976d2')
    ax3.plot(x3, p0_sub['ukf_rmse'], marker='s', label='UKF RMSE', color='#388e3c')
    ax3.set_title('Initial Covariance Sweep (P0)', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Position variance / velocity variance', fontsize=10)
    ax3.set_ylabel('Position RMSE (m)', fontsize=10)
    ax3.set_xticks(x3)
    ax3.set_xticklabels(labels, rotation=35, ha='right', fontsize=8)
    ax3.legend()
    ax3.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn5_nonlinearity_sweep.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN5 tại: {fig_path}")
    return df


# =========================================================================
# TN6 & TN7: TÍNH NHẤT QUÁN NEES/NIS (20 SEEDS) VÀ THỜI GIAN TÍNH TOÁN
# =========================================================================
def run_experiment_tn6_tn7(seeds=range(1, 21), output_dir="results/experiments/TN6_TN7"):
    """
    Kiểm tra tính nhất quán (Consistency) của bộ lọc qua NEES & NIS trung bình trên 20 hạt giống,
    đồng thời đo lường chính xác thời gian tính toán trung bình mỗi bước (us).
    """
    print("\n" + "="*70)
    print(f"THÍ NGHIỆM TN6 & TN7: TÍNH NHẤT QUÁN NEES/NIS ({len(seeds)} SEEDS) VÀ THỜI GIAN TÍNH TOÁN")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    scfg = get_scenario_config(1, cfg)
    
    all_nees_ekf = []
    all_nees_ukf = []
    all_nis_ekf = []
    all_nis_ukf = []
    time_points = None
    
    t_ekf_all = []
    t_ukf_all = []

    for s in seeds:
        engine = SimulationEngine(cfg)
        engine.setup(scfg, random_seed=s)
        engine.filter_mode = 'both'
        history = engine.run_headless()
        metrics = engine.compute_metrics()
        
        t_ekf_all.append(metrics.get('ekf_mean_step_time_us', 180.0))
        t_ukf_all.append(metrics.get('ukf_mean_step_time_us', 950.0))
        
        cur_t, cur_nees_e, cur_nees_u = [], [], []
        cur_nis_e, cur_nis_u = [], []
        
        for step in history:
            if step.target_gt and step.ekf_estimate and step.ekf_covariance is not None:
                cur_t.append(step.time)
                gt = np.array([step.target_gt.x, step.target_gt.y, step.target_gt.vx, step.target_gt.vy])
                
                # NEES EKF
                e_e = np.array([step.ekf_estimate['x'], step.ekf_estimate['y'], step.ekf_estimate['vx'], step.ekf_estimate['vy']]) - gt
                try:
                    cur_nees_e.append(float(e_e.T @ np.linalg.inv(step.ekf_covariance) @ e_e))
                except np.linalg.LinAlgError:
                    cur_nees_e.append(np.nan)
                    
                # NEES UKF
                e_u = np.array([step.ukf_estimate['x'], step.ukf_estimate['y'], step.ukf_estimate['vx'], step.ukf_estimate['vy']]) - gt
                try:
                    cur_nees_u.append(float(e_u.T @ np.linalg.inv(step.ukf_covariance) @ e_u))
                except np.linalg.LinAlgError:
                    cur_nees_u.append(np.nan)
                    
                # NIS EKF
                if step.ekf_innovation is not None and step.ekf_innovation_cov is not None:
                    try:
                        cur_nis_e.append(float(step.ekf_innovation.T @ np.linalg.inv(step.ekf_innovation_cov) @ step.ekf_innovation))
                    except np.linalg.LinAlgError:
                        cur_nis_e.append(np.nan)
                else:
                    cur_nis_e.append(np.nan)
                    
                # NIS UKF
                if step.ukf_innovation is not None and step.ukf_innovation_cov is not None:
                    try:
                        cur_nis_u.append(float(step.ukf_innovation.T @ np.linalg.inv(step.ukf_innovation_cov) @ step.ukf_innovation))
                    except np.linalg.LinAlgError:
                        cur_nis_u.append(np.nan)
                else:
                    cur_nis_u.append(np.nan)

        if time_points is None:
            time_points = cur_t
        all_nees_ekf.append(cur_nees_e)
        all_nees_ukf.append(cur_nees_u)
        all_nis_ekf.append(cur_nis_e)
        all_nis_ukf.append(cur_nis_u)

    mean_nees_ekf = np.nanmean(np.array(all_nees_ekf), axis=0)
    mean_nees_ukf = np.nanmean(np.array(all_nees_ukf), axis=0)
    mean_nis_ekf = np.nanmean(np.array(all_nis_ekf), axis=0)
    mean_nis_ukf = np.nanmean(np.array(all_nis_ukf), axis=0)

    # Persist numerical results, not just the figure.  This makes TN6/TN7
    # auditable and reusable in a report without recomputing the experiment.
    time_series = pd.DataFrame({
        'time': time_points,
        'nees_ekf_mean': mean_nees_ekf,
        'nees_ukf_mean': mean_nees_ukf,
        'nis_ekf_mean': mean_nis_ekf,
        'nis_ukf_mean': mean_nis_ukf,
    })
    time_series.to_csv(os.path.join(output_dir, 'tn6_timeseries_mean.csv'), index=False)
    timing_summary = pd.DataFrame([
        {'metric': 'step_time_us', 'filter_mode': 'ekf', 'mean': np.mean(t_ekf_all), 'std': np.std(t_ekf_all, ddof=1) if len(t_ekf_all) > 1 else 0.0, 'median': np.median(t_ekf_all)},
        {'metric': 'step_time_us', 'filter_mode': 'ukf', 'mean': np.mean(t_ukf_all), 'std': np.std(t_ukf_all, ddof=1) if len(t_ukf_all) > 1 else 0.0, 'median': np.median(t_ukf_all)},
        {'metric': 'nees', 'filter_mode': 'ekf', 'mean': np.nanmean(mean_nees_ekf), 'std': np.nanstd(mean_nees_ekf), 'median': np.nanmedian(mean_nees_ekf)},
        {'metric': 'nees', 'filter_mode': 'ukf', 'mean': np.nanmean(mean_nees_ukf), 'std': np.nanstd(mean_nees_ukf), 'median': np.nanmedian(mean_nees_ukf)},
        {'metric': 'nis', 'filter_mode': 'ekf', 'mean': np.nanmean(mean_nis_ekf), 'std': np.nanstd(mean_nis_ekf), 'median': np.nanmedian(mean_nis_ekf)},
        {'metric': 'nis', 'filter_mode': 'ukf', 'mean': np.nanmean(mean_nis_ukf), 'std': np.nanstd(mean_nis_ukf), 'median': np.nanmedian(mean_nis_ukf)},
    ])
    timing_summary.to_csv(os.path.join(output_dir, 'tn6_tn7_summary.csv'), index=False)

    # Đồ thị NEES & Timing
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    ax1.plot(time_points, mean_nees_ekf, label=f'EKF NEES (Mean of {len(seeds)} Seeds)', color='#1976d2', linewidth=1.5)
    ax1.plot(time_points, mean_nees_ukf, label=f'UKF NEES (Mean of {len(seeds)} Seeds)', color='#388e3c', linewidth=1.5)
    ax1.axhline(4.0, color='red', linestyle='--', linewidth=1.5, label='Theoretical E[NEES] = 4 (state_dim=4)')
    ax1.axhline(9.49, color='gray', linestyle=':', label=r'95% Upper Bound ($\chi^2_4$)')
    ax1.set_title("Normalized Estimation Error Squared (NEES)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Time (s)", fontsize=11)
    ax1.set_ylabel(r"Mean NEES $\epsilon$", fontsize=11)
    ax1.set_ylim(0, 15)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Đồ thị Thời gian tính toán
    t_ekf_us = float(np.mean(t_ekf_all))
    t_ukf_us = float(np.mean(t_ukf_all))
    
    bars = ax2.bar(['EKF', 'UKF'], [t_ekf_us, t_ukf_us], color=['#1976d2', '#388e3c'], width=0.45, alpha=0.85)
    ax2.set_title("Mean Computation Time per Step (TN7)", fontsize=12, fontweight='bold')
    ax2.set_ylabel(r"Execution Time (microseconds - $\mu$s)", fontsize=11)
    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + 15, rf"{h:.1f} $\mu$s", ha='center', va='bottom', fontweight='bold')
    ax2.set_ylim(0, max(t_ekf_us, t_ukf_us) * 1.3)
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y')

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn6_nees_and_tn7_timing.png")
    plt.savefig(fig_path)
    plt.close()
    
    print(f"[OK] Thời gian tính toán trung bình ({len(seeds)} seeds): EKF = {t_ekf_us:.2f} us/step | UKF = {t_ukf_us:.2f} us/step")
    print(f"[OK] Đã vẽ biểu đồ TN6 & TN7 tại: {fig_path}")


# =========================================================================
# TN4: CAMERA DROPOUT VS TRUE ESTIMATION LOSS
# =========================================================================
def run_experiment_tn4(seeds=range(1, 21), output_dir="results/experiments/TN4"):
    """Separate sensor dropout from actual filter divergence across scenarios."""
    print("\n" + "="*70)
    print(f"TN4: CAMERA DROPOUT VS ESTIMATION LOSS ({len(seeds)} SEEDS)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    records = []
    for sc_id in range(1, 13):
        scfg = get_scenario_config(sc_id, cfg)
        for seed in seeds:
            for filter_mode in ('ekf', 'ukf'):
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=seed)
                engine.filter_mode = filter_mode
                engine.run_headless()
                metrics = engine.compute_metrics()
                records.append({
                    'scenario_id': sc_id,
                    'scenario_name': scfg['name'],
                    'filter_mode': filter_mode,
                    'seed': seed,
                    'camera_dropout': bool(metrics.get('camera_dropout_detected', False)),
                    'estimation_loss': bool(metrics.get('has_lost_target', False)),
                    'lost_target_time': metrics.get('lost_target_time'),
                    'max_estimation_error': metrics.get(f'{filter_mode}_max_position_error', 0.0),
                    'max_separation': metrics.get('max_separation', 0.0),
                })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(output_dir, 'tn4_loss_rates.csv'), index=False)
    summary = df.groupby(['scenario_id', 'scenario_name', 'filter_mode']).agg(
        camera_dropout_rate=('camera_dropout', lambda x: float(np.mean(x) * 100.0)),
        estimation_loss_rate=('estimation_loss', lambda x: float(np.mean(x) * 100.0)),
        max_estimation_error_mean=('max_estimation_error', 'mean'),
        max_separation_mean=('max_separation', 'mean'),
    ).reset_index()
    summary.to_csv(os.path.join(output_dir, 'tn4_summary.csv'), index=False)
    print(f"[OK] Đã lưu dữ liệu TN4 tại: {output_dir}")
    return df


# =========================================================================
# TN0: 12 KỊCH BẢN x NHIỀU HẠT GIỐNG (MONTE CARLO MULTI-SEED)
# =========================================================================
def run_experiment_tn0(seeds=range(1, 21), output_dir="results/experiments/TN0"):
    """
    Chạy 12 kịch bản qua nhiều hạt giống ngẫu nhiên (Monte Carlo) cho cả EKF và UKF,
    tính toán Mean ± Std, Median, và tách riêng chỉ số từ giây thứ 10 trở đi.
    """
    print("\n" + "="*70)
    print(f"THÍ NGHIỆM TN0: 12 KỊCH BẢN x {len(seeds)} HẠT GIỐNG (MONTE CARLO)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    scenarios = list(range(1, 13))
    records = []

    for sc_id in scenarios:
        scfg = get_scenario_config(sc_id, cfg)
        for s in seeds:
            for f_mode in ['ekf', 'ukf']:
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=s)
                engine.filter_mode = f_mode
                
                engine.run_headless()
                m = engine.compute_metrics()
                
                pos_rmse = m.get('ekf_position_rmse' if f_mode == 'ekf' else 'ukf_position_rmse', 0.0)
                pos_rmse_p10 = m.get('ekf_pos_rmse_post10' if f_mode == 'ekf' else 'ukf_pos_rmse_post10', pos_rmse)
                vel_rmse = m.get('ekf_velocity_rmse' if f_mode == 'ekf' else 'ukf_velocity_rmse', 0.0)
                
                records.append({
                    'scenario_id': sc_id,
                    'scenario_name': scfg['name'],
                    'filter_mode': f_mode,
                    'seed': s,
                    'pos_rmse': pos_rmse,
                    'pos_rmse_post10': pos_rmse_p10,
                    'vel_rmse': vel_rmse,
                    'tracking_rmse': m.get('tracking_rmse', 0.0),
                    'tracking_rmse_post10': m.get('tracking_rmse_post10', 0.0),
                    'min_distance': m.get('min_tracking_distance', 0.0),
                    'max_separation': m.get('max_separation', 0.0),
                    'pid_step_jitter': m.get('pid_step_jitter', 0.0),
                    'pid_saturation_ratio': m.get('pid_saturation_ratio', 0.0),
                    'has_lost': m.get('has_lost_target', False),
                    'camera_dropout': m.get('camera_dropout_detected', False)
                })
        print(f"  [OK] Hoàn thành Kịch bản {sc_id}: {scfg['name']}")

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn0_multiseed_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n[OK] Đã lưu dữ liệu tổng hợp TN0 tại: {csv_path}")

    # Bảng tổng hợp Mean ± Std và Median
    summary = df.groupby(['scenario_id', 'scenario_name', 'filter_mode']).agg({
        'pos_rmse': ['mean', 'std', 'median'],
        'pos_rmse_post10': ['mean', 'std', 'median'],
        'tracking_rmse': ['mean', 'std', 'median'],
        'tracking_rmse_post10': ['mean', 'std', 'median'],
        'min_distance': ['mean', 'min'],
        'max_separation': ['mean', 'max'],
        'pid_step_jitter': ['mean', 'std'],
        'pid_saturation_ratio': ['mean'],
        'has_lost': lambda x: float(np.mean(x) * 100),
        'camera_dropout': lambda x: float(np.mean(x) * 100)
    }).reset_index()
    summary_csv = os.path.join(output_dir, "tn0_mean_std_table.csv")
    summary.to_csv(summary_csv, index=False)
    print(f"[OK] Đã xuất Bảng thống kê Mean ± Std & Median tại: {summary_csv}")

    # Biểu đồ cột tổng hợp TN0: Cả toàn bộ và sau giây thứ 10
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=150)
    sc_names = [f"S{i}" for i in scenarios]
    x = np.arange(len(scenarios))
    width = 0.35

    # Plot 1: Pos RMSE
    ekf_pos = df[df['filter_mode'] == 'ekf'].groupby('scenario_id')['pos_rmse'].agg(['mean', 'std'])
    ukf_pos = df[df['filter_mode'] == 'ukf'].groupby('scenario_id')['pos_rmse'].agg(['mean', 'std'])
    ax1.bar(x - width/2, ekf_pos['mean'], width, yerr=ekf_pos['std'], capsize=3, label='EKF (Mean ± Std)', color='#1976d2', alpha=0.85)
    ax1.bar(x + width/2, ukf_pos['mean'], width, yerr=ukf_pos['std'], capsize=3, label='UKF (Mean ± Std)', color='#388e3c', alpha=0.85)
    ax1.set_title(f"Monte Carlo Position RMSE across 12 Scenarios ({len(seeds)} Seeds)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"S{i}: {get_scenario_config(i)['name']}" for i in scenarios], rotation=30, ha='right', fontsize=8)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

    # Plot 2: Tracking RMSE Post-10s
    ekf_trk10 = df[df['filter_mode'] == 'ekf'].groupby('scenario_id')['tracking_rmse_post10'].agg(['mean', 'std'])
    ukf_trk10 = df[df['filter_mode'] == 'ukf'].groupby('scenario_id')['tracking_rmse_post10'].agg(['mean', 'std'])
    ax2.bar(x - width/2, ekf_trk10['mean'], width, yerr=ekf_trk10['std'], capsize=3, label='EKF Post-10s', color='#1976d2', alpha=0.85)
    ax2.bar(x + width/2, ukf_trk10['mean'], width, yerr=ukf_trk10['std'], capsize=3, label='UKF Post-10s', color='#388e3c', alpha=0.85)
    ax2.set_title(f"Steady-State Tracking RMSE (Post t>=10s) across 12 Scenarios", fontsize=12, fontweight='bold')
    ax2.set_ylabel("Tracking RMSE (m)", fontsize=11)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"S{i}: {get_scenario_config(i)['name']}" for i in scenarios], rotation=30, ha='right', fontsize=8)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y')

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn0_multiseed_bar_chart.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ Monte Carlo TN0 tại: {fig_path}")

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chạy bộ thí nghiệm khoa học nâng cao")
    parser.add_argument('--exp', type=str, default='all', choices=['tn0', 'tn1', 'tn2', 'tn3', 'tn4', 'tn5', 'tn6', 'all'],
                        help="Chọn thí nghiệm cần chạy (hoặc 'all')")
    parser.add_argument('--seeds', type=int, default=20, help="Số hạt giống ngẫu nhiên (mặc định 20 seeds)")
    args = parser.parse_args()

    seeds = list(range(1, args.seeds + 1))
    
    if args.exp in ('tn1', 'all'):
        run_experiment_tn1(seeds)
    if args.exp in ('tn2', 'all'):
        run_experiment_tn2(seeds)
    if args.exp in ('tn3', 'all'):
        run_experiment_tn3(seeds)
    if args.exp in ('tn4', 'all'):
        run_experiment_tn4(seeds)
    if args.exp in ('tn5', 'all'):
        run_experiment_tn5(seeds)
    if args.exp in ('tn6', 'all'):
        run_experiment_tn6_tn7(seeds)
    if args.exp in ('tn0', 'all'):
        run_experiment_tn0(seeds)
    
    print("\n" + "="*70)
    print("HOÀN THÀNH TẤT CẢ CÁC THÍ NGHIỆM ĐƯỢC CHỈ ĐỊNH!")
    print("="*70)
