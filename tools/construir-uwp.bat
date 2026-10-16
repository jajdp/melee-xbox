@echo off
rem Carga el entorno «store» (UWP) de Visual Studio y corre construir_uwp.py con los argumentos
rem dados. Sin ese entorno, INCLUDE y LIB apuntan al escritorio y el binario no sirve.
rem
rem Antes: las variables de entorno de docs/INSTALL.es.md §1 (MELEE_SRC, MELEE_TRABAJO,
rem MELEE_TOOLKIT, MELEE_MSYS).
rem
rem Este archivo tiene que estar en CRLF: con saltos de linea de Unix, cmd parte mal las lineas y
rem vcvarsall falla con mensajes que despistan.
rem
rem Recompilaciones - https://github.com/jajdp/melee-xbox
setlocal

rem El vcvarsall de la instalacion mas nueva, buscado y no fijado.
set VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe
if not exist "%VSWHERE%" (echo no encuentro vswhere.exe: hace falta Visual Studio ^(docs/INSTALL.es.md §1^) & exit /b 1)
for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -property installationPath`) do set VSDIR=%%i
if not defined VSDIR (echo vswhere no encontro ninguna instalacion de Visual Studio & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvarsall.bat" x64 store >nul 2>nul
if not defined INCLUDE (echo vcvarsall x64 store no cargo el entorno: ¿esta instalado el componente de UWP para C++? & exit /b 1)

py -3 -X utf8 "%~dp0construir_uwp.py" %*
