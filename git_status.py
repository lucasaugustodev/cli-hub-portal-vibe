#!/usr/bin/env python3
import subprocess
import os

os.chdir(r'C:\Users\PC\Documents\GitHub\cli-hub-portal-vibe')

print("=== GIT STATUS ===")
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

print("\n=== GIT DIFF ===")
result = subprocess.run(['git', 'diff'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

print("\n=== GIT DIFF --CACHED ===")
result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)