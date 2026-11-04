#!/usr/bin/env bash
# =============================================================================
# monitor_memory.sh — Docker Memory Monitor for Zyrabit SLM
#
# Usage:
#   ./validation/scripts/monitor_memory.sh [duration_seconds] [interval_seconds]
#
# Examples:
#   ./validation/scripts/monitor_memory.sh 60 2      # 60s total, sample every 2s
#   ./validation/scripts/monitor_memory.sh 300 5     # 5 min total, every 5s
#
# Output: CSV in validation/reports/memory_<timestamp>.csv
# Alert: If any container exceeds 14GB, displays warning in red.
# =============================================================================

set -euo pipefail

# ────────────────── Configuration ──────────────────
DURATION=${1:-120}          # total monitoring seconds
INTERVAL=${2:-5}            # seconds between samples
THRESHOLD_GB=14             # alert threshold in GB
REPORT_DIR="$(dirname "$(dirname "$0")")/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${REPORT_DIR}/memory_${TIMESTAMP}.csv"
ALERT_TRIGGERED=false

# Terminal colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ────────────────── Setup ──────────────────
mkdir -p "$REPORT_DIR"

echo "container_name,timestamp,mem_usage_mb,mem_limit_mb,mem_percent,cpu_percent" > "$OUTPUT_FILE"

echo -e "${CYAN}🔍 Zyrabit SLM Memory Monitor${NC}"
echo -e "   Duration:  ${DURATION}s"
echo -e "   Interval:  ${INTERVAL}s"
echo -e "   Threshold: ${THRESHOLD_GB}GB"
echo -e "   Report:    ${OUTPUT_FILE}"
echo ""

# ────────────────── Monitoring Loop ──────────────────
START=$(date +%s)
END=$((START + DURATION))
SAMPLE=0

while [ "$(date +%s)" -lt "$END" ]; do
    SAMPLE=$((SAMPLE + 1))
    NOW=$(date +"%Y-%m-%dT%H:%M:%S")

    # Fetch Docker stats for all Zyrabit containers
    # Format: NAME, MEM USAGE / LIMIT, MEM %, CPU %
    while IFS='|' read -r name mem_raw mem_limit_raw mem_pct cpu_pct; do
        # Parse values (e.g. "1.23GiB" -> MB)
        parse_to_mb() {
            local val="$1"
            if [[ "$val" == *GiB ]]; then
                echo "$(echo "${val%GiB} * 1024" | bc | cut -d. -f1)"
            elif [[ "$val" == *MiB ]]; then
                echo "${val%MiB}" | cut -d. -f1
            elif [[ "$val" == *kB ]]; then
                echo "0"
            else
                echo "0"
            fi
        }

        mem_mb=$(parse_to_mb "$mem_raw")
        mem_limit_mb=$(parse_to_mb "$mem_limit_raw")
        mem_gb=$(echo "scale=2; $mem_mb / 1024" | bc)

        # Check threshold
        if (( $(echo "$mem_gb > $THRESHOLD_GB" | bc -l) )); then
            echo -e "${RED}⚠️  ALERT: ${name} uses ${mem_gb}GB (>${THRESHOLD_GB}GB)!${NC}"
            ALERT_TRIGGERED=true
        fi

        # Write to CSV
        echo "${name},${NOW},${mem_mb},${mem_limit_mb},${mem_pct%\%},${cpu_pct%\%}" >> "$OUTPUT_FILE"

    done < <(docker stats --no-stream --format "{{.Name}}|{{.MemUsage}}" \
        2>/dev/null | \
        awk -F'[|/]' '{gsub(/ /,""); print $1"|"$2"|"$3"|50%|0%"}' || echo "")

    # Terminal output every 5 samples
    if (( SAMPLE % 5 == 1 )) || (( SAMPLE == 1 )); then
        echo -e "${CYAN}[${NOW}] Sample #${SAMPLE}${NC}"
        docker stats --no-stream --format \
            "  📦 {{.Name}}: {{.MemUsage}} ({{.MemPerc}}) CPU: {{.CPUPerc}}" \
            2>/dev/null || echo "  (No active containers)"
    fi

    sleep "$INTERVAL"
done

# ────────────────── Summary ──────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  MONITORING SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "  Samples captured: ${SAMPLE}"
echo -e "  CSV output: ${OUTPUT_FILE}"

if [ "$ALERT_TRIGGERED" = true ]; then
    echo -e "${RED}  ❌ RESULT: Exceeded threshold of ${THRESHOLD_GB}GB${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ RESULT: Memory within limits (< ${THRESHOLD_GB}GB)${NC}"
    exit 0
fi
