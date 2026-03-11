Set-Location "C:\Users\PC\Documents\GitHub\cli-hub-portal-vibe"
git status > git_status.txt 2>&1
git diff >> git_status.txt 2>&1
git diff --cached >> git_status.txt 2>&1
git remote -v >> git_status.txt 2>&1
Get-Content git_status.txt