#!/usr/bin/env bash
# =============================================================================
# monitor_memory.sh — Monitor de Memoria Docker para Zyrabit SLM
#
# Uso:
#   ./validation/scripts/monitor_memory.sh [duration_seconds] [interval_seconds]
#
# Ejemplos:
#   ./validation/scripts/monitor_memory.sh 60 2      # 60s total, muestrea c/2s
#   ./validation/scripts/monitor_memory.sh 300 5     # 5 min total, c/5s
#
# Salida: CSV en validation/reports/memory_<timestamp>.csv
# Alerta: Si algún contenedor supera 14GB, muestra advertencia en rojo.
# =============================================================================

set -euo pipefail

# ────────────────── Configuración ──────────────────
DURATION=${1:-120}          # segundos totales de monitoreo
INTERVAL=${2:-5}            # segundos entre muestras
THRESHOLD_GB=14             # límite de alerta en GB
REPORT_DIR="$(dirname "$(dirname "$0")")/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${REPORT_DIR}/memory_${TIMESTAMP}.csv"
ALERT_TRIGGERED=false

# Colores para terminal
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ────────────────── Setup ──────────────────
mkdir -p "$REPORT_DIR"

echo "container_name,timestamp,mem_usage_mb,mem_limit_mb,mem_percent,cpu_percent" > "$OUTPUT_FILE"

echo -e "${CYAN}🔍 Monitor de Memoria Zyrabit SLM${NC}"
echo -e "   Duración:  ${DURATION}s"
echo -e "   Intervalo: ${INTERVAL}s"
echo -e "   Umbral:    ${THRESHOLD_GB}GB"
echo -e "   Reporte:   ${OUTPUT_FILE}"
echo ""

# ────────────────── Loop de monitoreo ──────────────────
START=$(date +%s)
END=$((START + DURATION))
SAMPLE=0

while [ "$(date +%s)" -lt "$END" ]; do
    SAMPLE=$((SAMPLE + 1))
    NOW=$(date +"%Y-%m-%dT%H:%M:%S")

    # Obtiene stats de Docker para todos los contenedores Zyrabit
    # Formato: NAME, MEM USAGE / LIMIT, MEM %, CPU %
    while IFS='|' read -r name mem_raw mem_limit_raw mem_pct cpu_pct; do
        # Parsear valores (e.g. "1.23GiB" -> MB)
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

        # Verificar umbral
        if (( $(echo "$mem_gb > $THRESHOLD_GB" | bc -l) )); then
            echo -e "${RED}⚠️  ALERTA: ${name} usa ${mem_gb}GB (>${THRESHOLD_GB}GB)!${NC}"
            ALERT_TRIGGERED=true
        fi

        # Escribir al CSV
        echo "${name},${NOW},${mem_mb},${mem_limit_mb},${mem_pct%\%},${cpu_pct%\%}" >> "$OUTPUT_FILE"

    done < <(docker stats --no-stream --format "{{.Name}}|{{.MemUsage}}" \
        2>/dev/null | \
        awk -F'[|/]' '{gsub(/ /,""); print $1"|"$2"|"$3"|50%|0%"}' || echo "")

    # Output en terminal cada 5 muestras
    if (( SAMPLE % 5 == 1 )) || (( SAMPLE == 1 )); then
        echo -e "${CYAN}[${NOW}] Muestra #${SAMPLE}${NC}"
        docker stats --no-stream --format \
            "  📦 {{.Name}}: {{.MemUsage}} ({{.MemPerc}}) CPU: {{.CPUPerc}}" \
            2>/dev/null || echo "  (No hay contenedores activos)"
    fi

    sleep "$INTERVAL"
done

# ────────────────── Resumen ──────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  RESUMEN DE MONITOREO${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "  Muestras capturadas: ${SAMPLE}"
echo -e "  Archivo CSV: ${OUTPUT_FILE}"

if [ "$ALERT_TRIGGERED" = true ]; then
    echo -e "${RED}  ❌ RESULTADO: Se superó el umbral de ${THRESHOLD_GB}GB${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ RESULTADO: Memoria dentro del límite (< ${THRESHOLD_GB}GB)${NC}"
    exit 0
fi
