#!/usr/bin/env python3
"""Run the native aquarium under a temporary local Xvfb. No xauth required.

Usage: .venv/bin/python tools/headless_capture.py --demo 16 --screenshot .local/tank.png
Software rendering is visual verification, never Raspberry Pi performance evidence.
"""
import os,subprocess,sys
r,w=os.pipe()
x=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','1920x1080x24','-nolisten','tcp'],pass_fds=[w],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.close(w)
with os.fdopen(r) as source:display=source.readline().strip()
if not display:raise SystemExit('Xvfb failed to create a display')
try:
    result=subprocess.run([sys.executable,'-m','tank',*sys.argv[1:]],env={**os.environ,'DISPLAY':':'+display})
finally:
    x.terminate();x.wait(timeout=5)
raise SystemExit(result.returncode)
