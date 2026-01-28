#!/bin/bash
# Move to script directory
cd "$(dirname "$0")"

# Run the Python script
python3 gemini_rate_checker.py

# Keep terminal open if there's an error, or wait 10s
if [ $? -ne 0 ]; then
    echo "❌ Execution failed."
    read -p "Press enter to close..."
else
    echo "✅ Success! Waiting 5 seconds..."
    sleep 5
fi
