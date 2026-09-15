<#
.SYNOPSIS
    Equivalente de `make` para Windows sin GNU make.

.DESCRIPTION
    Envoltorio fino sobre `scripts/tasks.py`, igual que el `Makefile`. Los dos
    caminos ejecutan exactamente los mismos pasos (DECISIONS.md, D-14).

.PARAMETER Targets
    Uno o mas targets: install, demo, test, lint, typecheck, inventory,
    verify, clean. Sin argumentos, lista los disponibles.

.PARAMETER Python
    Interprete con el que crear el entorno virtual. Por defecto usa `py -3.12`
    si el lanzador de Python esta disponible, y `python` en caso contrario.

.PARAMETER Venv
    Directorio del entorno virtual. Por defecto `.venv`.

.EXAMPLE
    ./make.ps1 install
    ./make.ps1 verify
    ./make.ps1 lint test
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $Targets = @(),

    [string] $Python = '',

    [string] $Venv = ''
)

$ErrorActionPreference = 'Stop'

if ($Venv) { $env:VENV = $Venv }

# Resolucion del interprete: un `python` del PATH puede ser 3.11, y el proyecto
# exige 3.12 (DECISIONS.md, D-13). El lanzador `py` es la via fiable en Windows.
$exe = 'python'
$prefix = @()

if ($Python) {
    $exe = $Python
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -c 'pass' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $exe = 'py'
        $prefix = @('-3.12')
    }
}

$tasks = Join-Path $PSScriptRoot 'scripts\tasks.py'
& $exe @prefix $tasks @Targets
exit $LASTEXITCODE
