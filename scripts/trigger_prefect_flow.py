import asyncio
from prefect.client import get_client

async def trigger():
    async with get_client() as client:
        # Lấy thông tin deployment từ Prefect Orion
        deployment = await client.read_deployment_by_name("Kafka to Delta Pipeline/kafka-to-delta")
        # Tạo và khởi chạy Flow Run
        flow_run = await client.create_flow_run_from_deployment(deployment.id)
        print(f"Successfully triggered flow run! Run ID: {flow_run.id}")

if __name__ == "__main__":
    asyncio.run(trigger())
