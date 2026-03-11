const { execSync } = require('child_process');
const path = require('path');

process.chdir('C:/Users/PC/Documents/GitHub/cli-hub-portal-vibe');

try {
    console.log("=== GIT STATUS ===");
    console.log(execSync('git status', { encoding: 'utf8' }));
    
    console.log("=== GIT DIFF ===");
    console.log(execSync('git diff', { encoding: 'utf8', maxBuffer: 10*1024*1024 }));
    
    console.log("=== GIT DIFF --CACHED ===");
    console.log(execSync('git diff --cached', { encoding: 'utf8', maxBuffer: 10*1024*1024 }));
    
    console.log("=== GIT REMOTE -V ===");
    console.log(execSync('git remote -v', { encoding: 'utf8' }));
} catch (e) {
    console.log("Error:", e.message);
    console.log("stdout:", e.stdout);
    console.log("stderr:", e.stderr);
}