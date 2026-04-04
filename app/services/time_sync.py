import httpx
import time
import asyncio
from app.api.consensus import consensus_service

drift_offset=0.0
target_offset = 0.0
last_returned_time=0.0
SLEW_RATE=0.001
SLEW_INTERVAL=0.1
max_skew_threshold=60.0

NODE_CONFIG = {
    "Node A": "http://127.0.0.1:8000",
    "Node B": "http://127.0.0.1:8001",
    "Node C": "http://127.0.0.1:8002"
}

def get_current_node_time():
    """Returns the 'Synchronized' time for the whole system."""
    global last_returned_time
    current = time.time() + drift_offset
    if current <= last_returned_time:
        current = last_returned_time + 0.000001
    last_returned_time = current
    return current
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
        
async def perform_sync(leader_id: str,samples: int = 5):
    """
    Calculates and applies the clock offset using an enhanced Cristian's Algorithm.
    
    This function implements (High-Precision RTT Filtering) by gathering
    multiple samples to filter out non-deterministic network jitter.
    
    Mathematical Foundation:
    T_{sync} = T_{server} + \frac{1}{2n} \sum_{i=1}^{n} RTT_i
    """
    global drift_offset,target_offset
    
    if leader_id not in NODE_CONFIG:
        return {"status": "error", "message": "Unknown leader ID"}

    url = f"{NODE_CONFIG[leader_id]}/time"
    rtt_list = []
    server_times = []

    async with httpx.AsyncClient() as client:
        for i in range(samples):
            try:
                t_request = time.time()
                response = await client.get(url, timeout=1.5)
                t_response = time.time()
                response.raise_for_status()
                
                data=response.json()
                rtt_list.append(t_response - t_request)
                server_times.append(data["node_time"])

                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"WARNING: Sample {i+1} failed: {e}")
                continue
    if not rtt_list:
        return {"status": "error", "message": "Zero valid samples collected."}
    avg_rtt = sum(rtt_list) / len(rtt_list)
    latest_server_time = server_times[-1]
    synchronized_time = latest_server_time + (avg_rtt / 2)
    new_calculated_offset=synchronized_time- time.time()
    
    if abs(new_calculated_offset-drift_offset) > max_skew_threshold:
        print(f"CRITICAL: Rejected Byzantine time from {leader_id}. Skew: {new_calculated_offset:.2f}s")
        return {
            "status": "error",
            "message": f"Byzantine Fault Detected: Clock skew ({new_calculated_offset:.2f}s) exceeds safety threshold.",
            "current active_offset": drift_offset,
        }
    target_offset = new_calculated_offset
    return {
                    "status": "success",
                    "applied_target": target_offset,
                    "current_active_offset": drift_offset,
                    "Avg_RTT": avg_rtt,
                    "samples_collected": len(rtt_list),
                    "synchronized_time": get_current_node_time(),
                    "precision_boost": "Active (Statistical Average)"
                }
async def start_periodic_sync(Leader_id:str,interval:int =30):
    """
        Background loop that synchronizes time every interval seconds.
        maintains  consistent timestamps across the distributed system.
        automatically finds leader and synchronizes
    """
    while True:
        leader_name= consensus_service.get_leader()
        my_name= consensus_service.current_node

        if leader_name and leader_name != my_name:
            print(f"INFO: Synchronizing time with leader: {leader_name}")
            result = await perform_sync(leader_name)
            
            if result["status"] == "success":
                print(f"INFO: Sync successful. New offset: {result['new_offset']:.6f}s")
            else:
                print(f"WARNING: Sync failed: {result['message']}")
        else:
            print(f"DEBUG: I am the leader ({my_name}) or no leader exists. Skipping.")

        await asyncio.sleep(interval)
async def start_clock_slew():
    """background task that gradually adjusts the drift_offset toward target_offset.
       prevent suddent time jumps in distributed system."""
    global drift_offset, target_offset
    while True:
        diff= target_offset - drift_offset
        if abs(diff) > 0.000001:
            adjustment=max(min(diff, SLEW_RATE),-SLEW_RATE)
            drift_offset += adjustment
        await asyncio.sleep(SLEW_INTERVAL)