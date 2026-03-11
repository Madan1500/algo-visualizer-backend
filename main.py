"""
FastAPI backend for AlgoViz
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import time

app = FastAPI(title="AlgoViz API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request / Response models ────────────────────────────────────────────────

class ArrayInput(BaseModel):
    array: List[int]
    target: Optional[int] = None
    k: Optional[int] = 3

class GraphInput(BaseModel):
    nodes: List[int]
    edges: List[List[int]]
    start: int = 0

class DPInput(BaseModel):
    n: int

class AlgoResponse(BaseModel):
    steps: List[dict]
    duration_ms: float
    algorithm: str

# ─── Sorting ──────────────────────────────────────────────────────────────────

def _bubble_sort_steps(arr):
    steps = []
    a = arr[:]
    n = len(a)
    steps.append({"array": a[:], "comparing": [], "swapped": [], "sorted": [], "phase": "start", "info": "Starting Bubble Sort"})
    for i in range(n - 1):
        for j in range(n - i - 1):
            steps.append({"array": a[:], "comparing": [j, j+1], "swapped": [], "sorted": list(range(n-i, n)), "phase": "compare", "info": f"Comparing a[{j}]={a[j]} and a[{j+1}]={a[j+1]}"})
            if a[j] > a[j+1]:
                a[j], a[j+1] = a[j+1], a[j]
                steps.append({"array": a[:], "comparing": [], "swapped": [j, j+1], "sorted": list(range(n-i, n)), "phase": "swap", "info": f"Swapped → {a[j+1]} and {a[j]}"})
    steps.append({"array": a[:], "comparing": [], "swapped": [], "sorted": list(range(n)), "phase": "done", "info": "✓ Array sorted!"})
    return steps

def _quick_sort_steps(arr):
    steps = []
    a = arr[:]
    steps.append({"array": a[:], "pivot": -1, "comparing": [], "phase": "start", "info": "Starting Quick Sort"})

    def partition(arr, low, high):
        pivot = arr[high]
        steps.append({"array": arr[:], "pivot": high, "comparing": [], "phase": "pivot", "info": f"Pivot: {pivot} at index {high}"})
        i = low - 1
        for j in range(low, high):
            steps.append({"array": arr[:], "pivot": high, "comparing": [j], "phase": "compare", "info": f"Comparing {arr[j]} with pivot {pivot}"})
            if arr[j] <= pivot:
                i += 1
                arr[i], arr[j] = arr[j], arr[i]
                steps.append({"array": arr[:], "pivot": high, "comparing": [i, j], "phase": "swap", "info": f"Swapped {arr[i]} and {arr[j]}"})
        arr[i+1], arr[high] = arr[high], arr[i+1]
        steps.append({"array": arr[:], "pivot": i+1, "comparing": [], "phase": "place_pivot", "info": f"Pivot {pivot} at index {i+1}"})
        return i + 1

    def qs(arr, low, high):
        if low < high:
            pi = partition(arr, low, high)
            qs(arr, low, pi - 1)
            qs(arr, pi + 1, high)

    qs(a, 0, len(a) - 1)
    steps.append({"array": a[:], "pivot": -1, "comparing": [], "phase": "done", "info": "✓ Quick Sort complete!"})
    return steps

def _binary_search_steps(arr, target):
    steps = []
    sorted_arr = sorted(arr)
    left, right = 0, len(sorted_arr) - 1
    steps.append({"array": sorted_arr, "left": left, "right": right, "mid": -1, "target": target, "phase": "start", "info": f"Binary search for {target}"})
    while left <= right:
        mid = (left + right) // 2
        steps.append({"array": sorted_arr, "left": left, "right": right, "mid": mid, "target": target, "phase": "check", "info": f"Checking mid={mid}, value={sorted_arr[mid]}"})
        if sorted_arr[mid] == target:
            steps.append({"array": sorted_arr, "left": left, "right": right, "mid": mid, "found": mid, "target": target, "phase": "found", "info": f"✓ Found {target} at index {mid}!"})
            return steps
        elif sorted_arr[mid] < target:
            left = mid + 1
            steps.append({"array": sorted_arr, "left": left, "right": right, "mid": mid, "target": target, "phase": "right", "info": f"{sorted_arr[mid]} < {target}, search right"})
        else:
            right = mid - 1
            steps.append({"array": sorted_arr, "left": left, "right": right, "mid": mid, "target": target, "phase": "left", "info": f"{sorted_arr[mid]} > {target}, search left"})
    steps.append({"array": sorted_arr, "left": left, "right": right, "mid": -1, "target": target, "phase": "not_found", "info": f"{target} not found"})
    return steps

def _fib_dp_steps(n):
    steps = []
    dp = [None] * (n + 1)
    dp[0] = 0
    dp[1] = 1
    steps.append({"dp": dp[:], "current": 1, "phase": "start", "info": "Initialize: dp[0]=0, dp[1]=1"})
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
        steps.append({"dp": dp[:], "current": i, "using": [i-1, i-2], "phase": "compute", "info": f"dp[{i}] = dp[{i-1}]({dp[i-1]}) + dp[{i-2}]({dp[i-2]}) = {dp[i]}"})
    steps.append({"dp": dp[:], "current": n, "phase": "done", "info": f"✓ fib({n}) = {dp[n]}"})
    return steps

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "AlgoViz API running", "docs": "/docs"}

@app.post("/api/sort/bubble", response_model=AlgoResponse)
def bubble_sort(body: ArrayInput):
    start = time.time()
    steps = _bubble_sort_steps(body.array)
    return {"steps": steps, "duration_ms": round((time.time() - start) * 1000, 2), "algorithm": "bubbleSort"}

@app.post("/api/sort/quick", response_model=AlgoResponse)
def quick_sort(body: ArrayInput):
    start = time.time()
    steps = _quick_sort_steps(body.array)
    return {"steps": steps, "duration_ms": round((time.time() - start) * 1000, 2), "algorithm": "quickSort"}

@app.post("/api/search/binary", response_model=AlgoResponse)
def binary_search(body: ArrayInput):
    if body.target is None:
        raise HTTPException(status_code=400, detail="target is required")
    start = time.time()
    steps = _binary_search_steps(body.array, body.target)
    return {"steps": steps, "duration_ms": round((time.time() - start) * 1000, 2), "algorithm": "binarySearch"}

@app.post("/api/dp/fibonacci", response_model=AlgoResponse)
def fibonacci_dp(body: DPInput):
    if body.n < 2 or body.n > 40:
        raise HTTPException(status_code=400, detail="n must be between 2 and 40")
    start = time.time()
    steps = _fib_dp_steps(body.n)
    return {"steps": steps, "duration_ms": round((time.time() - start) * 1000, 2), "algorithm": "fibDP"}

@app.post("/api/graph/bfs")
def bfs_traverse(body: GraphInput):
    adj = {n: [] for n in body.nodes}
    for a, b in body.edges:
        adj[a].append(b)
        adj[b].append(a)

    steps = []
    visited = set()
    queue = [body.start]
    order = []
    visited.add(body.start)
    steps.append({"visited": list(visited), "queue": list(queue), "current": None, "order": [], "phase": "start", "info": f"BFS from node {body.start}"})

    while queue:
        node = queue.pop(0)
        order.append(node)
        steps.append({"visited": list(visited), "queue": list(queue), "current": node, "order": list(order), "phase": "visit", "info": f"Visiting node {node}"})
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                steps.append({"visited": list(visited), "queue": list(queue), "current": node, "order": list(order), "phase": "enqueue", "info": f"Enqueued {neighbor}"})

    steps.append({"visited": list(visited), "queue": [], "current": None, "order": order, "phase": "done", "info": f"✓ BFS done: {' → '.join(map(str, order))}"})
    return {"steps": steps, "algorithm": "bfs", "duration_ms": 0}