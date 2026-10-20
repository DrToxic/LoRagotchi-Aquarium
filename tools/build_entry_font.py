"""Build the single-face native entry font from the two bundled OFL fonts.

Development-only: uv run --with fonttools==4.67.0 python tools/build_entry_font.py
Text labels retain their existing font spans. No runtime fontTools dependency.
"""
from pathlib import Path
import tempfile
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.merge import Merger


def main():
    assets=Path(__file__).resolve().parents[1]/'tank/assets'
    with tempfile.TemporaryDirectory(prefix='aquarium-entry-font-') as directory:
        emoji=instantiateVariableFont(TTFont(assets/'NotoEmoji.ttf'),{'wght':400},inplace=True)
        for tag in ('vhea','vmtx','STAT'):
            if tag in emoji:del emoji[tag]
        static=Path(directory)/'emoji.ttf';emoji.save(static)
        merged=Merger().merge([str(assets/'LiberationSans-Regular.ttf'),str(static)])
        names={1:'Aquarium Entry',2:'Regular',3:'Aquarium Entry Regular 1.0',
               4:'Aquarium Entry Regular',6:'AquariumEntry-Regular',16:'Aquarium Entry',17:'Regular'}
        for record in merged['name'].names:
            if record.nameID in names:record.string=names[record.nameID].encode(record.getEncoding())
        for name_id,value in names.items():merged['name'].setName(value,name_id,3,1,0x409)
        merged['head'].created=merged['head'].modified=3800000000
        merged.recalcTimestamp=False
        merged.save(assets/'AquariumEntry-Regular.ttf')
    license_text=('Aquarium Entry Regular is a modified, combined font derived from the\n'
                  'bundled Liberation Sans and Noto Emoji fonts. Family names changed;\n'
                  'original licenses/attributions follow. Distributed under SIL OFL 1.1.\n'
                  'Generator: tools/build_entry_font.py (fontTools 4.67.0).\n\n')
    for name in ('Liberation-LICENSE.txt','NotoEmoji-LICENSE.txt'):
        license_text+=f'--- {name} ---\n'+(assets/name).read_text()+'\n'
    (assets/'AquariumEntry-LICENSE.txt').write_text(license_text)


if __name__=='__main__':main()
