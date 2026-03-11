@echo off
cd /d C:\Users\PC\Documents\GitHub\cli-hub-portal-vibe
echo === GIT STATUS ===
git status
echo.
echo === GIT DIFF ===
git diff
echo.
echo === GIT DIFF --CACHED ===
git diff --cached
echo.
echo === GIT REMOTE -V ===
git remote -v
pause