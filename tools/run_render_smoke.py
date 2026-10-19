import os,subprocess,sys
r,w=os.pipe();x=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=[w],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(w)
with os.fdopen(r) as f:display=f.readline().strip()
try:
 r=subprocess.run([sys.executable,'-m','tools.render_smoke','--demo','12','--settings','.local/smoke-settings.json'],env={**os.environ,'DISPLAY':':'+display})
finally:x.terminate();x.wait()
raise SystemExit(r.returncode)
