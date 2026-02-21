@echo OFF
cd ../App && cd prisma && python -m prisma generate --schema ./schema.prisma && cd ../../