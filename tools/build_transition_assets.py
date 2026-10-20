"""Regenerate editable, original pickup models: uv run python -m tools.build_transition_assets."""
from tank.transition_art import make_actor
from tank.transitions import ASSETS, STYLES


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    for style in STYLES:
        node=make_actor(style)
        if style!="shark":node.flattenStrong()
        assert node.writeBamFile(str(ASSETS/(style+".bam")))
        node.removeNode()
        print("Built",style)


if __name__=="__main__":main()
