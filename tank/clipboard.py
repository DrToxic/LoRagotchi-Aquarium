"""Native clipboard via Python's Tk binding; no extra visible application/UI."""


class Clipboard:
    def __init__(self):self.root=None

    def get_root(self):
        if self.root is None:
            import tkinter
            self.root=tkinter.Tk();self.root.withdraw()
        return self.root

    def copy(self,text):
        root=self.get_root();root.clipboard_clear();root.clipboard_append(text);root.update()

    def paste(self):return self.get_root().clipboard_get()

    def pump(self):
        if self.root is not None:self.root.update()

    def close(self):
        if self.root is not None:self.root.destroy();self.root=None
