from __future__ import annotations

import random
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from subterra.config import RESOLUTION_PRESETS
from subterra.filters import FILTER_NAMES
from subterra.narrative import STYLE_CHOICES


ROOT=Path(__file__).resolve().parent


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SUBTERRA 0.2 — Music to Film")
        self.geometry("1040x820")
        self.minsize(920,700)
        self.audio=tk.StringVar()
        self.output=tk.StringVar(value=str(ROOT/"output"/"subterra_film.mp4"))
        self.lyrics=tk.StringVar()
        self.resolution=tk.StringVar(value="1080p")
        self.width=tk.StringVar(value="1920")
        self.height=tk.StringVar(value="1080")
        self.fps=tk.StringVar(value="30")
        self.seed=tk.StringVar(value=str(random.randint(1,2_147_483_647)))
        self.style=tk.StringVar(value="reference_collage")
        self.filter_name=tk.StringVar(value="auto")
        self.filter_intensity=tk.DoubleVar(value=.72)
        self.edit_density=tk.DoubleVar(value=.68)
        self.render_scale=tk.StringVar(value="0.75")
        self.audio_mode=tk.StringVar(value="preserve")
        self.encoder=tk.StringVar(value="auto")
        self.preview_seconds=tk.StringVar(value="")
        self.strobe=tk.DoubleVar(value=.12)
        self.typography=tk.BooleanVar(value=True)
        self.media:list[str]=[]
        self._build()

    def _build(self):
        outer=ttk.Frame(self); outer.pack(fill="both",expand=True,padx=14,pady=12)
        ttk.Label(outer,text="SUBTERRA 0.2",font=("Arial",22,"bold")).pack(anchor="w")
        ttk.Label(outer,text="Música → filme techno underground · montagem procedural · filtros autorais · processamento local").pack(anchor="w",pady=(0,8))
        notebook=ttk.Notebook(outer); notebook.pack(fill="both",expand=True)
        main=ttk.Frame(notebook); visual=ttk.Frame(notebook); export=ttk.Frame(notebook)
        notebook.add(main,text="Entrada"); notebook.add(visual,text="Direção visual"); notebook.add(export,text="Exportação")
        self._build_main(main); self._build_visual(visual); self._build_export(export)
        bottom=ttk.Frame(outer); bottom.pack(fill="x",pady=(10,0))
        ttk.Button(bottom,text="Diagnóstico do PC",command=self.run_diagnose).pack(side="left")
        ttk.Button(bottom,text="Prévia de 15 s",command=lambda:self.run_render(preview=15)).pack(side="left",padx=8)
        ttk.Button(bottom,text="Renderizar filme",command=self.run_render).pack(side="left")
        self.log=tk.Text(outer,height=13,bg="#101014",fg="#e8e8e8",insertbackground="white")
        self.log.pack(fill="both",expand=True,pady=(10,0))

    def _row(self,parent,row,label,var,button=None,button_text="Selecionar",width=76):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",padx=10,pady=8)
        ttk.Entry(parent,textvariable=var,width=width).grid(row=row,column=1,sticky="ew",padx=10,pady=8)
        if button: ttk.Button(parent,text=button_text,command=button).grid(row=row,column=2,padx=10,pady=8)

    def _build_main(self,f):
        self._row(f,0,"Áudio",self.audio,self.pick_audio)
        self._row(f,1,"Saída",self.output,self.pick_output,"Salvar como")
        self._row(f,2,"Letra/legenda (opcional)",self.lyrics,self.pick_lyrics,"Selecionar")
        mf=ttk.Frame(f); mf.grid(row=3,column=0,columnspan=3,sticky="ew",padx=10,pady=8)
        ttk.Button(mf,text="Adicionar imagens/vídeos base",command=self.pick_media).pack(side="left")
        ttk.Button(mf,text="Limpar mídias",command=self.clear_media).pack(side="left",padx=8)
        self.media_label=ttk.Label(mf,text="Nenhuma mídia base"); self.media_label.pack(side="left",padx=10)
        info=("A letra aceita SRT, VTT, LRC ou TXT. Vídeos e imagens base são usados em colagens, CRT, câmera rave, "
              "halftone, machine vision e datamosh.")
        ttk.Label(f,text=info,wraplength=820).grid(row=4,column=0,columnspan=3,sticky="w",padx=10,pady=8)
        f.columnconfigure(1,weight=1)

    def _build_visual(self,f):
        ttk.Label(f,text="Linguagem visual").grid(row=0,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.style,values=STYLE_CHOICES,state="readonly",width=34).grid(row=0,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Filtro de pós-produção").grid(row=1,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.filter_name,values=FILTER_NAMES,state="readonly",width=34).grid(row=1,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Intensidade do filtro").grid(row=2,column=0,sticky="w",padx=10,pady=8)
        ttk.Scale(f,from_=0,to=1,variable=self.filter_intensity,orient="horizontal",length=420).grid(row=2,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,textvariable=self.filter_intensity).grid(row=2,column=2,sticky="w")
        ttk.Label(f,text="Densidade de montagem").grid(row=3,column=0,sticky="w",padx=10,pady=8)
        ttk.Scale(f,from_=0,to=1,variable=self.edit_density,orient="horizontal",length=420).grid(row=3,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,textvariable=self.edit_density).grid(row=3,column=2,sticky="w")
        ttk.Label(f,text="Flashes / strobe seguro").grid(row=4,column=0,sticky="w",padx=10,pady=8)
        ttk.Scale(f,from_=0,to=.30,variable=self.strobe,orient="horizontal",length=420).grid(row=4,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,textvariable=self.strobe).grid(row=4,column=2,sticky="w")
        ttk.Checkbutton(f,text="Usar tipografia, frases e legendas",variable=self.typography).grid(row=5,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Seed").grid(row=6,column=0,sticky="w",padx=10,pady=8)
        sf=ttk.Frame(f); sf.grid(row=6,column=1,sticky="w",padx=10,pady=8)
        ttk.Entry(sf,textvariable=self.seed,width=20).pack(side="left")
        ttk.Button(sf,text="Nova história",command=lambda:self.seed.set(str(random.randint(1,2_147_483_647)))).pack(side="left",padx=8)
        desc=("reference_collage aproxima a gramática observada no vídeo de referência: microcortes, infraestrutura elétrica, "
              "tipografia cinética, telas CRT, material documental e colagens. auto usa todos os arquétipos.")
        ttk.Label(f,text=desc,wraplength=820).grid(row=7,column=0,columnspan=3,sticky="w",padx=10,pady=12)

    def _build_export(self,f):
        ttk.Label(f,text="Preset de resolução").grid(row=0,column=0,sticky="w",padx=10,pady=8)
        combo=ttk.Combobox(f,textvariable=self.resolution,values=[*RESOLUTION_PRESETS,"personalizada"],state="readonly",width=24)
        combo.grid(row=0,column=1,sticky="w",padx=10,pady=8); combo.bind("<<ComboboxSelected>>",self.apply_resolution)
        ttk.Label(f,text="Largura digitável").grid(row=1,column=0,sticky="w",padx=10,pady=8)
        ttk.Entry(f,textvariable=self.width,width=14).grid(row=1,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Altura digitável").grid(row=2,column=0,sticky="w",padx=10,pady=8)
        ttk.Entry(f,textvariable=self.height,width=14).grid(row=2,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="FPS").grid(row=3,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.fps,values=["24","25","30","50","60"],width=12).grid(row=3,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Escala interna").grid(row=4,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.render_scale,values=["0.35","0.5","0.65","0.75","1.0"],width=12).grid(row=4,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Encoder").grid(row=5,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.encoder,values=["auto","h264_nvenc","hevc_nvenc","libx264","libx265"],state="readonly",width=20).grid(row=5,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Tratamento do áudio").grid(row=6,column=0,sticky="w",padx=10,pady=8)
        ttk.Combobox(f,textvariable=self.audio_mode,values=["preserve","streaming","cinema","club","normalize"],state="readonly",width=20).grid(row=6,column=1,sticky="w",padx=10,pady=8)
        ttk.Label(f,text="Limite opcional de prévia (s)").grid(row=7,column=0,sticky="w",padx=10,pady=8)
        ttk.Entry(f,textvariable=self.preview_seconds,width=14).grid(row=7,column=1,sticky="w",padx=10,pady=8)
        note=("A largura e a altura são sempre editáveis. Valores ímpares são ajustados para o número par imediatamente inferior, "
              "exigência comum do H.264. Para sua RTX 4060: 1080p/0.75 é o padrão; 4K/0.5 é indicado para render final.")
        ttk.Label(f,text=note,wraplength=820).grid(row=8,column=0,columnspan=3,sticky="w",padx=10,pady=12)

    def apply_resolution(self,event=None):
        name=self.resolution.get()
        if name in RESOLUTION_PRESETS:
            w,h=RESOLUTION_PRESETS[name]; self.width.set(str(w)); self.height.set(str(h))

    def pick_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Áudio","*.wav *.flac *.mp3 *.m4a *.aac *.ogg"),("Todos","*.*")])
        if p: self.audio.set(p)

    def pick_output(self):
        p=filedialog.asksaveasfilename(defaultextension=".mp4",filetypes=[("MP4","*.mp4"),("MKV","*.mkv"),("AVI","*.avi")])
        if p: self.output.set(p)

    def pick_lyrics(self):
        p=filedialog.askopenfilename(filetypes=[("Letra/legenda","*.srt *.vtt *.lrc *.txt"),("Todos","*.*")])
        if p: self.lyrics.set(p)

    def pick_media(self):
        files=filedialog.askopenfilenames(filetypes=[("Mídia","*.jpg *.jpeg *.png *.webp *.mp4 *.mov *.mkv *.avi *.webm"),("Todos","*.*")])
        if files: self.media=list(files); self.media_label.config(text=f"{len(self.media)} arquivo(s)")

    def clear_media(self):
        self.media=[]; self.media_label.config(text="Nenhuma mídia base")

    def _run(self,cmd:list[str]):
        self.log.delete("1.0","end"); self.log.insert("end","$ "+" ".join(cmd)+"\n\n")
        def worker():
            try:
                proc=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
                assert proc.stdout
                for line in proc.stdout:
                    self.after(0,self.log.insert,"end",line); self.after(0,self.log.see,"end")
                code=proc.wait(); self.after(0,lambda:messagebox.showinfo("SUBTERRA","Concluído." if code==0 else f"Processo terminou com código {code}."))
            except Exception as exc:
                self.after(0,lambda:messagebox.showerror("SUBTERRA",str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def run_diagnose(self):
        self._run([sys.executable,"subterra.py","diagnose","--output",str(ROOT/"hardware_report.json")])

    def run_render(self,preview:int|None=None):
        if not self.audio.get(): messagebox.showwarning("SUBTERRA","Selecione um arquivo de áudio."); return
        try:
            w=int(self.width.get()); h=int(self.height.get()); fps=float(self.fps.get()); scale=float(self.render_scale.get())
            if w<320 or h<180 or fps<=0 or not .3<=scale<=1.0: raise ValueError
        except ValueError:
            messagebox.showerror("SUBTERRA","Revise largura, altura, FPS e escala interna."); return
        output=Path(self.output.get())
        if preview:
            output=output.with_name(output.stem+"_preview"+output.suffix)
        output.parent.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,"subterra.py","render",self.audio.get(),str(output),"--width",str(w),"--height",str(h),
             "--fps",str(fps),"--seed",self.seed.get(),"--style",self.style.get(),"--filter",self.filter_name.get(),
             "--filter-intensity",f"{self.filter_intensity.get():.3f}","--edit-density",f"{self.edit_density.get():.3f}",
             "--render-scale",str(scale),"--audio-mode",self.audio_mode.get(),"--encoder",self.encoder.get(),
             "--strobe",f"{self.strobe.get():.3f}"]
        if not self.typography.get(): cmd.append("--no-typography")
        if self.lyrics.get(): cmd.extend(["--lyrics",self.lyrics.get()])
        seconds=preview or (float(self.preview_seconds.get()) if self.preview_seconds.get().strip() else None)
        if seconds: cmd.extend(["--preview-seconds",str(seconds)])
        for p in self.media: cmd.extend(["--media",p])
        self._run(cmd)


if __name__=="__main__": App().mainloop()
