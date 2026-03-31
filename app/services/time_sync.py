import httpx
import time
import asyncio

drift_offset=0.0

NODE_CONFIG={
    "nodeA": "http://127.0.0.1:8000",
    "nodeB": "http://127.0.0.1:8001",
    "nodeC": "http://127.0.0.1:8002"
}

def get_current_node_time():
    """Returns the 'Synchronized' time for the whole system."""
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
        
async def perform_sync(leader_id: str):
    """Calculates and applies the clock offset using Cristian's Algorithm."""
    global drift_offset

    if leader_id not in NODE_CONFIG:
        return{"status":"error","message":"Unknown Leader ID"}
    url=f"{NODE_CONFIG[leader_id]}/time"
async def perform_sync(leader_id: str):
    """Calculates and applies the clock offset using Cristian's Algorithm."""
    global drift_offset
    
    if leader_id not in NODE_CONFIG:
        return {"status": "error", "message": "Unknown leader ID"}

    url = f"{NODE_CONFIG[leader_id]}/time"
    
    async with httpx.AsyncClient() as client:
        try:
            t_request = time.time()
            response = await client.get(url, timeout=2.0)
            response.raise_for_status()
            
            t_server = response.json()["node_time"]
            t_response = time.time()
            
            rtt = t_response - t_request
            synchronized_time = t_server + (rtt / 2)
            
            drift_offset = synchronized_time - t_response
            
            return {
                "status": "success",
                "new_offset": drift_offset,
                "synchronized_time": get_current_node_time(),
                "RTT": rtt
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
async def start_periodic_sync(Leader_id:str,interval:int =60):
    """
        Background loop that synchronizes time every interval seconds.
        maintains  consistent timestamps across the distributed system.
    """
    print(f"info: Background sync task started. targeting Leader {Leader_id} every {interval} seconds.")
    while True:
        await asyncio.sleep(interval)
        result = await perform_sync(Leader_id)
        if result["status"]=="success":
            print(f"info: periodic sync successful. New offset: {result['new_offset']:.4f}s")
        else:
            print(f"Warning:periodic sync failed: {result['message']}")
