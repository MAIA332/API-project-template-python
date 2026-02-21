import asyncio
from prisma import Prisma

class PrismaConnection:
    def __init__(self):
        self.prisma = Prisma()
        print("Prisma initialized")

    async def connect(self):
        await self.prisma.connect()
        print("Prisma connected")

    async def disconnect(self):
        
        await self.prisma.disconnect()
        print("Prisma disconnected")

prisma_connection = PrismaConnection()