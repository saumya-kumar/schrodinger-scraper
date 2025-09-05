import os, uuid, json, signal, threading, subprocess, time
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Ecom Pipeline API", version="1.0")

PIPELINE_SCRIPT = os.environ.get("PIPELINE_SCRIPT", "/app/s1_complete_ecommerce_pipeline.py")
PYTHON_BIN      = os.environ.get("PYTHON_BIN", "python")
RESULTS_ROOT    = os.environ.get("RESULTS_ROOT", "/app/results")
LOGS_ROOT       = os.environ.get("LOGS_ROOT", "/app/logs")

os.makedirs(RESULTS_ROOT, exist_ok=True)
os.makedirs(LOGS_ROOT, exist_ok=True)

_JOBS = {}
_LOCK = threading.Lock()

def _utc_now():
    return datetime.now(timezone.utc).isoformat()

def _job_results_dir(job_id: str) -> str:
    d = os.path.join(RESULTS_ROOT, job_id)
    os.makedirs(d, exist_ok=True)
    return d

def _finalize(job_id: str, rc: int):
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job["return_code"] = rc
        job["finished_at"] = _utc_now()
        job["status"] = "succeeded" if rc == 0 else "failed"

    jd = _job_results_dir(job_id)
    result = {
        "job_id": job_id,
        "status": _JOBS[job_id]["status"],
        "return_code": rc,
        "started_at": _JOBS[job_id]["started_at"],
        "finished_at": _JOBS[job_id]["finished_at"],
        "args": _JOBS[job_id]["args"],
        "results_dir": jd,
        "log_path": _JOBS[job_id]["log_path"],
    }
    with open(os.path.join(jd, "job_result.json"), "w") as f:
        json.dump(result, f, indent=2)

    md = [
        f"# Job {job_id}",
        "",
        f"- **Status:** {result['status']}",
        f"- **Return code:** {rc}",
        f"- **Started:** {result['started_at']}",
        f"- **Finished:** {result['finished_at']}",
        f"- **Args:** `{ ' '.join(result['args']) }`",
        "",
        "## Files",
        "- `job_result.json` — status summary",
        "- `job_request.json` — request metadata",
        "- CSV/JSON/MD emitted by your script (relative paths go here).",
    ]
    with open(os.path.join(jd, "job_summary.md"), "w") as f:
        f.write("\n".join(md))

def _launch(job_id: str, args: List[str], timeout: Optional[int]):
    jd = _job_results_dir(job_id)

    with open(os.path.join(jd, "job_request.json"), "w") as f:
        json.dump({
            "job_id": job_id,
            "created_at": _utc_now(),
            "args": args,
            "timeout": timeout,
            "cwd": jd,
            "script": PIPELINE_SCRIPT,
        }, f, indent=2)

    env = os.environ.copy()

    cmd = [PYTHON_BIN, "-u", PIPELINE_SCRIPT] + args
    log_path = os.path.join(LOGS_ROOT, f"{job_id}.log")
    log_f = open(log_path, "a", buffering=1)

    proc = subprocess.Popen(
        cmd,
        cwd=jd,  # your script writes CSV/JSON/MD to results/<job_id>
        stdout=log_f,               # captures print() and errors
        stderr=subprocess.STDOUT,   # merge stderr into the same log
        text=True,
        env=env,
        preexec_fn=os.setsid  # Linux: put in its own process group
    )

    with _LOCK:
        _JOBS[job_id]["proc"] = proc
        _JOBS[job_id]["status"] = "running"
        _JOBS[job_id]["started_at"] = _utc_now()
        _JOBS[job_id]["log_path"] = log_path
        _JOBS[job_id]["results_dir"] = jd

    def _waiter():
        rc = proc.wait()
        try:
            log_f.flush()
            log_f.close()
        except Exception:
            pass
        _finalize(job_id, rc)

    def _timeout_guard():
        if timeout and timeout > 0:
            deadline = time.time() + timeout
            while time.time() < deadline:
                if proc.poll() is not None:
                    return
                time.sleep(0.5)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(2)
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

    threading.Thread(target=_waiter, daemon=True).start()
    threading.Thread(target=_timeout_guard, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/run")
def run(
    args: List[str] = Query(default=[], description="Repeat ?args=... e.g. /run?args=--mode&args=train"),
    timeout: Optional[int] = Query(default=None),
    label: Optional[str] = Query(default=None),
):
    if not os.path.exists(PIPELINE_SCRIPT):
        raise HTTPException(500, f"Script not found at {PIPELINE_SCRIPT}")

    suffix = label.strip().replace(" ", "-") if label else "job"
    job_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + suffix + "-" + uuid.uuid4().hex[:8]

    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": None,
            "finished_at": None,
            "return_code": None,
            "args": args,
            "log_path": os.path.join(LOGS_ROOT, f"{job_id}.log"),
            "results_dir": _job_results_dir(job_id),
        }

    _launch(job_id, args, timeout)
    return {
        "job_id": job_id,
        "status": _JOBS[job_id]["status"],
        "results_dir": _JOBS[job_id]["results_dir"],
        "log_path": _JOBS[job_id]["log_path"],
        "hint": "Tail logs at /logs/{job_id} and check status at /status/{job_id}",
    }

@app.get("/status/{job_id}")
def status(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {k: v for k, v in job.items() if k != "proc"}

@app.get("/logs/{job_id}")
def logs(job_id: str, tail: int = Query(200, ge=1, le=5000)):
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        path = job["log_path"]
    if not os.path.exists(path):
        return {"lines": []}
    lines = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        try:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 4096
            data = ""
            while size > 0 and len(lines) <= tail:
                size = max(0, size - block)
                f.seek(size)
                data = f.read(block) + data
                lines = data.splitlines()
        except Exception:
            f.seek(0)
            lines = f.readlines()
    return {"lines": lines[-tail:]}

@app.get("/cancel/{job_id}")
def cancel(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        proc = job.get("proc")
        if not proc or proc.poll() is not None:
            return {"status": job["status"], "message": "Job already finished"}
        job["status"] = "cancelling"
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    return {"status": "cancelling"}
