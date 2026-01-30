#!/bin/bash
export LD_LIBRARY_PATH="/mnt/sda/anaconda3/envs/auto-gpt/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"
cd /mnt/sda/worker/dev_ldm/iosys-generative/itembank-api
exec uvicorn api.main:app --host 0.0.0.0 --port 8010
