"""
Kill All Python Trading Processes
Run this to ensure ONLY GUI is running
"""

import os
import sys
import subprocess

print("=" * 70)
print("KILL ALL PYTHON TRADING PROCESSES")
print("=" * 70)
print()

# Windows
if sys.platform == "win32":
    print("🔍 Checking Python processes on Windows...")
    print()
    
    # List all python processes
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # More than just header
            print(f"Found {len(lines) - 1} Python processes:")
            print()
            for line in lines[1:]:  # Skip header
                print(f"  {line}")
            print()
            
            # Ask confirmation
            response = input("❓ Kill ALL Python processes? (y/n): ")
            if response.lower() == 'y':
                subprocess.run(["taskkill", "/F", "/IM", "python.exe"])
                print()
                print("✅ All Python processes killed!")
                print()
                print("🚀 Now run: python launch_gui.py")
            else:
                print("❌ Cancelled")
        else:
            print("✅ No Python processes found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Manual command:")
        print("  taskkill /F /IM python.exe")

# Linux/Mac
else:
    print("🔍 Checking Python processes on Linux/Mac...")
    print()
    
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        python_procs = [line for line in result.stdout.split('\n') 
                       if 'python' in line.lower()]
        
        if python_procs:
            print(f"Found {len(python_procs)} Python processes:")
            print()
            for proc in python_procs:
                print(f"  {proc}")
            print()
            
            # Ask confirmation
            response = input("❓ Kill ALL Python processes? (y/n): ")
            if response.lower() == 'y':
                subprocess.run(["pkill", "-9", "python"])
                print()
                print("✅ All Python processes killed!")
                print()
                print("🚀 Now run: python launch_gui.py")
            else:
                print("❌ Cancelled")
        else:
            print("✅ No Python processes found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Manual command:")
        print("  pkill -9 python")

print()
print("=" * 70)
