#!/usr/bin/env python3
import subprocess
import os

os.chdir(r'C:\Users\PC\Documents\GitHub\cli-hub-portal-vibe')

# Use shell=True on Windows
print("=== GIT STATUS ===")
result = subprocess.run('git status', shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== GIT DIFF ===")
result = subprocess.run('git diff', shell=True, capture_output=True, text=True)
print(result.stdout[:5000] if len(result.stdout) > 5000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== GIT DIFF --CACHED ===")
result = subprocess.run('git diff --cached', shell=True, capture_output=True, text=True)
print(result.stdout[:5000] if len(result.stdout) > 5000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== GIT REMOTE -V ===")
result = subprocess.run('git remote -v', shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)