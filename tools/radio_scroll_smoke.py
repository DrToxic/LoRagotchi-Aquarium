"""Pixel regression for Radio scroll panes; synthetic history, no radio I/O."""
from pathlib import Path
import json
import tempfile


def exercise(app):
    from panda3d.core import PNMImage, WindowProperties

    controls = app.controls
    panel = controls.radio
    shots = Path('.local/radio-scroll')
    shots.mkdir(parents=True, exist_ok=True)
    props = WindowProperties()
    props.setSize(1100, 800)
    app.win.requestProperties(props)
    for _ in range(12):
        app.taskMgr.step()
    controls.page('Radio')
    panel.page('Chat')
    panel.conversation = 'channel:0:scroll-test'
    results = []

    def capture():
        for _ in range(3):
            app.taskMgr.step()
        image = PNMImage()
        assert app.win.getScreenshot(image)
        return image

    def check_scroll(name, frame, label):
        capture()  # PGScrollFrame applies the outer canvas transform during cull.
        pos = frame.getPos(app.pixel2d)
        scale = frame.getScale(app.pixel2d).x
        left, right, bottom, top = frame['frameSize']
        x0, x1 = round(pos.x+(left+6)*scale), round(pos.x+(right-20)*scale)
        y0, y1 = round(-pos.z-top*scale), round(-pos.z-bottom*scale)
        counts = []
        for step in range(101):
            frame.verticalScroll['value'] = step/100
            image = capture()
            count = sum(min(image.getXel(x, y)) > .5
                        for y in range(y0+3, y1-3, 2) for x in range(x0, x1, 2))
            counts.append(count)
            if step in (0, 67, 100):
                image.write(str(shots/f'{name}-{step:03d}.png'))
        results.append(dict(name=name, pixel_counts=counts))
        (shots/'result.json').write_text(json.dumps(results, indent=2))
        assert min(counts) > 80, (name, counts)
        # The last lines must be reachable without a blank overscroll tail.
        assert any(min(image.getXel(x, y)) > .5
                   for y in range(y1-round(24*scale), y1-3)
                   for x in range(x0, x1)), name
        # Text really clips at the viewport, not by hiding the entire widget.
        frame.verticalScroll['value'] = .67
        visible = capture()
        label.hide()
        hidden = capture()
        label.show()
        assert all(visible.getXel(x, y) == hidden.getXel(x, y)
                   for y in (*range(y0-8, y0), *range(y1+1, y1+9))
                   for x in range(x0, x1)), name
        print(f'PASS {name}: 101 scroll positions, {min(counts)} minimum text pixels, '
              'last line reachable and viewport clips correctly', flush=True)

    def history(count, before=None):
        messages = [dict(id=i+1, timestamp=1700000000+i, direction='in', status='received',
                         text=f'Message {i+1:03d}: Reef chat stays visible while scrolling. '
                              + ('🐟 Café · '+('wide wrapping words '*5) if i%3 == 0 else ''))
                    for i in range(count)]
        panel.draw_history(dict(conversation=panel.conversation, messages=messages, before=before))
        assert panel.transcript.verticalScroll['value'] == (0 if before else 1)

    history(6)
    check_scroll('chat-short', panel.transcript, panel.transcript_label)
    history(60)
    check_scroll('chat-full-page', panel.transcript, panel.transcript_label)
    history(6, before=100)
    check_scroll('chat-older-page', panel.transcript, panel.transcript_label)
    # A new empty conversation must discard the previous page's scroll range.
    panel.choose_chat(None)
    capture()
    assert panel.transcript['canvasSize'][2] == -220
    assert panel.transcript.verticalScroll.isHidden()
    panel.conversation = 'dm:112233445566'
    history(60)
    props.setSize(800, 600)
    app.win.requestProperties(props)
    for _ in range(12):
        app.taskMgr.step()
    check_scroll('chat-scaled-dm', panel.transcript, panel.transcript_label)
    props.setSize(1100, 800)
    app.win.requestProperties(props)
    for _ in range(12):
        app.taskMgr.step()
    panel.page('Tools')
    controls.viewport.verticalScroll['value']=1
    for i in range(60):
        panel.on_event(dict(kind='radio_notice', text=f'Reply {i+1:03d}: 🐟 Remote status '
                            'and telemetry remain visible while scrolling.'))
    check_scroll('tools-full-log', panel.activity_frame, panel.activity_label)
    panel.activity.clear()
    panel.on_event(dict(kind='radio_notice', text='Short reply.'))
    capture()
    assert panel.activity_frame['canvasSize'][2] == -80
    assert panel.activity_frame.verticalScroll.isHidden()
    print('PASS channel/DM paging, Unicode/wrapping, operator scaling and short/empty resets', flush=True)


def main():
    from tank.aquarium import Aquarium
    import sys
    Aquarium.run = exercise
    with tempfile.TemporaryDirectory(prefix='tank-radio-scroll-') as directory:
        sys.argv = [sys.argv[0], '--demo', '0', '--preset', 'low',
                    '--settings', str(Path(directory)/'settings.json')]
        from tank.__main__ import main as run
        run()


if __name__ == '__main__':
    main()
