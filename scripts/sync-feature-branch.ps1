# Sync Feature Branch with Master
# Questo script aggiorna la feature branch con le ultime modifiche di master

param(
    [string]$FeatureBranch = "feature/wastage-and-multiprep",
    [switch]$UseMerge = $false  # Default: usa rebase, con -UseMerge usa merge
)

Write-Host "🔄 Sincronizzazione Feature Branch con Master" -ForegroundColor Cyan
Write-Host ""

# 1. Salva eventuali modifiche non committate
Write-Host "📦 Controllo modifiche non salvate..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  Ci sono modifiche non committate. Stashing..." -ForegroundColor Yellow
    git stash push -m "Auto-stash before sync $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $stashed = $true
} else {
    Write-Host "✓ Working directory pulito" -ForegroundColor Green
    $stashed = $false
}

# 2. Vai su master e aggiorna
Write-Host ""
Write-Host "📥 Aggiornamento master da remote..." -ForegroundColor Yellow
git checkout master
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Errore nel checkout di master" -ForegroundColor Red
    exit 1
}

git pull origin master
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Errore nel pull di master" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Master aggiornato" -ForegroundColor Green

# 3. Vai sulla feature branch
Write-Host ""
Write-Host "🌿 Passaggio a $FeatureBranch..." -ForegroundColor Yellow
git checkout $FeatureBranch
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Errore nel checkout della feature branch" -ForegroundColor Red
    exit 1
}

# 4. Integra master nella feature branch
Write-Host ""
if ($UseMerge) {
    Write-Host "🔀 Merge di master in $FeatureBranch..." -ForegroundColor Yellow
    git merge master -m "Merge master into $FeatureBranch"
    $syncMethod = "merge"
} else {
    Write-Host "📍 Rebase di $FeatureBranch su master..." -ForegroundColor Yellow
    git rebase master
    $syncMethod = "rebase"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⚠️  Conflitti rilevati!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Risolvi i conflitti manualmente, poi:" -ForegroundColor Yellow
    if ($syncMethod -eq "rebase") {
        Write-Host "  git add <files>" -ForegroundColor Cyan
        Write-Host "  git rebase --continue" -ForegroundColor Cyan
    } else {
        Write-Host "  git add <files>" -ForegroundColor Cyan
        Write-Host "  git commit" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "Per annullare:" -ForegroundColor Yellow
    if ($syncMethod -eq "rebase") {
        Write-Host "  git rebase --abort" -ForegroundColor Cyan
    } else {
        Write-Host "  git merge --abort" -ForegroundColor Cyan
    }
    exit 1
}

Write-Host "✓ Sincronizzazione completata con successo" -ForegroundColor Green

# 5. Push della feature branch aggiornata
Write-Host ""
Write-Host "📤 Push della feature branch aggiornata..." -ForegroundColor Yellow

if ($syncMethod -eq "rebase") {
    # Con rebase serve force-with-lease
    Write-Host "⚠️  Il rebase richiede force push. Procedo con --force-with-lease per sicurezza..." -ForegroundColor Yellow
    git push --force-with-lease origin $FeatureBranch
} else {
    git push origin $FeatureBranch
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Errore nel push" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Push completato" -ForegroundColor Green

# 6. Ripristina stash se necessario
if ($stashed) {
    Write-Host ""
    Write-Host "📦 Ripristino modifiche stashed..." -ForegroundColor Yellow
    git stash pop
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Modifiche ripristinate" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Conflitti nel ripristino stash. Risolvi manualmente con: git stash pop" -ForegroundColor Yellow
    }
}

# 7. Riepilogo
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ SINCRONIZZAZIONE COMPLETATA" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "Branch: $FeatureBranch" -ForegroundColor White
Write-Host "Metodo: $syncMethod" -ForegroundColor White
Write-Host ""
Write-Host "Comandi utili:" -ForegroundColor Yellow
Write-Host "  git log --oneline --graph --all -20    # Visualizza storia" -ForegroundColor Cyan
Write-Host "  git diff master..$FeatureBranch        # Vedi differenze" -ForegroundColor Cyan
Write-Host ""
