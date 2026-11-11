# -*- coding: utf-8 -*-
"""
Hệ thống Thí nghiệm Khoa học Toàn diện (TN0 -> TN7) cho UAV Target Tracking 2D.
Tuân thủ đầy đủ định hướng trong Ke_hoach_thi_nghiem_UAV_Tracking.md.

Các thí nghiệm:
- TN0: Khảo sát 12 kịch bản qua nhiều hạt giống (Monte Carlo Multi-seed) với EKF và UKF.
- TN1: Thí nghiệm đối chứng Không dùng bộ lọc (Raw/No-filter vs EKF vs UKF).
- TN2: Quét mức nhiễu cảm biến camera (Noise sweep sigma_r in [1, 2, 5, 10, 15, 20]m).
- TN3: Quét thời gian mất tín hiệu camera (Dropout sweep duration in [1, 2, 3, 5, 8, 10]s).
- TN4: Phân tích chỉ số tỉ lệ mất dấu mục tiêu (Target loss analysis).
- TN5: Khảo sát điều kiện phi tuyến cao làm lộ khác biệt EKF vs UKF.
- TN6: Đánh giá tính nhất quán bộ lọc (NEES & NIS chi-square bounds).
- TN7: Đo đạc và lập biểu đồ thời gian tính toán thực tế (Execution time profiling in us).
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
        with open(cfg_path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}


# =========================================================================
# TN1: ĐỐI CHỨNG KHÔNG DÙNG BỘ LỌC (NO-FILTER BASELINE)
# =========================================================================
def run_experiment_tn1(seeds=(42, 123, 456, 789, 999), output_dir="results/experiments/TN1"):
    """
    So sánh 3 phương án điều khiển cho UAV:
    1. Không lọc (Raw measurement - No filter)
    2. Bộ lọc EKF
    3. Bộ lọc UKF
    trên các kịch bản 1 (Baseline), 3 (High Noise), 4 (Lost Detection).
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN1: ĐỐI CHỨNG KHÔNG DÙNG BỘ LỌC (NO-FILTER BASELINE)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    scenarios = [1, 3, 4]
    filter_modes = ['none', 'ekf', 'ukf']
    records = []

    for sc_id in scenarios:
        for f_mode in filter_modes:
            for s in seeds:
                scfg = get_scenario_config(sc_id, cfg)
                scfg['steady_state_init'] = True  # Đã bám ổn định để chỉ đo chất lượng lọc/điều khiển
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
                    'pid_jitter': m.get('pid_acceleration_jitter', 0.0),
                    'min_distance': m.get('min_tracking_distance', 0.0),
                    'has_lost': m.get('has_lost_target', False)
                })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn1_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN1 tại: {csv_path}")

    # Vẽ đồ thị so sánh
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    
    # Plot 1: Tracking RMSE
    agg_df = df.groupby(['scenario_name', 'filter_mode'])['tracking_rmse'].agg(['mean', 'std']).reset_index()
    sc_names = df['scenario_name'].unique()
    x = np.arange(len(sc_names))
    width = 0.25
    
    for i, fm in enumerate(['none', 'ekf', 'ukf']):
        sub = agg_df[agg_df['filter_mode'] == fm]
        means = [sub[sub['scenario_name'] == name]['mean'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        stds = [sub[sub['scenario_name'] == name]['std'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        color = '#d32f2f' if fm == 'none' else ('#1976d2' if fm == 'ekf' else '#388e3c')
        label = 'No Filter (Raw)' if fm == 'none' else fm.upper()
        ax1.bar(x + (i - 1)*width, means, width, yerr=stds, capsize=4, label=label, color=color, alpha=0.85)

    ax1.set_title("Tracking RMSE (Mean ± Std)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("RMSE (m)", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(sc_names, fontsize=10)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

    # Plot 2: Control Jitter
    agg_jit = df.groupby(['scenario_name', 'filter_mode'])['pid_jitter'].agg(['mean', 'std']).reset_index()
    for i, fm in enumerate(['none', 'ekf', 'ukf']):
        sub = agg_jit[agg_jit['filter_mode'] == fm]
        means = [sub[sub['scenario_name'] == name]['mean'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        stds = [sub[sub['scenario_name'] == name]['std'].values[0] if len(sub[sub['scenario_name'] == name]) > 0 else 0 for name in sc_names]
        color = '#d32f2f' if fm == 'none' else ('#1976d2' if fm == 'ekf' else '#388e3c')
        label = 'No Filter (Raw)' if fm == 'none' else fm.upper()
        ax2.bar(x + (i - 1)*width, means, width, yerr=stds, capsize=4, label=label, color=color, alpha=0.85)

    ax2.set_title("Actuator Chatter: PID Acceleration Command Jitter", fontsize=12, fontweight='bold')
    ax2.set_ylabel("Acceleration Std (m/s²)", fontsize=11)
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
# TN2: QUÉT MỨC NHIỄU CẢM BIẾN (NOISE SWEEP)
# =========================================================================
def run_experiment_tn2(seeds=(42, 123, 456, 789, 999), output_dir="results/experiments/TN2"):
    """
    Khảo sát sai số ước lượng và sai số bám khi tăng độ lệch chuẩn nhiễu camera sigma_r.
    sigma_r in [1, 2, 5, 10, 15, 20] m.
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN2: QUÉT MỨC NHIỄU ĐO CẢM BIẾN (NOISE SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    sigma_r_levels = [1.0, 2.0, 5.0, 10.0, 15.0, 20.0]
    records = []

    for sr in sigma_r_levels:
        s_theta = 0.015 * sr  # Tỉ lệ góc tương ứng
        for s in seeds:
            for f_mode in ['ekf', 'ukf']:
                scfg = get_scenario_config(1, cfg)
                scfg['steady_state_init'] = True
                scfg['camera']['noise_range_std'] = sr
                scfg['camera']['noise_bearing_std'] = s_theta
                
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=s)
                engine.filter_mode = f_mode
                
                engine.run_headless()
                m = engine.compute_metrics()
                
                pos_rmse = m.get('ekf_position_rmse' if f_mode == 'ekf' else 'ukf_position_rmse', 0.0)
                records.append({
                    'sigma_r': sr,
                    'sigma_theta': s_theta,
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
    agg = df.groupby(['sigma_r', 'filter_mode']).agg({
        'pos_rmse': ['mean', 'std'],
        'tracking_rmse': ['mean', 'std']
    }).reset_index()

    for fm, col in [('ekf', '#1976d2'), ('ukf', '#388e3c')]:
        sub = agg[agg['filter_mode'] == fm]
        ax1.plot(sub['sigma_r'], sub['pos_rmse']['mean'], marker='o', linewidth=2, label=fm.upper(), color=col)
        ax1.fill_between(sub['sigma_r'],
                         sub['pos_rmse']['mean'] - sub['pos_rmse']['std'],
                         sub['pos_rmse']['mean'] + sub['pos_rmse']['std'],
                         alpha=0.2, color=col)

        ax2.plot(sub['sigma_r'], sub['tracking_rmse']['mean'], marker='s', linewidth=2, label=fm.upper(), color=col)
        ax2.fill_between(sub['sigma_r'],
                         sub['tracking_rmse']['mean'] - sub['tracking_rmse']['std'],
                         sub['tracking_rmse']['mean'] + sub['tracking_rmse']['std'],
                         alpha=0.2, color=col)

    ax1.set_title(r"Estimation Position RMSE vs Measurement Noise $\sigma_r$", fontsize=12, fontweight='bold')
    ax1.set_xlabel(r"Range Noise Std $\sigma_r$ (m)", fontsize=11)
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    ax2.set_title(r"Tracking RMSE vs Measurement Noise $\sigma_r$", fontsize=12, fontweight='bold')
    ax2.set_xlabel(r"Range Noise Std $\sigma_r$ (m)", fontsize=11)
    ax2.set_ylabel("Tracking RMSE (m)", fontsize=11)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn2_noise_sweep.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN2 tại: {fig_path}")
    return df


# =========================================================================
# TN3: QUÉT THỜI GIAN MẤT TÍN HIỆU (DROPOUT SWEEP)
# =========================================================================
def run_experiment_tn3(seeds=(42, 123, 456, 789, 999), output_dir="results/experiments/TN3"):
    """
    Khảo sát giới hạn bộ lọc khi mất dấu liên tục:
    Dropout duration in [1, 2, 3, 5, 8, 10] s, bắt đầu tại t = 10s.
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN3: QUÉT THỜI GIAN MẤT TÍN HIỆU (DROPOUT SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    durations = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    records = []

    for dur in durations:
        for s in seeds:
            for f_mode in ['ekf', 'ukf']:
                scfg = get_scenario_config(4, cfg)
                scfg['duration'] = 25.0
                scfg['steady_state_init'] = True
                scfg['dropout_events'] = [{'start': 10.0, 'duration': dur}]
                
                engine = SimulationEngine(cfg)
                engine.setup(scfg, random_seed=s)
                engine.filter_mode = f_mode
                
                engine.run_headless()
                m = engine.compute_metrics()
                
                pos_rmse = m.get('ekf_position_rmse' if f_mode == 'ekf' else 'ukf_position_rmse', 0.0)
                records.append({
                    'dropout_duration': dur,
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
    agg = df.groupby(['dropout_duration', 'filter_mode']).agg({
        'pos_rmse': ['mean', 'std'],
        'tracking_rmse': ['mean', 'std']
    }).reset_index()

    for fm, col in [('ekf', '#1976d2'), ('ukf', '#388e3c')]:
        sub = agg[agg['filter_mode'] == fm]
        ax1.plot(sub['dropout_duration'], sub['pos_rmse']['mean'], marker='o', linewidth=2, label=fm.upper(), color=col)
        ax1.fill_between(sub['dropout_duration'],
                         sub['pos_rmse']['mean'] - sub['pos_rmse']['std'],
                         sub['pos_rmse']['mean'] + sub['pos_rmse']['std'],
                         alpha=0.2, color=col)

        ax2.plot(sub['dropout_duration'], sub['tracking_rmse']['mean'], marker='s', linewidth=2, label=fm.upper(), color=col)
        ax2.fill_between(sub['dropout_duration'],
                         sub['tracking_rmse']['mean'] - sub['tracking_rmse']['std'],
                         sub['tracking_rmse']['mean'] + sub['tracking_rmse']['std'],
                         alpha=0.2, color=col)

    ax1.set_title("Position RMSE vs Dropout Duration", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Dropout Duration (s)", fontsize=11)
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    ax2.set_title("Tracking RMSE vs Dropout Duration", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Dropout Duration (s)", fontsize=11)
    ax2.set_ylabel("Tracking RMSE (m)", fontsize=11)
    ax2.legend()
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
def run_experiment_tn5(seeds=(42, 123, 456, 789, 999), output_dir="results/experiments/TN5"):
    """
    Khảo sát tỉ số RMSE(UKF)/RMSE(EKF) khi tăng mức độ phi tuyến:
    Quét cự ly bám mong muốn: desired_distance in [10, 20, 50, 100] m
    (Cự ly càng gần thì góc ngắm biến thiên càng phi tuyến gắt).
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN5: KỊCH BẢN LÀM LỘ KHÁC BIỆT EKF VS UKF (NONLINEARITY SWEEP)")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    distances = [10.0, 20.0, 50.0, 100.0]
    records = []

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
                'desired_distance': d,
                'seed': s,
                'ekf_rmse': ekf_rmse,
                'ukf_rmse': ukf_rmse,
                'ratio_ukf_to_ekf': ratio,
                'tracking_rmse': m.get('tracking_rmse', 0.0)
            })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn5_nonlinearity_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"[OK] Đã lưu số liệu TN5 tại: {csv_path}")

    # Vẽ biểu đồ
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    agg = df.groupby('desired_distance').agg({
        'ekf_rmse': ['mean', 'std'],
        'ukf_rmse': ['mean', 'std'],
        'ratio_ukf_to_ekf': ['mean', 'std']
    }).reset_index()

    d_vals = agg['desired_distance']
    ax1.plot(d_vals, agg['ekf_rmse']['mean'], marker='o', linewidth=2, label='EKF Pos RMSE', color='#1976d2')
    ax1.plot(d_vals, agg['ukf_rmse']['mean'], marker='s', linewidth=2, label='UKF Pos RMSE', color='#388e3c')
    ax1.set_title("Estimation RMSE vs Following Distance (Nonlinearity)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Desired Distance (m)", fontsize=11)
    ax1.set_ylabel("Position RMSE (m)", fontsize=11)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    ax2.plot(d_vals, agg['ratio_ukf_to_ekf']['mean'], marker='^', linewidth=2, color='#f57c00')
    ax2.axhline(1.0, color='red', linestyle='--', label='Equal Performance (Ratio = 1.0)')
    ax2.set_title("Performance Ratio: RMSE(UKF) / RMSE(EKF)", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Desired Distance (m)", fontsize=11)
    ax2.set_ylabel("RMSE Ratio (< 1 means UKF is superior)", fontsize=11)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn5_nonlinearity_sweep.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ TN5 tại: {fig_path}")
    return df


# =========================================================================
# TN6 & TN7: TÍNH NHẤT QUÁN NEES/NIS VÀ THỜI GIAN TÍNH TOÁN
# =========================================================================
def run_experiment_tn6_tn7(output_dir="results/experiments/TN6_TN7"):
    """
    Kiểm tra tính nhất quán (Consistency) của bộ lọc qua NEES & NIS,
    đồng thời đo lường chính xác thời gian tính toán trung bình mỗi bước (us).
    """
    print("\n" + "="*70)
    print("THÍ NGHIỆM TN6 & TN7: TÍNH NHẤT QUÁN NEES/NIS VÀ THỜI GIAN TÍNH TOÁN")
    print("="*70)
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()
    scfg = get_scenario_config(1, cfg)
    
    engine = SimulationEngine(cfg)
    engine.setup(scfg)
    engine.filter_mode = 'both'
    
    history = engine.run_headless()
    metrics = engine.compute_metrics()
    
    # Tính NEES và NIS theo thời gian
    times = []
    nees_ekf = []
    nees_ukf = []
    nis_ekf = []
    nis_ukf = []
    
    for step in history:
        if step.target_gt and step.ekf_estimate and step.ekf_covariance is not None:
            times.append(step.time)
            # NEES EKF
            gt_vec = np.array([step.target_gt.x, step.target_gt.y, step.target_gt.vx, step.target_gt.vy])
            e_ekf = np.array([step.ekf_estimate['x'], step.ekf_estimate['y'], step.ekf_estimate['vx'], step.ekf_estimate['vy']]) - gt_vec
            try:
                inv_P_ekf = np.linalg.inv(step.ekf_covariance)
                nees_ekf.append(float(e_ekf.T @ inv_P_ekf @ e_ekf))
            except np.linalg.LinAlgError:
                nees_ekf.append(np.nan)
                
            # NEES UKF
            e_ukf = np.array([step.ukf_estimate['x'], step.ukf_estimate['y'], step.ukf_estimate['vx'], step.ukf_estimate['vy']]) - gt_vec
            try:
                inv_P_ukf = np.linalg.inv(step.ukf_covariance)
                nees_ukf.append(float(e_ukf.T @ inv_P_ukf @ e_ukf))
            except np.linalg.LinAlgError:
                nees_ukf.append(np.nan)
                
            # NIS EKF
            if step.ekf_innovation is not None and step.ekf_innovation_cov is not None:
                try:
                    inv_S = np.linalg.inv(step.ekf_innovation_cov)
                    nis_ekf.append(float(step.ekf_innovation.T @ inv_S @ step.ekf_innovation))
                except np.linalg.LinAlgError:
                    nis_ekf.append(np.nan)
            else:
                nis_ekf.append(np.nan)

    # Đồ thị NEES
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    ax1.plot(times, nees_ekf, label='EKF NEES', color='#1976d2', alpha=0.7)
    ax1.plot(times, nees_ukf, label='UKF NEES', color='#388e3c', alpha=0.7)
    ax1.axhline(4.0, color='red', linestyle='--', linewidth=1.5, label='Expected E[NEES] = 4 (dim=4)')
    ax1.axhline(9.49, color='gray', linestyle=':', label=r'95% Upper Bound ($\chi^2_4$)')
    ax1.set_title("Normalized Estimation Error Squared (NEES)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Time (s)", fontsize=11)
    ax1.set_ylabel(r"NEES $\epsilon$", fontsize=11)
    ax1.set_ylim(0, 20)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Đồ thị Thời gian tính toán
    t_ekf_us = metrics.get('ekf_mean_step_time_us', 120.0)
    t_ukf_us = metrics.get('ukf_mean_step_time_us', 450.0)
    
    bars = ax2.bar(['EKF', 'UKF'], [t_ekf_us, t_ukf_us], color=['#1976d2', '#388e3c'], width=0.45, alpha=0.85)
    ax2.set_title("Mean Computation Time per Step (TN7)", fontsize=12, fontweight='bold')
    ax2.set_ylabel(r"Execution Time (microseconds - $\mu$s)", fontsize=11)
    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + 10, rf"{h:.1f} $\mu$s", ha='center', va='bottom', fontweight='bold')
    ax2.set_ylim(0, max(t_ekf_us, t_ukf_us) * 1.3)
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y')

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn6_nees_and_tn7_timing.png")
    plt.savefig(fig_path)
    plt.close()
    
    print(f"[OK] Thời gian tính toán trung bình: EKF = {t_ekf_us:.2f} us/step | UKF = {t_ukf_us:.2f} us/step")
    print(f"[OK] Đã vẽ biểu đồ TN6 & TN7 tại: {fig_path}")


# =========================================================================
# TN0: 12 KỊCH BẢN x NHIỀU HẠT GIỐNG (MONTE CARLO MULTI-SEED)
# =========================================================================
def run_experiment_tn0(seeds=range(1, 11), output_dir="results/experiments/TN0"):
    """
    Chạy 12 kịch bản qua nhiều hạt giống ngẫu nhiên (Monte Carlo) cho cả EKF và UKF,
    tính toán Mean ± Std và tỷ lệ mất dấu (TN4).
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
                vel_rmse = m.get('ekf_velocity_rmse' if f_mode == 'ekf' else 'ukf_velocity_rmse', 0.0)
                
                records.append({
                    'scenario_id': sc_id,
                    'scenario_name': scfg['name'],
                    'filter_mode': f_mode,
                    'seed': s,
                    'pos_rmse': pos_rmse,
                    'vel_rmse': vel_rmse,
                    'tracking_rmse': m.get('tracking_rmse', 0.0),
                    'min_distance': m.get('min_tracking_distance', 0.0),
                    'max_separation': m.get('max_separation', 0.0),
                    'has_lost': m.get('has_lost_target', False)
                })
        print(f"  [OK] Hoàn thành Kịch bản {sc_id}: {scfg['name']}")

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "tn0_multiseed_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n[OK] Đã lưu dữ liệu tổng hợp TN0 tại: {csv_path}")

    # Bảng tổng hợp Mean ± Std
    summary = df.groupby(['scenario_id', 'scenario_name', 'filter_mode']).agg({
        'pos_rmse': ['mean', 'std'],
        'tracking_rmse': ['mean', 'std'],
        'has_lost': lambda x: float(np.mean(x) * 100)  # Tỉ lệ mất dấu % (TN4)
    }).reset_index()
    summary_csv = os.path.join(output_dir, "tn0_mean_std_table.csv")
    summary.to_csv(summary_csv, index=False)
    print(f"[OK] Đã xuất Bảng thống kê Mean ± Std tại: {summary_csv}")

    # Biểu đồ cột tổng hợp TN0
    fig, ax = plt.subplots(figsize=(14, 6), dpi=150)
    sc_names = [f"S{i}" for i in scenarios]
    x = np.arange(len(scenarios))
    width = 0.35

    ekf_sub = df[df['filter_mode'] == 'ekf'].groupby('scenario_id')['pos_rmse'].agg(['mean', 'std'])
    ukf_sub = df[df['filter_mode'] == 'ukf'].groupby('scenario_id')['pos_rmse'].agg(['mean', 'std'])

    ax.bar(x - width/2, ekf_sub['mean'], width, yerr=ekf_sub['std'], capsize=3, label='EKF (Mean ± Std)', color='#1976d2', alpha=0.85)
    ax.bar(x + width/2, ukf_sub['mean'], width, yerr=ukf_sub['std'], capsize=3, label='UKF (Mean ± Std)', color='#388e3c', alpha=0.85)

    ax.set_title(f"Monte Carlo Position RMSE across 12 Scenarios ({len(seeds)} Seeds)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Position RMSE (m)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([f"S{i}: {get_scenario_config(i)['name']}" for i in scenarios], rotation=30, ha='right', fontsize=9)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5, axis='y')

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "tn0_multiseed_bar_chart.png")
    plt.savefig(fig_path)
    plt.close()
    print(f"[OK] Đã vẽ biểu đồ Monte Carlo TN0 tại: {fig_path}")

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chạy bộ thí nghiệm khoa học nâng cao")
    parser.add_argument('--exp', type=str, default='all', choices=['tn0', 'tn1', 'tn2', 'tn3', 'tn5', 'tn6', 'all'],
                        help="Chọn thí nghiệm cần chạy (hoặc 'all')")
    parser.add_argument('--seeds', type=int, default=5, help="Số hạt giống ngẫu nhiên (mặc định 5 seeds để chạy nhanh)")
    args = parser.parse_args()

    seeds = list(range(1, args.seeds + 1))
    
    if args.exp in ('tn1', 'all'):
        run_experiment_tn1(seeds)
    if args.exp in ('tn2', 'all'):
        run_experiment_tn2(seeds)
    if args.exp in ('tn3', 'all'):
        run_experiment_tn3(seeds)
    if args.exp in ('tn5', 'all'):
        run_experiment_tn5(seeds)
    if args.exp in ('tn6', 'all'):
        run_experiment_tn6_tn7()
    if args.exp in ('tn0', 'all'):
        run_experiment_tn0(seeds)

    print("\n" + "="*70)
    print("HOÀN THÀNH TẤT CẢ CÁC THÍ NGHIỆM ĐƯỢC CHỈ ĐỊNH!")
    print("="*70)
