#!/usr/bin/env bash
# Cập nhật dữ liệu hằng ngày (macOS/Linux). Lên lịch bằng cron, ví dụ 07:05 giờ VN:
#   5 7 * * * /đường/dẫn/crypto-regime-radar/scripts/update_daily.sh
cd "$(dirname "$0")/.." || exit 1
set -euo pipefail
source "${VIRTUAL_ENV:-$HOME/.venv}/bin/activate"
{
  echo "===== $(date) ====="
  python scripts/complete_research.py --download --rebuild-core
} >> outputs/metadata/update_log.txt 2>&1
