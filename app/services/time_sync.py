import time 
 
def get_current_node_time(): 
    return time.time() 
def synchronize_clock(target_time):
    return {"status": "success", "new_time": target_time}