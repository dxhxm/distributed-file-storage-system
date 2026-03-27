import httpx
import time

NODE_CONFIG={
    "nodeA": "http://127.0.0.1:8000",
    "nodeB": "http://127.0.0.1:8001",
    "nodeC": "http://127.0.0.1:8002"
}

def get_current_node_time():
    return time.time()
def synchronize_clock(target_time):
    return {"status": "success", "new_time": target_time}

async def fetch_remote_time(target_node_id: str):
    """Fetch the time from a neighbor node to calculate RTT."""
    if target_node_id not in NODE_CONFIG:
        return {"error:unknown node ID."}
    url= f"{NODE_CONFIG[target_node_id]}/time"
    print(f"DEBUG: Node A is attempting to contact {target_node_id} at {url}")
    start_time=time.time()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=2.0)
            print(f"DEBUG: Received status {response.status_code} from {target_node_id}")
            response.raise_for_status()

            remote_Data=response.json()
            end_time=time.time()

            return{
                "remote_time":remote_Data["node_time"],
                "RTT": end_time- start_time,
                "status":"success"
            }
        except Exception as e:
            print(f"CRITICAL ERROR in fetch_remote_time: {str(e)}")
            return{"status":"Error","message":str(e)}