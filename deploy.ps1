$git = "C:\Program Files\Git\cmd\git.exe"

& $git init
& $git add .
& $git commit -m "Deploy to IntelliVest"
& $git branch -M main
& $git remote add origin https://github.com/physicswallah5851-cell/IntelliVest.git
# If remote already exists, set it
& $git remote set-url origin https://github.com/physicswallah5851-cell/IntelliVest.git

Write-Host "Pushing to GitHub... A login window may appear!"
& $git push -u origin main
