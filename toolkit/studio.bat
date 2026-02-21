@echo OFF
:: Navega para a raiz do projeto onde o .env deve estar
cd /d "%~dp0\.."

:: Executa o migrate apontando para o schema (o Prisma procurará o .env na raiz)
python -m prisma studio --schema .\App\prisma\schema.prisma

:: Volta para a pasta toolkit
cd toolkit