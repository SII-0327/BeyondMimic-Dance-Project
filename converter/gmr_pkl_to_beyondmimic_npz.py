#!/usr/bin/env python3
"""
Convert GMR PKL format directly to BeyondMimic NPZ format using Isaac Sim.
This script computes full body states and velocities by simulating the motion.

Adapted from replay_go2_npz.py for G1 humanoid robot.

Usage:
    python gmr_pkl_to_beyondmimic_npz.py \
        --input outputs/dance_1_g1_15s.pkl \
        --output dance_1_g1_15s_FINAL \
        --z_offset -0.15 \
        --headless
"""

import argparse
import pickle
import numpy as np
import torch
import os

from isaaclab.app import AppLauncher

# Add argparse arguments
parser = argparse.ArgumentParser(description="Convert GMR PKL to BeyondMimic NPZ with full body states")
parser.add_argument("--input", type=str, required=True, help="Input GMR pickle file")
parser.add_argument("--output", type=str, required=True, help="Output name (will create artifacts/OUTPUT:v0/motion.npz)")
parser.add_argument("--z_offset", type=float, default=0.0, help="Z-axis offset to adjust height (e.g., -0.15)")
parser.add_argument("--fps", type=int, default=None, help="Override FPS (default: use FPS from PKL)")

# Append AppLauncher CLI args
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

# Launch Isaac Sim
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, ArticulationCfg, AssetBaseCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationContext
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

# Import G1 robot configuration
from whole_body_tracking.robots.g1 import G1_CYLINDER_CFG


@configclass
class ConversionSceneCfg(InteractiveSceneCfg):
    """Configuration for GMR to BeyondMimic conversion scene."""

    ground = AssetBaseCfg(prim_path="/World/defaultGroundPlane", spawn=sim_utils.GroundPlaneCfg())

    sky_light = AssetBaseCfg(
        prim_path="/World/skyLight",
        spawn=sim_utils.DomeLightCfg(
            intensity=750.0,
            texture_file=f"{ISAAC_NUCLEUS_DIR}/Materials/Textures/Skies/PolyHaven/kloofendal_43d_clear_puresky_4k.hdr",
        ),
    )

    # G1 humanoid robot
    robot: ArticulationCfg = G1_CYLINDER_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")


def load_gmr_data(pkl_path: str, z_offset: float = 0.0):
    """
    Load GMR pickle file and apply Z-offset if needed.

    Returns:
        dict with keys: fps, root_pos, root_rot, dof_pos
    """
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f)

    print(f"\n=== Loading GMR Data ===")
    print(f"Input file: {pkl_path}")
    print(f"Frames: {data['root_pos'].shape[0]}")
    print(f"FPS: {data['fps']}")
    print(f"DoF: {data['dof_pos'].shape[1]}")

    # Apply Z-offset to root position
    if z_offset != 0.0:
        data['root_pos'] = data['root_pos'].copy()
        data['root_pos'][:, 2] += z_offset
        print(f"Applied Z-offset: {z_offset}m")
        print(f"  New Z range: [{data['root_pos'][:, 2].min():.3f}, {data['root_pos'][:, 2].max():.3f}]")

    return data


def convert_gmr_to_beyondmimic(sim: sim_utils.SimulationContext, scene: InteractiveScene, gmr_data: dict, output_name: str):
    """
    Convert GMR motion to BeyondMimic format by simulating and capturing body states.
    """
    robot: Articulation = scene["robot"]
    sim_dt = sim.get_physics_dt()

    # Extract GMR data
    root_pos = gmr_data['root_pos']      # (N, 3)
    root_rot = gmr_data['root_rot']      # (N, 4) - xyzw quaternion
    dof_pos = gmr_data['dof_pos']        # (N, 29)
    fps = gmr_data['fps']
    num_frames = root_pos.shape[0]

    print(f"\n=== Converting Motion ===")
    print(f"Robot: G1 Humanoid")
    print(f"Bodies: {len(robot.data.body_names)}")
    print(f"Body names: {robot.data.body_names}")
    print(f"Joint names: {robot.data.joint_names}")
    print(f"Processing {num_frames} frames at {fps} FPS...")

    # Convert NumPy to PyTorch tensors
    root_pos_torch = torch.from_numpy(root_pos).float().to(sim.device)
    root_rot_torch = torch.from_numpy(root_rot).float().to(sim.device)
    dof_pos_torch = torch.from_numpy(dof_pos).float().to(sim.device)

    # Storage for captured body states
    recorded_body_pos = []
    recorded_body_quat = []
    recorded_body_lin_vel = []
    recorded_body_ang_vel = []
    recorded_joint_pos = []
    recorded_joint_vel = []

    # Simulation loop - replay and capture
    for frame_idx in range(num_frames):
        # Set robot state from GMR data
        root_states = robot.data.default_root_state.clone()

        # Set root position (add environment origin)
        root_states[:, :3] = root_pos_torch[frame_idx:frame_idx+1] + scene.env_origins[:, :]

        # Set root orientation (quaternion xyzw)
        root_states[:, 3:7] = root_rot_torch[frame_idx:frame_idx+1]

        # Set root velocities to zero initially
        # (will be computed from position differences later)
        root_states[:, 7:10] = 0.0  # linear velocity
        root_states[:, 10:] = 0.0   # angular velocity

        # Write root state to simulation
        robot.write_root_state_to_sim(root_states)

        # Set joint positions from GMR
        joint_pos = dof_pos_torch[frame_idx:frame_idx+1]
        joint_vel = torch.zeros_like(joint_pos)  # Initially zero, will compute later
        robot.write_joint_state_to_sim(joint_pos, joint_vel)

        # Update simulation (render without physics step)
        scene.write_data_to_sim()
        sim.render()
        scene.update(sim_dt)

        # **Capture body states from simulation**
        # Isaac Sim has computed all body positions via forward kinematics
        current_body_pos = robot.data.body_pos_w[0].clone().cpu().numpy()       # (num_bodies, 3)
        current_body_quat = robot.data.body_quat_w[0].clone().cpu().numpy()     # (num_bodies, 4)
        current_body_lin_vel = robot.data.body_lin_vel_w[0].clone().cpu().numpy()   # (num_bodies, 3)
        current_body_ang_vel = robot.data.body_ang_vel_w[0].clone().cpu().numpy()   # (num_bodies, 3)

        # Record this frame
        recorded_body_pos.append(current_body_pos)
        recorded_body_quat.append(current_body_quat)
        recorded_body_lin_vel.append(current_body_lin_vel)
        recorded_body_ang_vel.append(current_body_ang_vel)
        recorded_joint_pos.append(joint_pos[0].cpu().numpy())
        recorded_joint_vel.append(joint_vel[0].cpu().numpy())

        # Progress
        if frame_idx % 30 == 0:
            print(f"  Frame {frame_idx}/{num_frames} ({frame_idx/num_frames*100:.1f}%)")

    print(f"  Captured all {num_frames} frames ✓")

    # Convert lists to NumPy arrays
    body_pos_w = np.array(recorded_body_pos)          # (N, num_bodies, 3)
    body_quat_w = np.array(recorded_body_quat)        # (N, num_bodies, 4)
    body_lin_vel_w = np.array(recorded_body_lin_vel)  # (N, num_bodies, 3)
    body_ang_vel_w = np.array(recorded_body_ang_vel)  # (N, num_bodies, 3)
    joint_pos_arr = np.array(recorded_joint_pos)      # (N, 29)
    joint_vel_arr = np.array(recorded_joint_vel)      # (N, 29)

    # **Compute velocities from position differences**
    print("\n=== Computing Velocities ===")
    dt = 1.0 / fps

    # Joint velocities
    joint_vel_arr[1:] = (joint_pos_arr[1:] - joint_pos_arr[:-1]) / dt
    joint_vel_arr[0] = joint_vel_arr[1]  # Copy first frame

    # Body linear velocities
    body_lin_vel_w[1:] = (body_pos_w[1:] - body_pos_w[:-1]) / dt
    body_lin_vel_w[0] = body_lin_vel_w[1]

    # Body angular velocities (simplified finite difference)
    # For proper quaternion derivative, would need more complex computation
    # Here we use a simple approximation
    for i in range(1, num_frames):
        for b in range(body_quat_w.shape[1]):
            q0 = body_quat_w[i-1, b]
            q1 = body_quat_w[i, b]
            # Approximate angular velocity
            dq = q1 - q0
            body_ang_vel_w[i, b] = 2 * dq[:3] / dt  # Simplified, not exact
    body_ang_vel_w[0] = body_ang_vel_w[1]

    print(f"  Joint velocities computed ✓")
    print(f"  Body velocities computed ✓")

    # **Save to NPZ in BeyondMimic format**
    output_dir = f"artifacts/{output_name}:v0"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "motion.npz")

    np.savez(
        output_path,
        fps=fps,
        joint_pos=joint_pos_arr.astype(np.float32),
        joint_vel=joint_vel_arr.astype(np.float32),
        body_pos_w=body_pos_w.astype(np.float32),
        body_quat_w=body_quat_w.astype(np.float32),
        body_lin_vel_w=body_lin_vel_w.astype(np.float32),
        body_ang_vel_w=body_ang_vel_w.astype(np.float32),
        # Optional metadata
        body_names=np.array(robot.data.body_names),
        joint_names=np.array(robot.data.joint_names)
    )

    print(f"\n=== Conversion Complete ===")
    print(f"Output saved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")
    print(f"\nNPZ contents:")
    print(f"  fps: {fps}")
    print(f"  joint_pos: {joint_pos_arr.shape}")
    print(f"  joint_vel: {joint_vel_arr.shape}")
    print(f"  body_pos_w: {body_pos_w.shape}")
    print(f"  body_quat_w: {body_quat_w.shape}")
    print(f"  body_lin_vel_w: {body_lin_vel_w.shape}")
    print(f"  body_ang_vel_w: {body_ang_vel_w.shape}")
    print(f"\n✅ Ready for BeyondMimic training!")


def main():
    # Load GMR data
    gmr_data = load_gmr_data(args_cli.input, args_cli.z_offset)

    # Override FPS if specified
    if args_cli.fps is not None:
        gmr_data['fps'] = args_cli.fps
        print(f"Overriding FPS to: {args_cli.fps}")

    # Setup Isaac Sim
    sim_cfg = sim_utils.SimulationCfg(device=args_cli.device)
    sim_cfg.dt = 1.0 / gmr_data['fps']  # Match motion FPS
    sim = SimulationContext(sim_cfg)

    # Create scene with G1 robot
    scene_cfg = ConversionSceneCfg(num_envs=1, env_spacing=2.0)
    scene = InteractiveScene(scene_cfg)
    sim.reset()

    # Convert motion
    convert_gmr_to_beyondmimic(sim, scene, gmr_data, args_cli.output)


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
