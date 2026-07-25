#!/usr/bin/env bash
# Naive agent: du + ls per subdir. Realistic average-agent tool response.
set -euo pipefail
cd "$(dirname "$0")"
du -ah input/ | sort -rh | head -50
echo "---"
find input -type f -printf '%s %p\n' | sort -rn | head -20
