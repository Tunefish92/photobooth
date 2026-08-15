@echo off
REM Launches the photobooth app for local Windows dev (dummy camera/PDF
REM printer backends -- see README.md's Windows setup section). Works from
REM a double-click in Explorer or from a terminal, regardless of the
REM current directory.

cd /d "%~dp0.."
uv run photobooth

if errorlevel 1 (
    echo.
    echo Photobooth exited with an error ^(see above^).
    pause
)
