# BeyondMimic Dance Motion Training Project

**Author:** Guangjun Xu
**Date:** January 2026
**Supervisor:** [Professor Name]

## Project Overview

This project implements motion retargeting from GMR (General Motion Retargeting) to BeyondMimic format for training humanoid robots (Unitree G1) to perform dance motions. The key contribution is a novel converter that properly computes all body states using Isaac Sim forward kinematics, replacing the previous template-based approach.

## Problem Statement

**Original Issue:** GMR outputs only 3 arrays (root position, root rotation, joint positions), while BeyondMimic requires 7 arrays including full body states and velocities for all 30 body parts.

**Previous Solution:** Template-based resampling (approximate, led to poor training results)

**Our Solution:** Direct forward kinematics computation using Isaac Sim for accurate body states

## Repository Structure

```
BeyondMimic-Dance-Project/
├── README.md                          # This file
├── converter/
│   └── gmr_pkl_to_beyondmimic_npz.py # Main converter script
├── docs/
│   ├── GMR_to_BeyondMimic_Converter_README.md
│   ├── GMR_vs_BeyondMimic_Format_Comparison.md
│   └── UPLOAD_INSTRUCTIONS.md
├── experiments/
│   ├── training_logs/                 # Training experiment logs
│   └── results/                       # Trained models and results
├── reports/
│   └── experiment_results.md          # Detailed experiment analysis
└── models/                            # Saved model checkpoints
```

## Key Components

### 1. GMR to BeyondMimic Converter

**File:** `converter/gmr_pkl_to_beyondmimic_npz.py`

**Key Features:**
- Direct PKL → NPZ conversion (no intermediate CSV)
- Isaac Sim forward kinematics for all 30 body parts
- Proper velocity computation via finite differences
- Z-offset support for foot grounding
- Based on proven `replay_go2_npz.py` methodology

**Input Format (GMR PKL):**
```python
{
    'fps': 30,
    'root_pos': (450, 3),      # Root position
    'root_rot': (450, 4),      # Root quaternion [x,y,z,w]
    'dof_pos': (450, 29),      # Joint angles
}
```

**Output Format (BeyondMimic NPZ):**
```python
{
    'fps': 30,
    'joint_pos': (450, 29),           # Joint positions
    'joint_vel': (450, 29),           # Joint velocities ← COMPUTED
    'body_pos_w': (450, 30, 3),       # All body positions ← COMPUTED
    'body_quat_w': (450, 30, 4),      # All body quaternions ← COMPUTED
    'body_lin_vel_w': (450, 30, 3),   # Body linear velocities ← COMPUTED
    'body_ang_vel_w': (450, 30, 3),   # Body angular velocities ← COMPUTED
}
```

**Usage:**
```bash
python converter/gmr_pkl_to_beyondmimic_npz.py \
  --input motions/dance_1_g1_15s.pkl \
  --output dance_1_g1_15s_CONVERTED \
  --z_offset -0.15 \
  --headless
```

### 2. Format Comparison Analysis

**File:** `docs/GMR_vs_BeyondMimic_Format_Comparison.md`

Comprehensive 661-line analysis covering:
- Data structure differences
- Body state computation requirements
- Coordinate frame transformations
- Velocity computation methods
- File size expansion (127 KB → 796 KB)

## Experiments

### Previous Experiments (Template-Based Method)

**Problem:** Using template NPZ resampling led to:
- Only root body updated, others approximated
- Inaccurate velocity computations
- Poor training results with early episode terminations

**Threshold Experiments (Jan 6, 2026):**

| Threshold | Iterations | Status | Checkpoint Count | Completion Time |
|-----------|-----------|--------|------------------|-----------------|
| 0.50m     | 10,000    | ✅     | 21 models        | Jan 7 00:59:45  |
| 0.75m     | 10,000    | ✅     | 21 models        | Jan 7 00:56:58  |
| 1.00m     | 10,000    | ✅     | 21 models        | Jan 7 00:14:35  |

**Conclusion:** Threshold adjustments did not solve the core problem - the issue was data format accuracy.

### Current Experiment (New CONVERTED Format)

**Run Name:** `dance_15s_CONVERTED_thresh_025`
**Start Time:** Jan 12, 2026 10:54
**Status:** 🔄 Running
**WandB Link:** https://wandb.ai/violetxu219/robot_dance_episode_length/runs/unftugpz

**Parameters:**
- Task: `Tracking-Flat-G1-v0`
- Robot: Unitree G1 (30 bodies, 29 DoF)
- Motion: `dance_1_g1_15s_CONVERTED` (proper FK computation)
- Threshold: 0.25m
- Max Iterations: 10,000
- Environments: 4096
- Logger: WandB
- Project: `robot_dance_episode_length`

**Expected Improvements:**
- Accurate body state tracking
- Better episode length retention
- Smoother motion reproduction
- Higher policy learning efficiency

## Technical Details

### Robot Specifications

**Unitree G1 Humanoid:**
- Total Bodies: 30
- Total Joints: 29 DoF
- Root: pelvis
- Key Bodies: torso, left/right legs (hip, knee, ankle), left/right arms (shoulder, elbow, wrist)

### Motion Data

**Source Motion:** `dance_1_g1_15s.pkl`
- Duration: 15 seconds
- Frame Rate: 30 FPS
- Total Frames: 450
- DoF: 29 joints

**Z-Offset:** -0.15m (for proper foot grounding)
- Original Z-range: [0.863, 1.157]
- Adjusted Z-range: [0.713, 1.007]

### Velocity Computation

**Joint Velocities:**
```python
v[i] = (pos[i] - pos[i-1]) / dt
```

**Body Linear Velocities:**
```python
v_lin[i] = (pos_w[i] - pos_w[i-1]) / dt
```

**Body Angular Velocities:**
```python
# Quaternion derivative approximation
dq = quat[i] - quat[i-1]
v_ang[i] = 2 * dq[:3] / dt
```

## Results

### Converter Validation

✅ **NPZ Output Verification:**
```
File: dance_1_g1_15s_CONVERTED:v0/motion.npz
File size: 796 KB

Arrays and Shapes:
  fps                 : 30
  joint_pos           : (450, 29) ✓
  joint_vel           : (450, 29) ✓
  body_pos_w          : (450, 30, 3) ✓
  body_quat_w         : (450, 30, 4) ✓
  body_lin_vel_w      : (450, 30, 3) ✓
  body_ang_vel_w      : (450, 30, 3) ✓
  body_names          : (30,)
  joint_names         : (29,)

✅ All arrays present with correct shapes!
✅ Format matches BeyondMimic requirements!
```

### Training Metrics (Early Stage)

From WandB run (first iterations):
```
Metrics/motion/error_anchor_pos: 0.5284
Metrics/motion/error_anchor_rot: 0.8920
Metrics/motion/error_body_pos: 0.5320
Metrics/motion/error_body_rot: 1.2328
Metrics/motion/error_joint_pos: 3.0167

Total timesteps: 2,260,992
Iteration time: 2.23s
ETA: ~6-7 hours
```

## Installation & Setup

### Prerequisites
- Ubuntu 22.04
- NVIDIA GPU (8x RTX 4090 available)
- Isaac Sim 4.5
- Isaac Lab environment
- Conda environment: `isaaclab`

### Remote Server Setup
```bash
ssh xgj@10.13.238.34
cd ~/projects/BeyondMimic
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab
export OMNI_KIT_ACCEPT_EULA=YES
```

### Upload Converter
```bash
# From local Mac
scp converter/gmr_pkl_to_beyondmimic_npz.py xgj@10.13.238.34:~/projects/BeyondMimic/scripts/
```

### Run Converter
```bash
python scripts/gmr_pkl_to_beyondmimic_npz.py \
  --input motions/dance_1_g1_15s.pkl \
  --output dance_1_g1_15s_CONVERTED \
  --z_offset -0.15 \
  --headless
```

### Start Training
```bash
python scripts/rsl_rl/train.py \
  --task=Tracking-Flat-G1-v0 \
  --headless \
  --max_iterations=10000 \
  --run_name=dance_15s_CONVERTED_thresh_025 \
  --logger wandb \
  --log_project_name robot_dance_episode_length
```

## Key Findings

### 1. Data Format is Critical
- Template-based approximation → poor results
- Proper forward kinematics → expected better results

### 2. Threshold is Not the Primary Issue
- Tested 0.50m, 0.75m, 1.00m thresholds
- All completed training but didn't solve core problem
- Issue was data accuracy, not threshold tuning

### 3. Forward Kinematics Approach
- Adapted from `replay_go2_npz.py` (quadruped)
- Successfully applied to G1 (humanoid)
- Computes all 30 body states accurately

## Future Work

1. **Complete Current Training**
   - Monitor training to 10,000 iterations
   - Analyze final episode lengths
   - Compare with template-based results

2. **Policy Evaluation**
   - Replay trained policy
   - Record video demonstrations
   - Measure motion tracking accuracy

3. **Additional Motions**
   - Test converter on other dance sequences
   - Batch processing pipeline
   - Multiple motion dataset training

4. **Optimization**
   - Hyperparameter tuning
   - Reward function adjustments
   - Network architecture experiments

## References

- **GMR:** General Motion Retargeting for humanoid robots
- **BeyondMimic:** Motion tracking via guided diffusion
- **Isaac Sim:** NVIDIA physics simulation platform
- **Isaac Lab:** Robot learning framework
- **replay_go2_npz.py:** Reference implementation for quadruped

## Citation

If you use this work, please cite:
```bibtex
@misc{xu2026beyondmimic_dance,
  author = {Xu, Guangjun},
  title = {BeyondMimic Dance Motion Training with Proper Forward Kinematics},
  year = {2026},
  month = {January},
  note = {Humanoid robot motion retargeting and training}
}
```

## Contact

**Student:** Guangjun Xu
**Email:** [Your Email]
**GitHub:** [Your GitHub]
**WandB:** violetxu219

---

**Last Updated:** January 12, 2026
**Project Status:** Active Development
**Current Phase:** Training with properly converted motion data
