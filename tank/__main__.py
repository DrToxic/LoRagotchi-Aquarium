import argparse
from pathlib import Path
import os

def main():
    parser=argparse.ArgumentParser(description="LoRagotchi Community Tank — native 3D snapshot aquarium")
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--demo",type=int,nargs="?",const=12,help="bounded synthetic visitors (0..256), no radio")
    mode.add_argument("--replay",type=Path,help="JSONL records: rx public-key hex and payload hex")
    mode.add_argument("--connect",help="serial:PORT, ble:ADDRESS or tcp:HOST:PORT")
    parser.add_argument("--token-file",type=Path,help="32-byte pairing token for authenticated TCP bridge")
    parser.add_argument("--database",type=Path)
    parser.add_argument("--session",default="community")
    parser.add_argument("--settings",type=Path,default=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'loragotchi-tank'/'settings.json')
    parser.add_argument("--preset",choices=("compatibility","low","balanced","high","ultra"))
    parser.add_argument("--width",type=int,default=1280);parser.add_argument("--height",type=int,default=720)
    parser.add_argument("--render-scale",type=float)
    for name in ("detail","plants","bubbles","fps"):parser.add_argument("--"+name,type=int)
    parser.add_argument("--no-lighting",action="store_true");parser.add_argument("--no-caustics",action="store_true")
    parser.add_argument("--no-vsync",action="store_true")
    parser.add_argument("--fullscreen",action="store_true")
    parser.add_argument("--operator",action="store_true",help="show operator controls at startup")
    parser.add_argument("--wall-columns",type=int,choices=(1,2),default=1,help="one or two separate aquarium windows")
    parser.add_argument("--second-width",type=int,help="second window width (defaults to primary)")
    parser.add_argument("--second-height",type=int,help="second window height (defaults to primary)")
    parser.add_argument("--second-origin",type=int,nargs=2,metavar=("X","Y"),help="second window desktop position; negative monitor coordinates allowed")
    parser.add_argument("--screenshot",type=Path);parser.add_argument("--capture-after",type=float,default=3)
    parser.add_argument("--run-seconds",type=float,default=0)
    args=parser.parse_args()
    for key,low,high in (("detail",8,48),("plants",0,100),("bubbles",0,100),("fps",10,240)):
        value=getattr(args,key)
        if value is not None and not low<=value<=high:parser.error(f"{key} must be {low}..{high}")
    if args.demo is None and not args.connect and not args.replay:args.demo=12
    if args.demo is not None and not 0<=args.demo<=256:parser.error("Demo fish count must be 0..256")
    if args.width<320 or args.height<180:parser.error("Output must be at least 320x180")
    if args.second_width is not None and args.second_width<320:parser.error("Second output width must be at least 320")
    if args.second_height is not None and args.second_height<180:parser.error("Second output height must be at least 180")
    if args.render_scale is not None and not .25<=args.render_scale<=2:parser.error("Render scale must be .25..2")
    if args.connect and args.connect.startswith('tcp:') and not args.token_file:parser.error("TCP bridge needs --token-file")
    if not args.database:
        if args.demo is not None or args.replay:args.database=Path(':memory:')
        else:
            data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'loragotchi-tank';data.mkdir(parents=True,exist_ok=True)
            args.database=data/'live.sqlite'
    from .aquarium import Aquarium
    app=Aquarium(args)
    try:app.run()
    finally:app.destroy()

if __name__=="__main__":main()
