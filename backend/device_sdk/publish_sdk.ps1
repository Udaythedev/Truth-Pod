<#
Build and publish device SDK wheel locally. Requires gh (optional) and twine for publishing to PyPI.

Usage:
  Open PowerShell in backend/device_sdk
  .\publish_sdk.ps1 -Version 0.1.0 -PublishToPyPI:$false -CreateGitHubRelease:$true
#>

param(
  [string]$Version = "0.1.0",
  [switch]$PublishToPyPI = $false,
  [switch]$CreateGitHubRelease = $false
)

Write-Host "Building device SDK (version $Version)"
python -m pip install --upgrade pip build twine
python -m build

if ($CreateGitHubRelease) {
  if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "gh CLI not found; install and authenticate first: https://cli.github.com/"
    exit 1
  }
  $tag = "v$Version"
  Write-Host "Creating draft GitHub release $tag and uploading artifacts..."
  gh release create $tag dist/* --title $tag --notes-file ..\..\CHANGELOG.md --draft
}

if ($PublishToPyPI) {
  Write-Host "Publishing to PyPI via twine..."
  python -m twine upload dist/*
}

Write-Host "Done. Artifacts are in dist\\"
