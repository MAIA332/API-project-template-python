@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   BACKUP TOOLKIT (VIA CONNECTION STRING) - DOCKER REMOTO
echo ========================================================
echo.

:: ==========================================
:: 1. CONFIGURACOES DO HOST DOCKER REMOTO
:: ==========================================
set "DOCKER_HOST_URI=ssh://maiaserver@192.168.18.14"
set "DOCKER_HOST=%DOCKER_HOST_URI%"

echo [INFO] Conectando ao Docker remoto em: %DOCKER_HOST_URI%
echo.
echo ========================================================
echo   INFORME OS DADOS (Aperte ENTER para usar o padrao)
echo ========================================================
echo.

:: ==========================================
:: 2. INPUTS DO POSTGRESQL
:: ==========================================
echo --- PostgreSQL ---
set "PG_CONTAINER=meu-postgres"
set /p "PG_CONTAINER=Container Postgres [%PG_CONTAINER%]: "

set "DATABASE_URL=postgres://usuario:senha@192.168.0.x:5432/nome_do_banco"
set /p "DATABASE_URL=Connection String [%DATABASE_URL%]: "
echo.

:: ==========================================
:: 3. INPUTS DO MONGODB
:: ==========================================
echo --- MongoDB ---
set "MONGO_CONTAINER=meu-mongo"
set /p "MONGO_CONTAINER=Container Mongo [%MONGO_CONTAINER%]: "

set "MONGO_URL=mongodb://usuario:senha@192.168.0.x:27017/?directConnection=true"
set /p "MONGO_URL=Connection String [%MONGO_URL%]: "
echo.

:: ==========================================
:: 4. PREPARACAO DO AMBIENTE E VARIAVEIS
:: ==========================================
:: Cria a pasta com a data e hora do backup
set "t=%TIME: =0%"
set "timestamp=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%t:~0,2%%t:~3,2%%t:~6,2%"
set "BACKUP_DIR=backups\backup_%timestamp%"

mkdir "%BACKUP_DIR%\mongo"
mkdir "%BACKUP_DIR%\postgres"

:: ==========================================
:: 5. EXECUCAO DOS BACKUPS
:: ==========================================
echo [1/2] Extraindo dados do MongoDB remoto (Container: %MONGO_CONTAINER%)...
:: Usa a URI completa. Aspas duplas sao essenciais por causa do '&' ou '?' na URL
docker exec %MONGO_CONTAINER% mongodump --uri="%MONGO_URL%" --out="/tmp/mongodump"
:: Copia o diretorio inteiro de dump, garantindo que pega todos os bancos exportados
docker cp %MONGO_CONTAINER%:/tmp/mongodump "%BACKUP_DIR%\mongo"
:: Limpa a sujeira
docker exec %MONGO_CONTAINER% rm -rf /tmp/mongodump

echo.
echo [2/2] Extraindo dados do PostgreSQL remoto (Container: %PG_CONTAINER%)...
:: O pg_dump aceita a URL de conexao completa no lugar do nome do banco
docker exec -t %PG_CONTAINER% pg_dump "%DATABASE_URL%" -F c -f /tmp/pg_backup.dump
docker cp %PG_CONTAINER%:/tmp/pg_backup.dump "%BACKUP_DIR%\postgres\pg_backup.dump"
docker exec %PG_CONTAINER% rm /tmp/pg_backup.dump

echo.
echo ========================================================
echo  SUCESSO! Backup salvo localmente em:
echo  %CD%\%BACKUP_DIR%
echo ========================================================
pause