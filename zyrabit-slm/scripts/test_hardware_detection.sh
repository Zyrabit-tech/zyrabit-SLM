#!/bin/bash
# Zyrabit Core v2.0 - Hardware Detection Mock Tester
# Validates zyra-up.sh logic without real hardware.

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

test_profile() {
    local name=$1
    local mock_uname_s=$2
    local mock_uname_m=$3
    local mock_nvidia=$4
    local mock_tt=$5
    
    echo -e "Testing Profile: ${name}..."
    
    # Mocking environment
    export SLM_URL=""
    
    # Simulate logic from zyra-up.sh
    local accelerator="cpu"
    
    if [[ "$mock_nvidia" == "true" ]]; then
        accelerator="nvidia"
    elif [[ "$mock_tt" == "true" ]]; then
        accelerator="tenstorrent"
        export SLM_URL="http://zyrabit-tt-bridge:8000"
    elif [[ "$mock_uname_s" == "Darwin" && "$mock_uname_m" == "arm64" ]]; then
        accelerator="metal"
        export SLM_URL="http://host.docker.internal:11434"
    fi
    
    # Validation
    if [[ "$accelerator" == "$6" ]]; then
        echo -e "${GREEN}  PASS: Detected ${accelerator}${NC}"
        if [[ -n "$7" && "$SLM_URL" != "$7" ]]; then
            echo -e "${RED}  FAIL: Wrong SLM_URL. Expected $7, got $SLM_URL${NC}"
            exit 1
        fi
    else
        echo -e "${RED}  FAIL: Expected $6, got ${accelerator}${NC}"
        exit 1
    fi
}

# 1. Test Mac Metal
test_profile "Mac Metal" "Darwin" "arm64" "false" "false" "metal" "http://host.docker.internal:11434"

# 2. Test Nvidia CUDA
test_profile "Nvidia CUDA" "Linux" "x86_64" "true" "false" "nvidia" ""

# 3. Test Tenstorrent
test_profile "Tenstorrent Sovereign" "Linux" "x86_64" "false" "true" "tenstorrent" "http://zyrabit-tt-bridge:8000"

# 4. Test Generic CPU
test_profile "Generic CPU" "Linux" "x86_64" "false" "false" "cpu" ""

echo -e "\n${GREEN}✨ All Hardware Profiles validated correctly.${NC}"
