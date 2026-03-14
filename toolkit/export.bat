@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   BACKUP TOOLKIT (VIA DOCKER) - MONGODB E POSTGRESQL
echo ========================================================
echo.

:: ==========================================
:: SOLICITACAO DE CREDENCIAIS (INPUT)
:: ==========================================
echo Por favor, insira as credenciais para realizar o backup:
echo.
set /p PG_USER="1. Digite o USUARIO do PostgreSQL (ex: admin): "
set /p PG_PASS="2. Digite a SENHA do PostgreSQL: "
echo.
set /p MONGO_USER="3. Digite o USUARIO do MongoDB (ex: mongo_user): "
set /p MONGO_PASS="4. Digite a SENHA do MongoDB: "
echo.

:: ==========================================
:: CONFIGURACOES FIXAS DOS BANCOS E CONTAINERS
:: ==========================================
set PG_DB_NAME=OPA
set MONGO_DB_NAME=opa-mongo-db
set MONGO_CONTAINER=opaan-mongodb
set PG_CONTAINER=opaan-postgres

:: Monta a URI do Mongo injetando as variaveis digitadas
set MONGO_URI="mongodb://%MONGO_USER%:%MONGO_PASS%@localhost:27017/%MONGO_DB_NAME%?authSource=admin"

:: Cria a pasta com a data e hora do backup
set "t=%TIME: =0%"
set "timestamp=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%t:~0,2%%t:~3,2%%t:~6,2%"
set BACKUP_DIR=backups\backup_%timestamp%

mkdir "%BACKUP_DIR%\mongo"
mkdir "%BACKUP_DIR%\postgres"

echo [1/2] Extraindo dados do MongoDB (Container: %MONGO_CONTAINER%)...
:: Manda o container gerar o backup la dentro usando a URI com as credenciais inseridas
docker exec %MONGO_CONTAINER% mongodump --uri=%MONGO_URI% --out="/tmp/mongodump"
:: Puxa o backup para o Windows
docker cp %MONGO_CONTAINER%:/tmp/mongodump/%MONGO_DB_NAME% "%BACKUP_DIR%\mongo\%MONGO_DB_NAME%"
:: Limpa a sujeira dentro do container
docker exec %MONGO_CONTAINER% rm -rf /tmp/mongodump

echo.
echo [2/2] Extraindo dados do PostgreSQL (Container: %PG_CONTAINER%)...
:: Manda o container gerar o dump do Postgres usando as credenciais inseridas
docker exec -e PGPASSWORD=%PG_PASS% -t %PG_CONTAINER% pg_dump -U %PG_USER% -F c -f /tmp/prisma.dump %PG_DB_NAME%
:: Puxa o arquivo para o Windows
docker cp %PG_CONTAINER%:/tmp/prisma.dump "%BACKUP_DIR%\postgres\prisma.dump"
:: Limpa a sujeira
docker exec %PG_CONTAINER% rm /tmp/prisma.dump

echo.
echo ========================================================
echo  SUCESSO! Backup salvo em: %BACKUP_DIR%
echo ========================================================
pause