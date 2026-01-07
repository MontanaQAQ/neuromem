#!/bin/bash
# NeuroMem Quick Start Script
# Helps users quickly set up and test NeuroMem (sage.neuromem)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source helper scripts (splitting responsibilities under utils/installation)
source "$SCRIPT_DIR/utils/installation/common.sh"
source "$SCRIPT_DIR/utils/installation/install_dev.sh"
source "$SCRIPT_DIR/utils/installation/verify_install.sh"
source "$SCRIPT_DIR/utils/installation/precommit.sh"
source "$SCRIPT_DIR/utils/installation/tests.sh"
source "$SCRIPT_DIR/utils/installation/dependencies.sh"
source "$SCRIPT_DIR/utils/installation/example.sh"

# Select language first
select_language

# Initialize logging and environment
init_logging
print_main_banner
if [[ "$LANG_SETTING" == "zh" ]]; then
    print_info "$(get_msg 'installation_log'): $LOG_FILE"
else
    print_info "$(get_msg 'installation_log'): $LOG_FILE"
fi
log ""

# Check conda environment (required)
check_conda_environment

# Core installation + verification
install_neuromem_dev
verify_neuromem_install
show_installed_version

# Optional dev helpers
maybe_install_precommit
maybe_run_basic_tests

# User guidance and examples
show_quick_example_and_docs

# Optional dependency checks
check_optional_dependencies

# Final summary
show_final_summary
