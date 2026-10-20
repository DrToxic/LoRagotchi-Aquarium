"""Run a native module in an isolated Xvfb display without requiring xauth."""
import os
import subprocess
import sys


def main():
    r,w=os.pipe()
    server=subprocess.Popen(["Xvfb","-displayfd",str(w),"-screen","0","3840x2160x24","-nolisten","tcp"],
                            pass_fds=[w],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(w)
    try:
        with os.fdopen(r) as stream:display=stream.readline().strip()
        if not display:raise RuntimeError("Xvfb failed to start")
        return subprocess.call([sys.executable,"-m",*sys.argv[1:]],env={**os.environ,"DISPLAY":":"+display})
    finally:
        server.terminate();server.wait(timeout=5)


if __name__=="__main__":raise SystemExit(main())
