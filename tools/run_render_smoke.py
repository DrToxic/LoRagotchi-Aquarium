import os,subprocess,sys
r,w=os.pipe();x=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','1920x1080x24','-nolisten','tcp'],pass_fds=[w],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(w)
with os.fdopen(r) as f:display=f.readline().strip()
try:
 r=subprocess.run([sys.executable,'-m','tools.render_smoke','--demo','256','--preset','low','--width','960','--height','540','--settings','.local/smoke-settings.json',*sys.argv[1:]],env={**os.environ,'DISPLAY':':'+display})
finally:x.terminate();x.wait(timeout=5)
raise SystemExit(r.returncode)
