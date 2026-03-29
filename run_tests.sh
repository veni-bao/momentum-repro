# Momentum Reproduction - Test Scripts
# Run this from project root

# Step 1: Setup environment with uv
echo [1/3] Setting up environment with uv...
uv sync

# Step 2: Run mock data test
echo [2/3] Running mock data test...
python -m data.mock.test_run

# Step 3: Run full pipeline test
echo [3/3] Running full pipeline...
python -m src.factors.test_pipeline

echo Done!