import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os

# Add the app directory to sys.path to import ConsensusService
sys.path.append('c:/Users/ASUS/.antigravity/distributed-file-storage-system')

from app.services.consensus import ConsensusService

class HealthMockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_mock_server():
    server = HTTPServer(('localhost', 8001), HealthMockHandler)
    print("Mock server started on port 8001")
    server.serve_forever()

if __name__ == "__main__":
    # Start mock server in a thread
    mock_thread = threading.Thread(target=run_mock_server, daemon=True)
    mock_thread.start()

    # Wait for server to start
    time.sleep(1)

    # Initialize ConsensusService
    # Currently Node A is self, leader starts as Node A.
    # We'll set leader to Node B (localhost:8001)
    service = ConsensusService()
    service.leader = "Node B"
    print(f"Current leader set to: {service.leader}")

    # The health check loop runs every 5 seconds.
    # Wait for one successful check
    print("Waiting for first health check (should be successful)...")
    time.sleep(6)
    print(f"Leader is still: {service.get_leader()}")

    # Now we'll "stop" the server by just ignoring it or we can't easily stop it from here without a global flag
    # But we can just change the service's node_urls to a bunk port to simulate failure
    print("Simulating leader failure by changing URL to invalid port...")
    service.node_urls["Node B"] = "http://localhost:9999"

    print("Waiting for health check to detect failure...")
    # It should detect it within 5 seconds + 2 seconds timeout
    time.sleep(8)

    if service.get_leader() is None or service.get_leader() == "Node A":
        print("SUCCESS: Leader failure detected!")
    else:
        print(f"FAILURE: Leader is still {service.get_leader()}")
