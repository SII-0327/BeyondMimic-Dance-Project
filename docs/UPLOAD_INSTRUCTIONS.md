# Upload Instructions for GMR to BeyondMimic Converter

## Files Created on Your Local PC

All files are in: `/Users/guangjunxu/Desktop/1. dance robots/`

### 1. **gmr_pkl_to_beyondmimic_npz.py** (Main Converter)
- Direct PKL → NPZ converter using Isaac Sim
- Based on replay_go2_npz.py method
- Computes all body states and velocities

### 2. **GMR_to_BeyondMimic_Converter_README.md** (Usage Guide)
- Complete documentation
- Usage examples
- Technical details

### 3. **GMR_vs_BeyondMimic_Format_Comparison.md** (Format Analysis)
- Detailed format comparison
- Data flow diagrams
- Conversion pipeline explanation

---

## How to Upload to Remote Server

### Option 1: Manual SCP (Recommended)
```bash
# From your Mac terminal
cd "/Users/guangjunxu/Desktop/1. dance robots"

# Upload the converter script
scp gmr_pkl_to_beyondmimic_npz.py xgj@10.13.238.34:~/projects/BeyondMimic/scripts/

# Upload documentation (optional)
scp GMR_to_BeyondMimic_Converter_README.md xgj@10.13.238.34:~/projects/BeyondMimic/docs/
scp GMR_vs_BeyondMimic_Format_Comparison.md xgj@10.13.238.34:~/projects/BeyondMimic/docs/
```

### Option 2: Using File Transfer App
1. Open any SFTP client (Cyberduck, FileZilla, etc.)
2. Connect to: `10.13.238.34`
3. Username: `xgj`
4. Navigate to: `/data/home/xgj/projects/BeyondMimic/scripts/`
5. Upload: `gmr_pkl_to_beyondmimic_npz.py`

---

## How to Use After Upload

### Step 1: SSH to Remote Server
```bash
ssh xgj@10.13.238.34
```

### Step 2: Prepare Environment
```bash
cd ~/projects/BeyondMimic
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab
export OMNI_KIT_ACCEPT_EULA=YES
```

### Step 3: Upload Your GMR PKL File (if not already there)
```bash
# From your Mac (in another terminal)
scp "/Users/guangjunxu/Desktop/1. dance robots/GMR/outputs/dance_1_g1_15s.pkl" \
    xgj@10.13.238.34:~/projects/BeyondMimic/motions/
```

### Step 4: Run Converter
```bash
python scripts/gmr_pkl_to_beyondmimic_npz.py \
  --input motions/dance_1_g1_15s.pkl \
  --output dance_1_g1_15s_FINAL \
  --z_offset -0.15 \
  --headless
```

### Step 5: Verify Output
```bash
# Check if NPZ was created
ls -lh artifacts/dance_1_g1_15s_FINAL:v0/motion.npz

# Load and inspect
python -c "
import numpy as np
data = np.load('artifacts/dance_1_g1_15s_FINAL:v0/motion.npz')
print('Keys:', list(data.keys()))
print('Shapes:')
for k in data.keys():
    if hasattr(data[k], 'shape'):
        print(f'  {k}: {data[k].shape}')
"
```

---

## Expected Output

```
=== Loading GMR Data ===
Input file: motions/dance_1_g1_15s.pkl
Frames: 450
FPS: 30
DoF: 29
Applied Z-offset: -0.15m
  New Z range: [0.713, 1.007]

=== Converting Motion ===
Robot: G1 Humanoid
Bodies: 30
Processing 450 frames at 30 FPS...
  Frame 0/450 (0.0%)
  Frame 30/450 (6.7%)
  ...
  Frame 450/450 (100.0%)
  Captured all 450 frames ✓

=== Computing Velocities ===
  Joint velocities computed ✓
  Body velocities computed ✓

=== Conversion Complete ===
Output saved to: artifacts/dance_1_g1_15s_FINAL:v0/motion.npz
File size: 790.2 KB

NPZ contents:
  fps: 30
  joint_pos: (450, 29)
  joint_vel: (450, 29)
  body_pos_w: (450, 30, 3)
  body_quat_w: (450, 30, 4)
  body_lin_vel_w: (450, 30, 3)
  body_ang_vel_w: (450, 30, 3)

✅ Ready for BeyondMimic training!
```

---

## What This Achieves

### Before (Old Method)
```
GMR PKL → CSV (manual) → csv_to_npz.py (HANGS) → Template workaround → NPZ
```

### After (New Method)
```
GMR PKL → gmr_pkl_to_beyondmimic_npz.py → NPZ ✓
```

### Key Improvements
1. ✅ **One-step conversion** (no intermediate CSV)
2. ✅ **Proper forward kinematics** (all 30 bodies computed)
3. ✅ **Accurate velocities** (from position differences)
4. ✅ **No hanging** (proven method from replay_go2.py)
5. ✅ **Z-offset support** (built-in height adjustment)

---

## Troubleshooting

### If Isaac Sim Hangs
1. Kill stuck processes: `pkill -f isaac`
2. Use single GPU: `export CUDA_VISIBLE_DEVICES=0`
3. Check GPU: `nvidia-smi`

### If Conversion Fails
1. Verify PKL file exists and is valid
2. Check conda environment is activated
3. Ensure EULA is accepted
4. Try with `--device cpu` for debugging

### If Output NPZ is Wrong Size
- Should be ~790 KB for 450 frames
- Much smaller = incomplete data
- Check for errors in console output

---

## Next Steps After Conversion

### 1. Train with New NPZ
```bash
# Update config if needed (thresholds already set)
python scripts/rsl_rl/train.py \
  --task=Tracking-Flat-G1-v0 \
  --headless \
  --max_iterations=10000 \
  --run_name=dance_15s_proper_npz \
  --logger wandb \
  --log_project_name robot_dance
```

### 2. Compare with Old Method
Check if episode lengths improve with proper body states

### 3. Visualize Motion
```bash
python scripts/replay_npz.py \
  --motion_file artifacts/dance_1_g1_15s_FINAL:v0/motion.npz
```

---

## Summary

You now have:
- ✅ **Direct PKL→NPZ converter** (gmr_pkl_to_beyondmimic_npz.py)
- ✅ **Complete documentation** (2 markdown files)
- ✅ **Upload instructions** (this file)

**Ready to synchronize GMR output with BeyondMimic input format!** 🤖✨

---

**Created:** 2026-01-07
**Files Location:** `/Users/guangjunxu/Desktop/1. dance robots/`
