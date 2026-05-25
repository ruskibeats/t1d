#!/bin/bash
# Full verbose pipeline runner - streams all output unfiltered

cd /root/t1d/sim_user_insights || exit 1

# Run pipeline with verbose flag, pass all arguments
python3 scripts/companion_pipeline_v2.py "$@" --verbose