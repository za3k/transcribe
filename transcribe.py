#!/usr/bin/env python3
import os, sys
import tkinter as tk
from tkinter.ttk import Notebook
import natsort
import PIL, PIL.ImageTk

# add a checkbox for whether to show already-transcribed content, or just stuff to do
# add a progress bar (how many images are transcribed, blacklisted, or yet to do)
class Image(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent)
        self.img = None
        self.bind("<Configure>", self.resize)

    def set(self, image_path):
        self.img = PIL.Image.open(image_path)
        self.update_image(self.img)
    
    def update_image(self, img, width=None, height=None):
        if width is None:
            width, height = self.winfo_width(), self.winfo_height()

        # Keep aspect ratio
        img_width, img_height = img.size
        ratio = min(width*1.0/img_width, height*1.0/img_height)
        width, height = max(int(img_width*ratio),1), max(int(img_height*ratio),1)

        self.pi = PIL.ImageTk.PhotoImage(img.resize(
            (width, height), PIL.Image.ANTIALIAS
        ))
        self.delete("all")
        self.create_image(0, 0, anchor=tk.NW, image=self.pi) 

    def resize(self, event):
        self.update_image(self.img, width=event.width, height=event.height)

class TranscriptionWindow(tk.Tk):
    def __init__(self, *args, **kw_args): 
        super().__init__(*args, **kw_args)
        self.images = []
        self.transcribed = set()
        self.current_image = None

        self.grid()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.frame = frame = tk.Frame(self)
        frame.grid(row=0, column=0, sticky=tk.W+tk.N+tk.E+tk.S)
        # "Flex" rows that take up extra space
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, minsize=100)

        self.sv_current_image = tk.StringVar(frame, "Loading...")
        self.lbl_image = tk.Label(frame, textvariable=self.sv_current_image, padx=20, pady=0)
        self.lbl_image.grid(column=1, row=1)
        self.sv_progress = tk.StringVar(frame, "Loading...")
        self.lbl_progress = tk.Label(frame, textvariable=self.sv_progress, padx=20, pady=0)
        self.lbl_progress.grid(column=1, row=2)
        self.image_canvas = Image(frame)
        self.image_canvas.grid(column=1, row=3, rowspan=2, sticky=tk.W+tk.N+tk.E+tk.S) # row 2+3

        self.txt_entry = tk.Text(frame)
        self.txt_entry.grid(column=2, row=1, rowspan=3, sticky=tk.W+tk.N+tk.E+tk.S)

        self.frm_button = tk.Frame(frame)
        self.frm_button.grid(column=2, row=4)
        self.btn_save = tk.Button(self.frm_button, text="Save transcript")
        self.btn_save.grid(column=1, row=1)
        #self.btn_blacklist = tk.Button(self.frm_button, text="Blacklist (permanent skip)")
        #self.btn_blacklist.grid(column=2, row=1)
        self.btn_skip_prev = tk.Button(self.frm_button, text="Prev image")
        self.btn_skip_prev.grid(column=3, row=1)
        self.btn_skip_next = tk.Button(self.frm_button, text="Next image")
        self.btn_skip_next.grid(column=4, row=1)

        self.btn_save.bind("<Button-1>", self.handle_save)
        self.btn_skip_next.bind("<Button-1>", self.handle_skip_next)
        self.btn_skip_prev.bind("<Button-1>", self.handle_skip_prev)
        #self.btn_blacklist.bind("<Button-1>", self.handle_blacklist)
        self.txt_entry.bind("<Key>", self.handle_keypress)

        self.update_buttons()
        self.update_progress()

    def transcription_content(self):
        return self.txt_entry.get("1.0", tk.END).strip()

    def add_images(self, files):
        self.images.extend(files)
        self.check_transcribed()
        if self.current_image is None:
            self.switch_image()
        self.update_progress()

    def _transcription_path(self, image_path):
        return "{}.txt".format(image_path)

    def check_transcribed(self):
        for image_path in self.images:
            if os.path.exists(self._transcription_path(image_path)):
                self.transcribed.add(image_path)
        # todo - Blacklist typeset documents via a (single, global) blacklist file

    def switch_image(self, offset=1):
        available = natsort.natsorted(set(self.images)-set(self.transcribed))
        if len(available) == 0:
            self.current_image = None
        elif self.current_image is None:
            self.current_image = available[0]
        else:
            current_index = available.index(self.current_image)
            self.current_image = available[(current_index+offset+len(available)) % len(available)]

        if self.current_image is None:
            self.sv_current_image.set("Complete")
        else:
            self.image_canvas.set(self.current_image)
            self.sv_current_image.set(self.current_image)
        self.txt_entry.delete("1.0", tk.END)

    def submit_transcription(self):
        assert self.current_image is not None
        assert self.current_image in self.images
        assert self.current_image not in self.transcribed
        
        with open(self._transcription_path(self.current_image), "w") as f:
            f.write(self.transcription_content()+"\n")
        self.transcribed.add(self.current_image)
        self.current_image = None
        self.check_transcribed()

        self.switch_image()

    def update_buttons(self):
        if self.transcription_content() == "":
            # Enable skip and blacklist. Disable save.
            self.btn_skip_next.config(state=tk.NORMAL)
            self.btn_skip_prev.config(state=tk.NORMAL)
            #self.btn_blacklist.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.DISABLED)
        else:
            # Disable skip and blacklist. Enable save.
            self.btn_skip_next.config(state=tk.DISABLED)
            self.btn_skip_prev.config(state=tk.DISABLED)
            #self.btn_blacklist.config(state=tk.DISABLED)
            self.btn_save.config(state=tk.NORMAL)
    
    def update_progress(self):
        transcribed_count = len(self.transcribed)
        nontranscribed_count = len(self.images) - transcribed_count
        self.sv_progress.set("{} complete | {} incomplete".format(transcribed_count, nontranscribed_count))

    def handle_keypress(self, event):
        self.update_buttons() # slightly wrong because the keypress hasn't been handled yet, so empty/not-empty is off by one keypress

    def handle_save(self, event):
        if self.transcription_content() != "":
            self.submit_transcription()
            self.update_buttons()
            self.update_progress()
        else:
            # Instead grey out submit until you type stuff
            tk.messagebox.showerror("Cannot submit empty transcription")

    def handle_skip_prev(self, event):
        if self.transcription_content() != "":
            return # tk.messagebox doesn't work
        self.switch_image(-1)
        self.update_buttons()
    def handle_skip_next(self, event):
        if self.transcription_content() != "":
            return
        self.switch_image(1)
        self.update_buttons()

    def handle_blacklist(self, event):
        pass # todo

def main():
    window = TranscriptionWindow()

    paths = sys.argv[1:]
    if paths == []:
       paths = [os.getcwd()]
    files = []
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for x in os.listdir(path):
                if os.path.isfile(x):
                    files.append(x)
    files = [f for f in files if not f.endswith(".txt")]

    window.add_images(files)

    window.mainloop()

if __name__ == "__main__":
    main()
