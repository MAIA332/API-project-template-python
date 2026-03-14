@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   RESTORE TOOLKIT (MENU AUTOMATICO) - MONGO E POSTGRES
echo ========================================================
echo.

set BACKUPS_DIR=backups

if not exist "%BACKUPS_DIR%" (
    echo [ERRO] A pasta '%BACKUPS_DIR%' nao foi encontrada! Certifique-se de gerar um backup primeiro.
    pause
    exit /b
)

echo ==========================================
echo SELECIONE O BACKUP
echo ==========================================
set count=0

:: Lista as pastas dentro de 'backups', ordenando das mais recentes para as mais antigas (/o-d)
for /f "delims=" %%D in ('dir /b /ad /o-d "%BACKUPS_DIR%"') do (
    set /a count+=1
    set "folder_!count!=%BACKUPS_DIR%\%%D"
    echo [!count!] %%D
)

if !count!==0 (
    echo [ERRO] Nenhuma pasta de backup encontrada dentro de '%BACKUPS_DIR%'.
    pause
    exit /b
)

echo.
set /p choice="Digite o NUMERO do backup que deseja restaurar e aperte Enter: "

:: Pega a pasta correspondente ao numero digitado
set BACKUP_FOLDER=!folder_%choice%!

if "!BACKUP_FOLDER!"=="" (
    echo [ERRO] Opcao invalida!
    pause
    exit /b
)

:: Converte para caminho absoluto (O Docker exige isso para mapear os arquivos)
for %%i in ("!BACKUP_FOLDER!") do set ABS_BACKUP_FOLDER=%%~fi

echo.
echo Backup selecionado: !BACKUP_FOLDER!
echo.
echo ==========================================
echo OPCOES DE RESTAURACAO
echo ==========================================

:: Pergunta sobre o MongoDB
set /p DO_MONGO="Deseja restaurar o MONGODB? (S/N): "
if /I "!DO_MONGO!"=="S" (
    set /p TARGET_MONGO="  - Cole a URI do NOVO MongoDB (ex: mongodb://user:pass@host:27017/opa-mongo-db): "
)

echo.

:: Pergunta sobre o PostgreSQL
set /p DO_PG="Deseja restaurar o POSTGRESQL? (S/N): "
if /I "!DO_PG!"=="S" (
    set /p TARGET_POSTGRES="  - Cole a URL do NOVO PostgreSQL (ex: postgresql://user:pass@host:5432/prisma_db): "
)

echo.
echo [AVISO] Isso vai SOBRESCREVER os dados nos bancos de destino informados!
pause

echo.
if /I "!DO_MONGO!"=="S" (
    echo [1/2] Restaurando MongoDB...
    :: ✅ CORREÇÃO APLICADA AQUI: 
    :: Montamos o volume inteiro em /backup e rodamos mongorestore em /backup, 
    :: que conterá nativamente a subpasta do banco e será interpretada corretamente
    docker run --rm -v "!ABS_BACKUP_FOLDER!\mongo:/backup" mongo:4.4 mongorestore --uri="!TARGET_MONGO!" --drop /backup
) else (
    echo [1/2] Pulando a restauracao do MongoDB...
)

echo.
if /I "!DO_PG!"=="S" (
    echo [2/2] Restaurando PostgreSQL...
    docker run --rm -v "!ABS_BACKUP_FOLDER!\postgres:/backup" postgres:15 pg_restore -d "!TARGET_POSTGRES!" --clean --if-exists --no-owner /backup/prisma.dump
) else (
    echo [2/2] Pulando a restauracao do PostgreSQL...
)

echo.
echo ========================================================
echo  SUCESSO! Operacoes concluidas.
echo ========================================================
pause