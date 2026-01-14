# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project converts GMR (General Motion Retargeting) dance motions to BeyondMimic NPZ format and trains humanoid robots (Unitree G1) to perform these motions using reinforcement learning in Isaac Sim/Isaac Lab.

**Key Innovation:** Direct PKL→NPZ conversion using Isaac Sim forward kinematics to compute all 30 body states accurately, replacing the previous template-based approximation that led to poor training results.

## High-Level Architecture

### Data Pipeline
```
GMR PKL (3 arrays) → Isaac Sim FK → BeyondMimic NPZ (7 arrays) → RL Training → Trained Policy
```

1. **GMR Output**: `root_pos`, `root_rot`, `dof_pos` (450 frames, 29 DoF)
2. **Converter**: Uses Isaac Sim to compute full body states for all 30 bodies via forward kinematics
3. **BeyondMimic Format**: Adds `joint_vel`, `body_pos_w`, `body_quat_w`, `body_lin_vel_w`, `body_ang_vel_w`
4. **Training**: PPO algorithm with 4096 parallel environments tracks reference motion

### Critical Design Decision

The converter simulates each frame in Isaac Sim to capture computed body states rather than approximating them. This is based on the proven `replay_go2_npz.py` methodology from the quadruped robot and ensures accurate training data for all 30 body parts.

## Remote Server Workflow

This project runs on a remote GPU server, not locally.

**Server Details:**
- Host: `xgj@10.13.238.34`
- GPUs: 8× NVIDIA RTX 4090 (24GB each)
- Base Path: `/data/home/xgj/projects/BeyondMimic/`
- Conda Environment: `isaaclab`

### Standard Session Setup
```bash
ssh xgj@10.13.238.34
cd ~/projects/BeyondMimic
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab
export OMNI_KIT_ACCEPT_EULA=YES
```

### File Upload from Mac
```bash
# Upload converter script
scp converter/gmr_pkl_to_beyondmimic_npz.py xgj@10.13.238.34:~/projects/BeyondMimic/scripts/

# Upload motion data
scp dance_motion.pkl xgj@10.13.238.34:~/projects/BeyondMimic/motions/
```

## Common Commands

### Convert GMR PKL to BeyondMimic NPZ
```bash
python scripts/gmr_pkl_to_beyondmimic_npz.py \
  --input motions/dance_1_g1_15s.pkl \
  --output dance_1_g1_15s_CONVERTED \
  --z_offset -0.15 \
  --headless
```
- Output location: `artifacts/OUTPUT_NAME:v0/motion.npz`
- Z-offset -0.15m is critical for proper foot grounding
- Expects ~2-3 minutes for 450 frames (15 seconds at 30 FPS)
- Output file should be ~790 KB (expansion from 127 KB PKL)

### Train Motion Tracking Policy
```bash
python scripts/rsl_rl/train.py \
  --task=Tracking-Flat-G1-v0 \
  --headless \
  --max_iterations=10000 \
  --run_name=dance_15s_CONVERTED_thresh_025 \
  --logger wandb \
  --log_project_name robot_dance_episode_length
```
- Training takes ~6-7 hours for 10,000 iterations
- Creates checkpoints every 500 iterations
- WandB project: `robot_dance_episode_length` (user: violetxu219)

### Replay Trained Policy
```bash
python scripts/rsl_rl/play.py \
  --task=Tracking-Flat-G1-v0 \
  --num_envs=1 \
  --checkpoint=/path/to/model.pt
```

### Verify NPZ Format
```bash
python -c "
import numpy as np
data = np.load('artifacts/MOTION_NAME:v0/motion.npz')
print('Arrays:', list(data.keys()))
for k in data.keys():
    if hasattr(data[k], 'shape'):
        print(f'  {k}: {data[k].shape}')
"
```

Expected output for 15s motion:
```
fps: 30
joint_pos: (450, 29)
joint_vel: (450, 29)
body_pos_w: (450, 30, 3)
body_quat_w: (450, 30, 4)
body_lin_vel_w: (450, 30, 3)
body_ang_vel_w: (450, 30, 3)
```

## Critical Technical Details

### Robot Configuration (Unitree G1)
- 30 bodies (pelvis is root, index 0)
- 29 DoF joints
- URDF: `/data/home/xgj/projects/BeyondMimic/source/whole_body_tracking/whole_body_tracking/assets/unitree_description/urdf/g1/main.urdf`
- Body order matters: Isaac Sim provides bodies in specific order that must match training expectations

### Z-Offset Rationale
GMR outputs have the robot too high off the ground. The `-0.15m` offset is empirically determined to:
- Ensure feet make proper ground contact
- Prevent floating appearance
- Original Z-range: [0.863, 1.157] → Adjusted: [0.713, 1.007]

### Velocity Computation
Velocities are computed via finite differences, not from simulation physics:
- `joint_vel[i] = (joint_pos[i] - joint_pos[i-1]) / dt`
- `body_lin_vel[i] = (body_pos[i] - body_pos[i-1]) / dt`
- `body_ang_vel[i] ≈ 2 * (quat[i] - quat[i-1])[:3] / dt` (simplified quaternion derivative)

First frame velocities are copied from second frame to avoid zero initialization.

### Training Termination Threshold
The distance threshold determines when episodes terminate early:
- Previous experiments used 0.50m, 0.75m, 1.00m with template-based data (poor results)
- Current approach uses 0.25m with properly computed body states
- Threshold affects both training stability and final policy quality

### PPO Hyperparameters
Key parameters from `whole_body_tracking/tasks/tracking/config/g1/agents/rsl_rl_ppo_cfg.py`:
- 4096 parallel environments
- Learning rate: 5e-4 (both policy and critic)
- Clip range: 0.2
- Network: [512, 256, 128] with ELU activation
- Batch size: 40,960 (4096 envs × 10 steps)

## Repository Structure Context

```
BeyondMimic-Dance-Project/          # Local documentation/tracking repo
├── converter/
│   └── gmr_pkl_to_beyondmimic_npz.py    # Upload to server scripts/
├── docs/                                 # Technical documentation
├── experiments/                          # Parameter logs
└── reports/                              # Experiment analysis
```

This is a **documentation repository** on your local Mac. The actual codebase lives on the remote server at `/data/home/xgj/projects/BeyondMimic/` which is the BeyondMimic framework (not tracked in this repo).

## Key Files and Their Roles

### converter/gmr_pkl_to_beyondmimic_npz.py
The core converter script. Key characteristics:
- Adapted from `replay_go2_npz.py` (quadruped) for G1 (humanoid)
- Imports `G1_CYLINDER_CFG` from `whole_body_tracking.robots.g1`
- Uses Isaac Sim's `AppLauncher` initialization pattern
- Frame-by-frame simulation: sets robot state, renders, captures body data
- Must run on server (requires Isaac Sim installation)

### docs/GMR_vs_BeyondMimic_Format_Comparison.md
661-line technical analysis of format differences. Reference this when:
- Understanding why conversion is necessary
- Debugging format mismatches
- Explaining to others why simple resampling doesn't work

### experiments/training_parameters.md
Complete parameter documentation including:
- Hardware specs (8× RTX 4090)
- All PPO hyperparameters
- Reward function weights
- Observation/action space definitions

Reference this when tuning training or debugging convergence issues.

## Common Issues and Solutions

### Isaac Sim Hangs During Conversion
- Symptom: Script freezes after "Launching Isaac Sim"
- Solution: `pkill -f isaac` then retry, or use `export CUDA_VISIBLE_DEVICES=0` for single GPU

### Wrong Motion Reference in Training
- Training config points to motion file by name
- After converting, update config to use new `_CONVERTED` motion name
- Config location: `whole_body_tracking/tasks/tracking/config/g1/flat_env_cfg.py`

### Episode Terminates Immediately
- Check if body states are NaN or extremely large values
- Verify Z-offset was applied during conversion
- Verify motion NPZ has all 7 required arrays with correct shapes

### Training Doesn't Improve
- Previous issue: template-based conversion led to inaccurate body states
- Ensure using `_CONVERTED` motion (not `_FINAL` which was template-based)
- Check WandB for tracking errors - high `error_body_pos` indicates data problem

## Development Patterns

### Adding New Dance Motions
1. Obtain GMR PKL output (29 DoF, 30 FPS recommended)
2. Upload to server `motions/` directory
3. Run converter with appropriate z_offset
4. Update training config if motion duration differs significantly
5. Start new training run with descriptive `--run_name`

### Comparing Training Runs
All runs logged to WandB under `robot_dance_episode_length` project. Key metrics:
- `Metrics/motion/error_body_pos` - Primary tracking error
- `Episode_lengths/mean` - How long episodes last (higher = better tracking)
- `Rewards/total` - Overall policy performance

### Modifying Converter
The converter follows this pattern:
1. `load_gmr_data()` - Load PKL and apply transformations
2. `convert_gmr_to_beyondmimic()` - Main loop
   - Set robot state from GMR frame
   - Call `sim.render()` to compute FK
   - Capture `robot.data.body_*_w` arrays
3. Compute velocities via finite differences
4. Save to NPZ with `np.savez()`

Maintain this structure when adding features like smoothing or interpolation.

## WandB Monitoring

Active project: https://wandb.ai/violetxu219/robot_dance_episode_length

When training is running, monitor:
- Real-time episode lengths (should stay near motion duration if tracking well)
- Tracking errors per body part
- Termination reasons (helps identify if threshold too strict)

## Git Workflow

This repo uses standard git workflow. When updating:
```bash
cd ~/Desktop/BeyondMimic-Dance-Project
git add .
git commit -m "Descriptive message"
git push
```

Large files (*.pkl, *.npz, *.pt) are gitignored. Results stay on remote server.
