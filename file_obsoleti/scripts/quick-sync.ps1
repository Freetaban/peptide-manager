# Quick Sync - Versione Rapida
# Uso: .\scripts\quick-sync.ps1

Write-Host "🚀 Quick Sync Feature Branch" -ForegroundColor Cyan

# Checkout master, pull, checkout feature, rebase, push
git checkout master
if ($LASTEXITCODE -eq 0) { git pull }
if ($LASTEXITCODE -eq 0) { git checkout feature/wastage-and-multiprep }
if ($LASTEXITCODE -eq 0) { git rebase master }
if ($LASTEXITCODE -eq 0) { git push --force-with-lease }

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Sync completato!" -ForegroundColor Green
} else {
    Write-Host "❌ Errore durante sync. Controlla i conflitti." -ForegroundColor Red
}
