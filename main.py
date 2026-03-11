"""
FastAPI backend for AlgoViz
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time, ast, traceback, sys
from io import StringIO

app = FastAPI(title="AlgoViz API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────────

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

class CodeRunInput(BaseModel):
    code: str
    input_array: Optional[List[int]] = None
    target: Optional[int] = None

# ─── Sorting ──────────────────────────────────────────────────────────────────

def _bubble_sort_steps(arr):
    steps, a, n = [], arr[:], len(arr)
    steps.append({"array": a[:], "comparing": [], "swapped": [], "sorted": [], "phase": "start", "info": "Starting Bubble Sort"})
    for i in range(n - 1):
        for j in range(n - i - 1):
            steps.append({"array": a[:], "comparing": [j, j+1], "swapped": [], "sorted": list(range(n-i, n)), "phase": "compare", "info": f"Comparing a[{j}]={a[j]} and a[{j+1}]={a[j+1]}"})
            if a[j] > a[j+1]:
                a[j], a[j+1] = a[j+1], a[j]
                steps.append({"array": a[:], "comparing": [], "swapped": [j, j+1], "sorted": list(range(n-i, n)), "phase": "swap", "info": f"Swapped → now {a[j+1]} before {a[j]}"})
    steps.append({"array": a[:], "comparing": [], "swapped": [], "sorted": list(range(n)), "phase": "done", "info": "✓ Array sorted!"})
    return steps

def _quick_sort_steps(arr):
    steps, a = [], arr[:]
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
        steps.append({"array": arr[:], "pivot": i+1, "comparing": [], "phase": "place_pivot", "info": f"Pivot {pivot} placed at index {i+1}"})
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
    steps, s = [], sorted(arr)
    left, right = 0, len(s) - 1
    steps.append({"array": s, "left": left, "right": right, "mid": -1, "target": target, "phase": "start", "info": f"Binary search for {target}"})
    while left <= right:
        mid = (left + right) // 2
        steps.append({"array": s, "left": left, "right": right, "mid": mid, "target": target, "phase": "check", "info": f"mid={mid}, value={s[mid]}"})
        if s[mid] == target:
            steps.append({"array": s, "left": left, "right": right, "mid": mid, "found": mid, "target": target, "phase": "found", "info": f"✓ Found {target} at index {mid}!"})
            return steps
        elif s[mid] < target:
            left = mid + 1
            steps.append({"array": s, "left": left, "right": right, "mid": mid, "target": target, "phase": "right", "info": f"{s[mid]} < {target}, search right half"})
        else:
            right = mid - 1
            steps.append({"array": s, "left": left, "right": right, "mid": mid, "target": target, "phase": "left", "info": f"{s[mid]} > {target}, search left half"})
    steps.append({"array": s, "left": left, "right": right, "mid": -1, "target": target, "phase": "not_found", "info": f"{target} not found"})
    return steps

def _fib_dp_steps(n):
    steps, dp = [], [None] * (n + 1)
    dp[0], dp[1] = 0, 1
    steps.append({"dp": dp[:], "current": 1, "using": [], "phase": "start", "info": "Initialize: dp[0]=0, dp[1]=1"})
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
        steps.append({"dp": dp[:], "current": i, "using": [i-1, i-2], "phase": "compute", "info": f"dp[{i}] = dp[{i-1}]({dp[i-1]}) + dp[{i-2}]({dp[i-2]}) = {dp[i]}"})
    steps.append({"dp": dp[:], "current": n, "using": [], "phase": "done", "info": f"✓ fib({n}) = {dp[n]}"})
    return steps

# ─── BFS with animated queue ──────────────────────────────────────────────────

def _bfs_steps(nodes, edges, start):
    adj = {n: [] for n in nodes}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)

    steps = []
    visited = set([start])
    queue = [start]
    order = []

    steps.append({
        "visited": list(visited),
        "queue": list(queue),
        "queue_log": [{"node": start, "action": "enqueue", "label": f"Enqueue {start} (start)"}],
        "current": None,
        "order": [],
        "phase": "start",
        "info": f"BFS start — enqueue node {start}"
    })

    while queue:
        node = queue.pop(0)
        order.append(node)

        steps.append({
            "visited": list(visited),
            "queue": list(queue),
            "queue_log": [{"node": node, "action": "dequeue", "label": f"Dequeue {node} — now visiting"}],
            "current": node,
            "order": list(order),
            "phase": "visit",
            "info": f"Dequeued {node} — visiting"
        })

        newly_enqueued = []
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                newly_enqueued.append(neighbor)

        if newly_enqueued:
            steps.append({
                "visited": list(visited),
                "queue": list(queue),
                "queue_log": [{"node": n, "action": "enqueue", "label": f"Enqueue {n}"} for n in newly_enqueued],
                "current": node,
                "order": list(order),
                "phase": "enqueue",
                "info": f"Enqueued neighbors of {node}: {newly_enqueued}"
            })

    steps.append({
        "visited": list(visited),
        "queue": [],
        "queue_log": [],
        "current": None,
        "order": order,
        "phase": "done",
        "info": f"✓ BFS complete: {' → '.join(map(str, order))}"
    })
    return steps

# ─── Safe Python code tracer ──────────────────────────────────────────────────

BLOCKED = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "importlib", "ctypes", "multiprocessing", "threading"}

def _check_safety(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {e}")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            for name in names + [module]:
                if name.split(".")[0] in BLOCKED:
                    raise HTTPException(status_code=400, detail=f"Import '{name}' is not allowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("exec", "eval", "open", "__import__", "compile"):
                raise HTTPException(status_code=400, detail=f"'{node.func.id}' is not allowed")

def _run_python_code(code: str, input_array: list, target):
    _check_safety(code)

    steps = []
    source_lines = code.splitlines()

    builtins_dict = {}
    import builtins as _builtins_mod
    for k in dir(_builtins_mod):
        if k not in ("open", "exec", "eval", "__import__", "compile", "input", "breakpoint"):
            builtins_dict[k] = getattr(_builtins_mod, k)

    exec_globals = {
        "__builtins__": builtins_dict,
        "arr": input_array[:] if input_array else [],
        "array": input_array[:] if input_array else [],
        "nums": input_array[:] if input_array else [],
        "target": target,
        "n": len(input_array) if input_array else 0,
    }
    exec_locals = {}
    stdout_buf = StringIO()

    def _snap(frame):
        snap = {}
        for k, v in {**frame.f_globals, **frame.f_locals}.items():
            if k.startswith("_") or callable(v):
                continue
            try:
                if isinstance(v, (int, float, str, bool, type(None))):
                    snap[k] = v
                elif isinstance(v, list) and len(v) <= 60:
                    if all(isinstance(x, (int, float, str, bool, type(None))) for x in v):
                        snap[k] = list(v)
                elif isinstance(v, dict) and len(v) <= 20:
                    snap[k] = {str(kk): vv for kk, vv in v.items() if isinstance(vv, (int, float, str, bool))}
            except Exception:
                pass
        return snap

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != "<user_code>":
            return tracer
        if event not in ("line", "return"):
            return tracer

        snap = _snap(frame)
        line_no = frame.f_lineno
        line_src = source_lines[line_no - 1].strip() if 0 < line_no <= len(source_lines) else ""

        # Find the best array to display
        array_val = None
        for key in ("arr", "array", "nums", "a", "result", "output"):
            v = snap.get(key)
            if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
                array_val = v
                break

        # Auto-detect comparing indices from loop vars i, j
        comparing = []
        i_v, j_v = snap.get("i"), snap.get("j")
        if array_val:
            if isinstance(i_v, int) and 0 <= i_v < len(array_val):
                comparing.append(i_v)
            if isinstance(j_v, int) and 0 <= j_v < len(array_val) and j_v != i_v:
                comparing.append(j_v)

        # Pull named fields if user set them
        pivot = snap.get("pivot") if isinstance(snap.get("pivot"), int) else None
        left  = snap.get("left")  if isinstance(snap.get("left"),  int) else None
        right = snap.get("right") if isinstance(snap.get("right"), int) else None
        mid   = snap.get("mid")   if isinstance(snap.get("mid"),   int) else None
        found = snap.get("found") if isinstance(snap.get("found"), int) else None

        # Build readable info line from changed locals
        info_parts = []
        for k, v in list(snap.items())[:5]:
            if k not in ("arr", "array", "nums", "target", "n"):
                info_parts.append(f"{k}={v}")
        info = f"Line {line_no}: `{line_src}`" + (f"  →  {', '.join(info_parts)}" if info_parts else "")

        steps.append({
            "array": array_val,
            "locals": snap,
            "line": line_no,
            "line_src": line_src,
            "comparing": comparing,
            "pivot": pivot,
            "left": left,
            "right": right,
            "mid": mid,
            "found": found,
            "phase": "trace",
            "info": info,
        })
        return tracer

    old_stdout = sys.stdout
    sys.stdout = stdout_buf
    try:
        compiled = compile(code, "<user_code>", "exec")
        sys.settrace(tracer)
        exec(compiled, exec_globals, exec_locals)
        sys.settrace(None)
    except Exception:
        sys.settrace(None)
        raise HTTPException(status_code=400, detail=f"Runtime error:\n{traceback.format_exc()}")
    finally:
        sys.stdout = old_stdout

    captured_stdout = stdout_buf.getvalue().splitlines()

    # Deduplicate steps where array didn't change and no important vars moved
    deduped, prev_sig = [], None
    for s in steps:
        sig = (str(s.get("array")), str(s.get("locals")))
        if sig != prev_sig:
            deduped.append(s)
            prev_sig = sig

    if not deduped:
        deduped = [{
            "array": input_array,
            "locals": {},
            "line": 0,
            "line_src": "",
            "comparing": [],
            "phase": "done",
            "info": "Code ran with no traceable variable changes. Try naming your array 'arr', and use variables like i, j, left, right."
        }]

    # Final step
    final_arr = None
    for key in ("arr", "array", "nums", "result"):
        v = exec_locals.get(key) or exec_globals.get(key)
        if isinstance(v, list):
            final_arr = v
            break

    deduped.append({
        "array": final_arr or input_array,
        "locals": {k: v for k, v in exec_locals.items() if not k.startswith("_") and isinstance(v, (int, float, str, bool, list))},
        "stdout": captured_stdout,
        "line": -1,
        "line_src": "",
        "comparing": [],
        "phase": "done",
        "info": f"✓ Done. Output: {captured_stdout[:3]}" if captured_stdout else "✓ Execution complete",
    })

    return deduped

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "AlgoViz API running ⚡", "docs": "/docs"}

@app.post("/api/sort/bubble", response_model=AlgoResponse)
def bubble_sort(body: ArrayInput):
    t = time.time()
    return {"steps": _bubble_sort_steps(body.array), "duration_ms": round((time.time()-t)*1000, 2), "algorithm": "bubbleSort"}

@app.post("/api/sort/quick", response_model=AlgoResponse)
def quick_sort(body: ArrayInput):
    t = time.time()
    return {"steps": _quick_sort_steps(body.array), "duration_ms": round((time.time()-t)*1000, 2), "algorithm": "quickSort"}

@app.post("/api/search/binary", response_model=AlgoResponse)
def binary_search(body: ArrayInput):
    if body.target is None:
        raise HTTPException(status_code=400, detail="target is required")
    t = time.time()
    return {"steps": _binary_search_steps(body.array, body.target), "duration_ms": round((time.time()-t)*1000, 2), "algorithm": "binarySearch"}

@app.post("/api/dp/fibonacci", response_model=AlgoResponse)
def fibonacci_dp(body: DPInput):
    if body.n < 2 or body.n > 40:
        raise HTTPException(status_code=400, detail="n must be between 2 and 40")
    t = time.time()
    return {"steps": _fib_dp_steps(body.n), "duration_ms": round((time.time()-t)*1000, 2), "algorithm": "fibDP"}

@app.post("/api/graph/bfs")
def bfs_traverse(body: GraphInput):
    t = time.time()
    return {"steps": _bfs_steps(body.nodes, body.edges, body.start), "algorithm": "bfs", "duration_ms": round((time.time()-t)*1000, 2)}

@app.post("/api/run/code")
def run_user_code(body: CodeRunInput):
    """Execute user Python code with line-by-line tracer. Returns variable snapshots per step."""
    if not body.code.strip():
        raise HTTPException(status_code=400, detail="No code provided")
    if len(body.code) > 8000:
        raise HTTPException(status_code=400, detail="Code too long (max 8000 chars)")
    t = time.time()
    steps = _run_python_code(body.code, body.input_array or [], body.target)
    return {"steps": steps, "algorithm": "custom", "duration_ms": round((time.time()-t)*1000, 2)}