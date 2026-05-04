@ECHO OFF

REM Command file for Sphinx documentation.

pushd %~dp0

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=build

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure Sphinx is installed,
	echo.then set SPHINXBUILD to the full path of the executable. Alternatively,
	echo.add the Sphinx directory to PATH.
	echo.
	echo.If you do not have Sphinx installed, install docs requirements first:
	echo.
	echo.    pip install -r requirements.txt
	echo.
	goto end
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:end
popd
