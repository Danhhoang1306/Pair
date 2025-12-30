#!/bin/bash
# Rename gold/silver variables to primary/secondary
sed -i 's/gold_pos\b/primary_pos/g' main_cli.py
sed -i 's/silver_pos\b/secondary_pos/g' main_cli.py
sed -i 's/gold_closed\b/primary_closed/g' main_cli.py
sed -i 's/silver_closed\b/secondary_closed/g' main_cli.py
sed -i 's/gold_missing\b/primary_missing/g' main_cli.py
sed -i 's/silver_missing\b/secondary_missing/g' main_cli.py
sed -i 's/gold_result\b/primary_result/g' main_cli.py
sed -i 's/silver_result\b/secondary_result/g' main_cli.py
sed -i 's/gold_lots\b/primary_lots/g' main_cli.py
sed -i 's/silver_lots\b/secondary_lots/g' main_cli.py
sed -i 's/gold_quantity\b/primary_quantity/g' main_cli.py
sed -i 's/silver_quantity\b/secondary_quantity/g' main_cli.py
sed -i 's/gold_value\b/primary_value/g' main_cli.py
sed -i 's/silver_value\b/secondary_value/g' main_cli.py
echo "Renamed all gold/silver variables to primary/secondary"
