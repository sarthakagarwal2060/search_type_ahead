import time
import urllib.request
import json
import threading
from concurrent.futures import ThreadPoolExecutor

READ_URL = "http://localhost/suggest?q=google"
WRITE_URL = "http://localhost/search"
TOTAL_REQUESTS = 10000
CONCURRENCY = 1

def make_read_request(_):
    start = time.perf_counter()
    try:
        req = urllib.request.Request(READ_URL)
        with urllib.request.urlopen(req) as response:
            response.read()
            return time.perf_counter() - start, True
    except Exception:
        return time.perf_counter() - start, False

def make_write_request(_):
    start = time.perf_counter()
    try:
        data = json.dumps({"query": "viral test query"}).encode('utf-8')
        req = urllib.request.Request(WRITE_URL, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as response:
            response.read()
            return time.perf_counter() - start, True
    except Exception:
        return time.perf_counter() - start, False

def run_benchmark(name, func):
    print(f"\n--- Starting {name} Benchmark ---")
    print(f"Target: {TOTAL_REQUESTS} requests with {CONCURRENCY} concurrent threads")
    
    start_time = time.time()
    latencies = []
    successes = 0
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        results = list(executor.map(func, range(TOTAL_REQUESTS)))
        
    end_time = time.time()
    total_time = end_time - start_time
    
    for lat, success in results:
        latencies.append(lat)
        if success:
            successes += 1
            
    latencies.sort()
    
    print(f"Time taken: {total_time:.2f} seconds")
    print(f"Successful requests: {successes}/{TOTAL_REQUESTS}")
    print(f"Requests per second (RPS): {TOTAL_REQUESTS / total_time:.2f} [#/sec]")
    print(f"Fastest Request: {latencies[0]*1000:.2f} ms")
    print(f"Average Request: {(sum(latencies)/len(latencies))*1000:.2f} ms")
    print(f"95th Percentile: {latencies[int(len(latencies)*0.95)]*1000:.2f} ms")
    print(f"Slowest Request: {latencies[-1]*1000:.2f} ms")

if __name__ == "__main__":
    print("Wait 2 seconds for server to settle...")
    time.sleep(2)
    run_benchmark("READ LATENCY (Nginx -> Redis Cache)", make_read_request)
    run_benchmark("WRITE LATENCY (Nginx -> Batch Writer Queue)", make_write_request)
