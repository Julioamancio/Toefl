@echo off
REM Script para backup automatico do banco de dados TOEFL Dashboard
REM Uso: backup_script.bat [backup|restore|export|import]

setlocal enabledelayedexpansion

REM Definir diretorio de backups
set BACKUP_DIR=backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Obter data e hora atual para nome do arquivo
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"

if "%1"=="backup" (
    echo Fazendo backup do banco de dados...
    python database_backup.py backup --file "%BACKUP_DIR%\toefl_backup_%timestamp%.db"
    if !errorlevel! equ 0 (
        echo Backup criado com sucesso: %BACKUP_DIR%\toefl_backup_%timestamp%.db
    ) else (
        echo Erro ao criar backup
    )
) else if "%1"=="export" (
    echo Exportando dados para JSON...
    python database_backup.py export --file "%BACKUP_DIR%\toefl_export_%timestamp%.json"
    if !errorlevel! equ 0 (
        echo Exportacao criada com sucesso: %BACKUP_DIR%\toefl_export_%timestamp%.json
    ) else (
        echo Erro ao exportar dados
    )
) else if "%1"=="restore" (
    if "%2"=="" (
        echo Uso: backup_script.bat restore [caminho_do_arquivo]
        exit /b 1
    )
    echo Restaurando banco de dados de: %2
    python database_backup.py restore --file "%2"
    if !errorlevel! equ 0 (
        echo Restauracao concluida com sucesso
    ) else (
        echo Erro ao restaurar banco
    )
) else if "%1"=="import" (
    if "%2"=="" (
        echo Uso: backup_script.bat import [caminho_do_arquivo_json]
        exit /b 1
    )
    echo Importando dados de: %2
    python database_backup.py import --file "%2"
    if !errorlevel! equ 0 (
        echo Importacao concluida com sucesso
    ) else (
        echo Erro ao importar dados
    )
) else (
    echo Uso: backup_script.bat [backup^|restore^|export^|import] [arquivo]
    echo.
    echo Comandos:
    echo   backup  - Cria backup do banco de dados
    echo   export  - Exporta dados para JSON
    echo   restore [arquivo] - Restaura banco de backup
    echo   import [arquivo]  - Importa dados de JSON
    echo.
    echo Exemplos:
    echo   backup_script.bat backup
    echo   backup_script.bat export
    echo   backup_script.bat restore backups\toefl_backup_20231201_143022.db
    echo   backup_script.bat import backups\toefl_export_20231201_143022.json
)

endlocal