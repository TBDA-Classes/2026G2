#!/bin/bash
# Task 6 — every comparison of the report (test/validation x 16/8 circuits, test without the NE|HVAC event).
#   bash run_task6_all.sh            -> results/task6_<run>/
set -e
cd "$(dirname "$0")"
export SCALE_FILE=data/task6_circuit_scale_train_mean_v1.2.csv EVENTS_FILE=data/task6_events_test.csv
P=results/predictions
M16="ML_RandomForest ML_Linear ML_GBM_v1.3 ML_Chronos_v1.3 ML_ChronosGBM_v1.3 ML_Blend_v1.3 B1_last_week B2_weekday_hour_median B3_persistence"
M8="$M16 ML_GBM_v1.0 ML_Chronos_v1.1"
files(){ split=$1; shift; for m in "$@"; do echo "$P/${m}_${split}_predictions.csv"; done; }
run(){ out=$1; shift; echo ">> $out"; mkdir -p results/$out; OUT_DIR=results/$out python3 task6_compare.py "$@" > results/$out/log.txt 2>&1; }
SPLIT_LABEL=Test       run task6_test_16circuits                $(files test $M16)
SPLIT_LABEL=Test       run task6_test_8circuits                 $(files test $M8)
SPLIT_LABEL=Test EXCLUDE_EVENTS=1 run task6_test_16circuits_without_events $(files test $M16)
SPLIT_LABEL=Test EXCLUDE_EVENTS=1 run task6_test_8circuits_without_events  $(files test $M8)
SPLIT_LABEL=Validation run task6_validation_16circuits          $(files validation $M16)
SPLIT_LABEL=Validation run task6_validation_8circuits           $(files validation $M8)
python3 figures/task6_make_figure.py
