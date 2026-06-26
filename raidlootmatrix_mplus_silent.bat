@echo off
set RAIDLOOTMATRIX_SCHEDULED=1
"C:\Users\rynec\OneDrive\Documents\RLM-Desktop-Companion\RLM_Companion.exe" --run-mplus --week both > "C:\Users\rynec\OneDrive\Documents\RLM-Desktop-Companion\raidlootmatrix_mplus_auto.log" 2>&1
"C:\Users\rynec\OneDrive\Documents\RLM-Desktop-Companion\RLM_Companion.exe" --run-sync --non-interactive >> "C:\Users\rynec\OneDrive\Documents\RLM-Desktop-Companion\raidlootmatrix_mplus_auto.log" 2>&1
