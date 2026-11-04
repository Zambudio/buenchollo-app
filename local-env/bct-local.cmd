@echo off
rem Atajo: ejecuta bct-local.ps1 sin depender de la ExecutionPolicy del PC.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bct-local.ps1" %*
