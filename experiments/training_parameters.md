# Training Parameters Summary

## Hardware Configuration

**Remote Server:** 10.13.238.34
**GPUs:** 8× NVIDIA GeForce RTX 4090 (24GB each)
**CPU:** Intel Xeon Platinum 8368Q @ 2.60GHz (152 logical cores)
**RAM:** 515 GB
**OS:** Ubuntu 22.04.5 LTS

## Software Environment

**Framework:** Isaac Lab 4.5
**Simulation:** Isaac Sim 4.5 (NVIDIA Omniverse)
**RL Library:** RSL-RL (Robotic Systems Lab - RL)
**Logging:** Weights & Biases (WandB)
**Python:** 3.10
**Conda Environment:** isaaclab

## Robot Configuration

**Model:** Unitree G1 Humanoid
**URDF:** `/data/home/xgj/projects/BeyondMimic/source/whole_body_tracking/whole_body_tracking/assets/unitree_description/urdf/g1/main.urdf`

**Specifications:**
- Total Bodies: 30
- Total Joints: 29 DoF
- Root Link: pelvis
- Control Mode: Position control

**Body List:**
```
0:  pelvis (root)
1:  left_hip_pitch_link
2:  right_hip_pitch_link
3:  waist_yaw_link
4:  left_hip_roll_link
5:  right_hip_roll_link
6:  waist_roll_link
7:  left_hip_yaw_link
8:  right_hip_yaw_link
9:  torso_link
10: left_knee_link
11: right_knee_link
12: left_shoulder_pitch_link
13: right_shoulder_pitch_link
14: left_ankle_pitch_link
15: right_ankle_pitch_link
16: left_shoulder_roll_link
17: right_shoulder_roll_link
18: left_ankle_roll_link
19: right_ankle_roll_link
20: left_shoulder_yaw_link
21: right_shoulder_yaw_link
22: left_elbow_link
23: right_elbow_link
24: left_wrist_roll_link
25: right_wrist_roll_link
26: left_wrist_pitch_link
27: right_wrist_pitch_link
28: left_wrist_yaw_link
29: right_wrist_yaw_link
```

**Actuator Configuration:**

| Group | Joints | Effort Limit | Velocity Limit | Stiffness | Damping |
|-------|--------|--------------|----------------|-----------|---------|
| Legs | hip_yaw, hip_roll, hip_pitch, knee | 88N / 160N | 32 rad/s / 20 rad/s | 40 | 2 |
| Feet | ankle_pitch, ankle_roll | 73N | 50 rad/s | 20 | 1 |
| Waist | waist_roll, waist_pitch | 50N | 50 rad/s | 20 | 1 |
| Waist Yaw | waist_yaw | 88N | 32 rad/s | 40 | 2 |
| Arms | shoulder, elbow, wrist | 25N | 50 rad/s | 12 | 1 |

## Motion Data

**Source:** GMR (General Motion Retargeting)
**Motion File:** dance_1_g1_15s.pkl
**Converted File:** dance_1_g1_15s_CONVERTED:v0/motion.npz

**Motion Properties:**
- Duration: 15 seconds
- Frame Rate: 30 FPS
- Total Frames: 450
- DoF: 29 joints
- Z-offset: -0.15m (for foot grounding)

**NPZ Arrays:**
```
fps: 30
joint_pos: (450, 29)           # Joint positions
joint_vel: (450, 29)           # Joint velocities
body_pos_w: (450, 30, 3)       # Body positions (world frame)
body_quat_w: (450, 30, 4)      # Body orientations (quaternions)
body_lin_vel_w: (450, 30, 3)   # Body linear velocities
body_ang_vel_w: (450, 30, 3)   # Body angular velocities
```

## Training Hyperparameters

### Environment Parameters

```yaml
Task: Tracking-Flat-G1-v0
Num Environments: 4096
Environment Spacing: 2.5m
Decimation: 2 (control freq = sim_freq / 2)
Sim dt: 0.005s
Episode Length: Variable (motion-dependent)
```

### PPO Algorithm Parameters

**From:** `whole_body_tracking/tasks/tracking/config/g1/agents/rsl_rl_ppo_cfg.py`

```yaml
# Policy Network
Policy Architecture: [512, 256, 128]
Activation: ELU
Initialization: Orthogonal

# Value Network
Critic Architecture: [512, 256, 128]
Activation: ELU
Initialization: Orthogonal

# Training
Max Iterations: 10,000
Batch Size: 40,960 (4096 envs × 10 steps)
Num Mini-batches: 8
Learning Rate (policy): 5e-4
Learning Rate (critic): 5e-4
Discount Factor (γ): 0.99
GAE Lambda (λ): 0.95
Clip Range (ε): 0.2
Value Function Clip Range: 0.2
Entropy Coefficient: 0.01
Max Grad Norm: 1.0

# PPO Specific
Num Learning Epochs: 5
Surrogate Loss: Clipped
Value Loss: MSE
Use Clipped Value Loss: True
```

### Observation Space

**Policy Observations:**
- Base linear velocity (3D)
- Base angular velocity (3D)
- Projected gravity (3D)
- Joint positions (29D)
- Joint velocities (29D)
- Previous actions (29D)
- Motion anchor position in base frame (3D)
- Motion body positions (14 bodies × 3D)
- Motion body rotations (14 bodies × 6D, rotation 6D repr)

**Total Dimension:** Variable based on observation config

### Action Space

**Type:** Continuous
**Dimension:** 29 (one per joint)
**Range:** [-1, 1] (scaled by action scale)
**Action Scale:** G1-specific per-joint scaling

### Reward Function

**Components:**

| Reward Term | Weight | Description |
|-------------|--------|-------------|
| tracking_motion_anchor_pos | 100.0 | Track anchor body position |
| tracking_motion_anchor_rot | 10.0 | Track anchor body rotation |
| tracking_motion_anchor_lin_vel | 1.0 | Track anchor linear velocity |
| tracking_motion_anchor_ang_vel | 0.1 | Track anchor angular velocity |
| tracking_motion_joint_pos | 10.0 | Track joint positions |
| tracking_motion_joint_vel | 0.1 | Track joint velocities |
| tracking_motion_body_pos | 10.0 | Track body positions |
| tracking_motion_body_rot | 1.0 | Track body rotations |
| action_rate_l2 | -0.01 | Penalize action changes |
| joint_torques_l2 | -0.0001 | Penalize high torques |
| joint_accel_l2 | -0.00025 | Penalize joint accelerations |

**Total Reward:** Weighted sum of all components

### Termination Conditions

```yaml
# Distance-based termination
distance_threshold: 0.25m  # NEW: Using proper body states

# Termination conditions:
1. anchor_pos: |position - target| > threshold
2. anchor_ori: |orientation - target| > threshold
3. ee_body_pos: End-effector position error > threshold
4. time_out: Episode exceeds max length
```

## Experiment Configurations

### Previous Experiments (Template Method)

**Date:** January 6-7, 2026

#### Experiment 1
```yaml
Name: dance_15s_thresh_050
Threshold: 0.50m
Motion: dance_1_g1_15s_FINAL (template-based)
Status: Completed (10,000 iterations)
Duration: 11.4 hours
Models Saved: 21 checkpoints
```

#### Experiment 2
```yaml
Name: dance_15s_thresh_075
Threshold: 0.75m
Motion: dance_1_g1_15s_FINAL (template-based)
Status: Completed (10,000 iterations)
Duration: 11.4 hours
Models Saved: 21 checkpoints
```

#### Experiment 3
```yaml
Name: dance_15s_thresh_100
Threshold: 1.00m
Motion: dance_1_g1_15s_FINAL (template-based)
Status: Completed (10,000 iterations)
Duration: 10.6 hours
Models Saved: 21 checkpoints
```

### Current Experiment (Forward Kinematics Method)

**Date:** January 12, 2026

```yaml
Name: dance_15s_CONVERTED_thresh_025
Threshold: 0.25m
Motion: dance_1_g1_15s_CONVERTED (forward kinematics)
Status: Running
Start Time: 2026-01-12 10:54:08
Expected Duration: ~6-7 hours
Expected Completion: 2026-01-12 17:30
Max Iterations: 10,000
WandB Run: unftugpz
WandB Link: https://wandb.ai/violetxu219/robot_dance_episode_length/runs/unftugpz
```

**Key Difference:** Using properly computed body states from Isaac Sim forward kinematics instead of template-based approximation.

## Logging Configuration

**Logger:** Weights & Biases (WandB)
**User:** violetxu219
**Project:** robot_dance_episode_length
**Entity:** violetxu219

**Logged Metrics:**
- Episode rewards
- Episode lengths
- Motion tracking errors (per body part)
- Termination reasons
- Policy loss
- Value loss
- Learning rate
- Entropy
- KL divergence

**Logging Frequency:**
- Training metrics: Every iteration
- Video recording: Every 2000 steps (optional)
- Model checkpoints: Every 500 iterations

## Command Reference

### Training Command
```bash
python scripts/rsl_rl/train.py \
  --task=Tracking-Flat-G1-v0 \
  --headless \
  --max_iterations=10000 \
  --run_name=dance_15s_CONVERTED_thresh_025 \
  --logger wandb \
  --log_project_name robot_dance_episode_length
```

### Replay Command
```bash
python scripts/rsl_rl/play.py \
  --task=Tracking-Flat-G1-v0 \
  --num_envs=1 \
  --checkpoint=/path/to/model.pt
```

### Converter Command
```bash
python scripts/gmr_pkl_to_beyondmimic_npz.py \
  --input motions/dance_1_g1_15s.pkl \
  --output dance_1_g1_15s_CONVERTED \
  --z_offset -0.15 \
  --headless
```

## Performance Metrics

### Computational Performance

**Training Speed:**
- Iteration Time: ~2.23s per iteration
- Timesteps per Second: ~18,370 (4096 envs × 10 steps / 2.23s)
- GPU Utilization: ~80-90% (distributed across 8 GPUs)
- Memory Usage: ~20GB per GPU

**Expected Training Time:**
- 10,000 iterations × 2.23s = 22,300s ≈ 6.2 hours

### Conversion Performance

**GMR PKL → BeyondMimic NPZ:**
- Initialization: 1-2 minutes (Isaac Sim startup)
- Processing: 30-60 FPS
- Total Time (450 frames): 2-3 minutes
- Input Size: 127 KB
- Output Size: 796 KB

---

**Last Updated:** January 12, 2026
**Configuration Status:** Active - Training in progress
