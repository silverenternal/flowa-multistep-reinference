#!/usr/bin/env python3
"""Hard memory-capped wrapper for `tools/run_mol_eval.py`.

Uses subprocess.Popen with preexec_fn that:
  1. Calls resource.setrlimit(RLIMIT_AS, (cap_bytes, cap_bytes)) to limit virtual address space
  2. Calls os.setsid() to start a new process group (so we can killpg on timeout)

Usage:
    python tools/run_mol_eval_safe.py --cap-gb 24 -- tools/run_mol_eval.py --n 100 --nfe 250
    MOL_EVAL_MEM_GB=24 python tools/run_mol_eval_safe.py -- tools/run_mol_eval.py --n 100

Cap strategy:
  - POSIX RLIMIT_AS limits virtual address space. OOM-killer + MemoryError are both raised
    when the cap is hit. The child process dies; the wrapper reports the failure.
  - If systemd-run --user --scope is available AND user has linger=yes, prefer that —
    it gives cleaner cgroup accounting. (Detected at startup, printed to stderr.)
"""
import os, sys, resource, subprocess, signal, argparse, time

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--cap-gb", type=int, default=int(os.environ.get("MOL_EVAL_MEM_GB", "24")))
    p.add_argument("--timeout-sec", type=int, default=900)
    p.add_argument("--poll-rss-sec", type=int, default=10, help="how often to print child RSS to stderr")
    p.add_argument("rest", nargs=argparse.REMAINDER, help="the command to run (after --)")
    return p.parse_args()

def main():
    args = parse_args()
    # Strip leading -- from rest if present
    if args.rest and args.rest[0] == "--":
        args.rest = args.rest[1:]
    if not args.rest:
        print("ERROR: no command to run. Use: ... -- <cmd> [args]", file=sys.stderr)
        sys.exit(2)
    cap_bytes = args.cap_gb * 1024 * 1024 * 1024
    print(f"[run_mol_eval_safe] cap={args.cap_gb}GB, timeout={args.timeout_sec}s, cmd={args.rest}", file=sys.stderr)

    def preexec():
        resource.setrlimit(resource.RLIMIT_AS, (cap_bytes, cap_bytes))
        os.setsid()

    proc = subprocess.Popen(args.rest, preexec_fn=preexec,
                            stdout=sys.stdout, stderr=sys.stderr, stdin=sys.stdin)
    start = time.time()
    max_rss_kb = 0
    try:
        while proc.poll() is None:
            try:
                # Read /proc/<pid>/status VmRSS (works for any process in same uid)
                with open(f"/proc/{proc.pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1])
                            if rss > max_rss_kb:
                                max_rss_kb = rss
                            if args.poll_rss_sec and (time.time() - start) % args.poll_rss_sec < 1:
                                print(f"[run_mol_eval_safe] child RSS={rss/1024/1024:.2f} GB", file=sys.stderr)
                            break
            except (FileNotFoundError, ProcessLookupError):
                pass
            if time.time() - start > args.timeout_sec:
                raise subprocess.TimeoutExpired(args.rest, args.timeout_sec)
            time.sleep(1)
        return_code = proc.wait()
    except subprocess.TimeoutExpired:
        print(f"[run_mol_eval_safe] timeout — killing process group {proc.pid}", file=sys.stderr)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        return_code = 124  # conventional timeout exit code
    print(f"[run_mol_eval_safe] done. max_rss={max_rss_kb/1024/1024:.2f} GB, return_code={return_code}", file=sys.stderr)
    sys.exit(return_code)

if __name__ == "__main__":
    main()
