#!/bin/bash
# utils/train_vits.slurm
#
# Slurm submission script for running HAUSA AI VITS training on a university HPC cluster.
# Submit with: sbatch utils/train_vits.slurm

#SBATCH --job-name=hausa_vits_training     # Job name
#SBATCH --output=hausa_vits_%j.out         # Standard output log (%j inserts job ID)
#SBATCH --error=hausa_vits_%j.err          # Standard error log
#SBATCH --partition=gpu                    # Request GPU partition (change to your cluster's partition name)
#SBATCH --gres=gpu:1                       # Request 1 GPU (typically T4, L4, V100, or A100)
#SBATCH --cpus-per-task=4                  # Request 4 CPU cores for DataLoader workers
#SBATCH --mem=32G                          # Request 32 GB RAM
#SBATCH --time=48:00:00                    # Set max walltime to 48 hours

echo "=== HPC Job Started: $(date) ==="
echo "Node: $SLURM_NODENAME"
echo "GPUs allocated: $CUDA_VISIBLE_DEVICES"

# 1. Load CUDA module (change version to match your cluster's CUDA installation)
echo "Loading CUDA and environment modules..."
module load cuda/12.1 || module load cuda || echo "No module command or CUDA module found. Assumes global installation."

# 2. Activate Python Virtual Environment
echo "Activating virtual environment..."
source venv/bin/activate

# 3. Start training
echo "Starting VITS training..."
python utils/train_vits_gcp.py

echo "=== HPC Job Completed: $(date) ==="
