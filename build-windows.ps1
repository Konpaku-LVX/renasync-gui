#!/usr/bin/env pwsh
# Build a standalone windows gui executable and setup installer.
# Pulls in renasync itself (from Codeberg) and bundles it with the addon.
# Requires: python, pip, git and either the 7z tool or a prebuilt mpv runtime dll.
# Inno Setup is installed automatically when missing (winget, then choco).

param(
	# skip building the installer, only produce the exe
	[switch]$NoInstaller
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Bundle the libmpv runtime as mpv-2.dll: python-mpv looks for it first,
# then libmpv-2.dll, then mpv-1.dll.
$dll = Join-Path $root 'mpv-2.dll'

# accept a prebuilt runtime dll dropped next to this script (any soname)
if (-not (Test-Path $dll)) {
	foreach ($alt in @('mpv-2.dll', 'libmpv-2.dll', 'mpv-1.dll', 'libmpv-1.dll')) {
		$candidate = Join-Path $root $alt

		if (Test-Path $candidate) {
			Move-Item $candidate $dll
			break
		}
	}
}

# fetch windows libmpv if not already present
if (-not (Test-Path $dll)) {
	$release = Invoke-RestMethod 'https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest'
	$asset = $release.assets | Where-Object { $_.name -match '^mpv-dev-x86_64.*\.7z$' } | Select-Object -First 1

	if (-not $asset) {
		throw 'Could not find a mpv-dev x86_64 archive'
	}

	$archive = Join-Path $env:TEMP $asset.name
	$extract = Join-Path $env:TEMP 'renasync-mpv'

	Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
	New-Item -ItemType Directory -Force -Path $extract | Out-Null

	# 7z is preinstalled on github windows runners
	$sevenzip = Get-Command 7z -ErrorAction SilentlyContinue

	if (-not $sevenzip) {
		$candidate = 'C:\Program Files\7-Zip\7z.exe'

		if (Test-Path $candidate) {
			$sevenzip = Get-Item $candidate
		}
	}

	if (-not $sevenzip) {
		throw '7z is required to extract the mpv runtime dll (place a prebuilt mpv dll next to this script instead)'
	}

	$seven = $sevenzip.Source
	if (-not $seven) {
		$seven = $sevenzip.FullName
	}

	& $seven x $archive "-o$extract" | Out-Null

	# the runtime dll may sit in a bin dir or at the archive root, under
	# mpv-1.dll, libmpv-1.dll, mpv-2.dll or libmpv-2.dll depending on the
	# mpv soname of the current release
	$found = Get-ChildItem $extract -Recurse -File |
		Where-Object { $_.Name -match '^(lib)?mpv-[0-9]+\.dll$' } |
		Select-Object -First 1

	if (-not $found) {
		throw "mpv runtime dll not found in archive $($asset.name)"
	}

	Copy-Item $found.FullName $dll
	Remove-Item $archive -Force -ErrorAction SilentlyContinue
	Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
}

# install deps and build the exe (renasync 1.0.2 is pulled from Codeberg and bundled;
# if Codeberg is unreachable, pin $root to vendor/renasync instead)
Push-Location $root
python -m pip install --quiet 'git+https://codeberg.org/xordev/renasync.git@1.0.2' '.[build]'
$pipExit = $LASTEXITCODE
Pop-Location

if ($pipExit -ne 0) {
	throw "pip install failed with exit code $pipExit"
}

$entry = Join-Path $env:TEMP 'renasync_gui_entry.py'
Set-Content -Path $entry -Value "from renasync_gui import main`nmain()`n"

python -m PyInstaller -F -w -n renasync-gui --add-data "$dll;." $entry
$pyiExit = $LASTEXITCODE
Remove-Item $entry -Force

if ($pyiExit -ne 0) {
	throw "PyInstaller failed with exit code $pyiExit"
}

Write-Host "Built dist/renasync-gui.exe"

if ($NoInstaller) {
	return
}

# installer version from the nearest git tag (v0.0.1 -> 0.0.1)
$tag = git describe --tags --exact-match 2>$null
if (-not $tag) {
	$tag = git describe --tags 2>$null
}
if (-not $tag) {
	$tag = 'v0.0.1'
}

$version = (($tag -replace '^v', '') -replace '[^0-9.]', '')
if (-not $version) {
	$version = '0.0.1'
}

function Get-InnoSetup {
	$candidates = @(
		'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
		'C:\Program Files\Inno Setup 6\ISCC.exe'
	)

	foreach ($path in $candidates) {
		if (Test-Path $path) {
			return $path
		}
	}

	$cmd = Get-Command iscc -ErrorAction SilentlyContinue

	if ($cmd) {
		return $cmd.Source
	}

	return $null
}

$iscc = Get-InnoSetup

if (-not $iscc) {
	Write-Host 'Inno Setup not found, installing it...'

	if (Get-Command winget -ErrorAction SilentlyContinue) {
		winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements | Out-Null
		$iscc = Get-InnoSetup
	}

	if (-not $iscc) {
		if (Get-Command choco -ErrorAction SilentlyContinue) {
			choco install innosetup -y | Out-Null
			$iscc = Get-InnoSetup
		}
	}

	if (-not $iscc) {
		throw 'Inno Setup (ISCC.exe) is required to build the installer. Install it from https://jrsoftware.org/isdl.php or run: winget install -e JRSoftware.InnoSetup'
	}
}

& $iscc "/DMyAppVersion=$version" (Join-Path $root 'renasync.iss')
if ($LASTEXITCODE -ne 0) {
	throw "ISCC failed with exit code $LASTEXITCODE"
}

Write-Host "Built dist/Renasync-Setup-$version.exe"