import os
import re
import random
import unicodedata
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

class VTICore:
    """Gestisce la logica di elaborazione dei file e generazione LaTeX."""
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.materie = ["Matematica", "Logica", "Scienze"] #

    def fix_latex(self, testo):
        """Normalizza i caratteri Unicode e applica l'escape per LaTeX."""
        if not testo: return ""
        testo_norm = unicodedata.normalize('NFC', testo) #
        return testo_norm.replace("_", "\\_").replace("#", "\\#").replace("&", "\\&").replace("%", "\\%") #

    def natural_sort_key(self, s):
        """Chiave di ordinamento per gestire correttamente i numeri nelle stringhe."""
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))] #

    def processa_file(self, filepath):
        """Estrae il contenuto e la lettera della risposta dal file txt."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                linee = f.readlines()
            if not linee: return None
            
            ultima_riga = linee[-1].strip()
            # Cerca "Risposta corretta: X" dove X è tra 1 e 5
            match = re.search(r"Risposta\s+corretta:\s*([1-5])", ultima_riga, re.IGNORECASE)
            mappa = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"} #
            lettera = mappa.get(match.group(1), "?") if match else "?"
            
            contenuto = "".join(linee[:-1]).strip()
            return {"testo": unicodedata.normalize('NFC', contenuto), "risp": lettera}
        except Exception as e:
            print(f"Errore nel file {filepath}: {e}")
            return None

    def get_struttura_quesiti(self):
        """Mappa i file disponibili per ogni materia e argomento."""
        db = {m: {} for m in self.materie}
        for m in self.materie:
            cartella = self.base_path / "quesiti" / f"Q - {m}" #
            if not cartella.exists(): continue
            
            # Recupera tutti i file txt non nascosti
            files = sorted([f for f in cartella.glob("*.txt") if not f.name.startswith('.')], 
                           key=lambda x: self.natural_sort_key(x.name))
            
            for f in files:
                parti = [p.strip() for p in f.stem.split(" - ")] #
                if len(parti) < 2: continue
                argomento = parti[1]
                if argomento not in db[m]: db[m][argomento] = []
                db[m][argomento].append(f)
        return db

   def genera_eserciziario(self, materia_selezionata=None):
        """Genera i file .tex per l'eserciziario (singola materia e/o completo)."""
        output_dir = self.base_path / "eserciziario"
        output_dir.mkdir(exist_ok=True)
        
        db = self.get_struttura_quesiti()
        materie_da_processare = [materia_selezionata] if materia_selezionata else self.materie
        
        soluzioni_globali = [] # Lista per il file completo
        contatore_globale = 1

        for materia in materie_da_processare:
            if not db.get(materia): continue
            
            soluzioni_materia = [] 
            contatore_materia = 1 
            path_out = output_dir / f"quesiti_{materia.lower()}.tex"
            path_sol = output_dir / f"soluzioni_{materia.lower()}.tex" 
            
            with open(path_out, 'w', encoding='utf-8') as f_out:
                for argomento in sorted(db[materia].keys()):
                    f_out.write(f"\\subsection{{{self.fix_latex(argomento)}}}\n")
                    f_out.write("\\begin{multicols}{2}\n\\begin{itemize}[leftmargin=*]\n")
                    
                    files_arg = sorted(db[materia][argomento], key=lambda x: self.natural_sort_key(x.name))
                    for f_path in files_arg:
                        dati = self.processa_file(f_path)
                        if dati:
                            f_out.write(f"{dati['testo']}\n\n")
                            parti = [p.strip() for p in f_path.stem.split(" - ")]
                            nome_quesito = re.sub(r"\s*#\d+", "", parti[2]) if len(parti) > 2 else f_path.stem
                            
                            item = {
                                "id_mat": contatore_materia,
                                "id_glob": contatore_globale,
                                "materia": materia,
                                "arg": argomento,
                                "nome": nome_quesito,
                                "risp": dati['risp']
                            }
                            soluzioni_materia.append(item)
                            soluzioni_globali.append(item)
                            contatore_materia += 1
                            contatore_globale += 1
                            
                    f_out.write("\\end{itemize}\n\\end{multicols}\n\\newpage\n\n")

            # Scrittura file soluzioni per materia (es. soluzioni_matematica.tex)
            self._scrivi_tabella_latex(path_sol, f"Soluzioni - {materia}", soluzioni_materia, "id_mat")

        # Se l'utente ha scelto "Tutte", genera anche il file completo
        if not materia_selezionata:
            path_completo = output_dir / "soluzioni_completo.tex"
            self._scrivi_tabella_latex(path_completo, "Soluzioni Complete (Tutte le materie)", soluzioni_globali, "id_glob")
            
        return True

    def _scrivi_tabella_latex(self, path, titolo, dati, id_key):
        """Metodo di supporto per non ripetere il codice delle tabelle LaTeX."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"\\section{{{titolo}}}\n")
            f.write("\\begin{longtable}{|p{1cm}|p{4cm}|p{8.5cm}|p{1cm}|}\n\\hline \n")
            f.write("\\rowcolor{headercolor} \\textbf{N.} & \\textbf{Argomento} & \\textbf{Nome Quesito} & \\textbf{Risp.} \\\\ \\hline\n")
            f.write("\\endfirsthead\n\\hline \n\\rowcolor{headercolor} \\textbf{N.} & \\textbf{Argomento} & \\textbf{Nome Quesito} & \\textbf{Risp.} \\\\ \\hline\n\\endhead\n")
            
            for s in dati:
                arg_safe = self.fix_latex(s['arg'])
                nome_safe = self.fix_latex(s['nome'])
                f.write(f"{s[id_key]} & {arg_safe} & {nome_safe} & \\centering \\textbf{{{s['risp']}}} \\tabularnewline \\hline\n")
            
            f.write("\\end{longtable}\n\\newpage\n")

# --- FINESTRE UI ---

class TestConfigWindow(ctk.CTkToplevel):
    def __init__(self, parent, core):
        super().__init__(parent)
        self.title("Configura Nuovo Test")
        self.geometry("600x750")
        self.core = core
        self.db = core.get_struttura_quesiti()
        self.entries = {}
        self.setup_ui()
        ctk.CTkLabel(self, text="Seleziona ambito generazione:").pack(pady=(15, 0))
        self.combo_materia = ctk.CTkComboBox(self, values=["Tutte", "Matematica", "Logica", "Scienze"])
        self.combo_materia.set("Tutte")
        self.combo_materia.pack(pady=5)

    def setup_ui(self):
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(header, text="Titolo Test:").grid(row=0, column=0, padx=5)
        self.ent_titolo = ctk.CTkEntry(header, width=200); self.ent_titolo.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(header, text="Data:").grid(row=0, column=2, padx=5)
        self.ent_data = ctk.CTkEntry(header, width=100); self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y")); self.ent_data.grid(row=0, column=3, padx=5)

        self.scroll = ctk.CTkScrollableFrame(self, label_text="Seleziona numero quesiti")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        for mat in self.core.materie:
            if not self.db[mat]: continue
            ctk.CTkLabel(self.scroll, text=mat.upper(), font=("Arial", 14, "bold"), text_color="#3498db").pack(pady=10, anchor="w")
            for arg in sorted(self.db[mat].keys()):
                f = ctk.CTkFrame(self.scroll, fg_color="transparent"); f.pack(fill="x")
                n = len(self.db[mat][arg])
                ctk.CTkLabel(f, text=f"• {arg} (Disp: {n})", width=300, anchor="w").pack(side="left")
                e = ctk.CTkEntry(f, width=50); e.insert(0, "0"); e.pack(side="right", padx=10)
                self.entries[(mat, arg)] = (e, n)

        ctk.CTkButton(self, text="GENERA TEST PDF (LATEX)", fg_color="#27ae60", command=self.genera_azione).pack(pady=20)

    def genera_azione(self):
        titolo = self.ent_titolo.get() or "Test_Senza_Titolo"
        data_t = self.ent_data.get()
        quesiti_scelti = {m: [] for m in self.core.materie}
        soluzioni_data = []
        global_count = 1

        for (mat, arg), (widget, n_disp) in self.entries.items():
            try:
                n_req = int(widget.get())
                if n_req > 0:
                    selected = random.sample(self.db[mat][arg], min(n_req, n_disp))
                    for f_path in selected:
                        dati = self.core.processa_file(f_path)
                        if dati:
                            quesiti_scelti[mat].append(dati['testo'])
                            parti = f_path.stem.split(" - ")
                            nome_q = re.sub(r"\s*#\d+", "", parti[2]) if len(parti) > 2 else f_path.stem
                            soluzioni_data.append({"n": global_count, "mat": mat, "arg": arg, "nome": nome_q, "risp": dati['risp']})
                            global_count += 1
            except: continue

        if global_count == 1: return messagebox.showwarning("Errore", "Seleziona almeno un quesito!")
        
        output_dir = self.core.base_path / "test"
        output_dir.mkdir(exist_ok=True)
        out_path = output_dir / f"Test_{titolo.replace(' ', '_')}.tex"

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(r"""\documentclass[20pt, a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[italian]{babel}
\usepackage[table]{xcolor}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, calc, patterns, decorations.pathmorphing}
\usepackage{amsmath, amssymb, amsthm, empheq, siunitx, textcomp}
\usepackage{array, caption, longtable, multicol, framed, geometry}
\usepackage{enumitem, tasks, fancyhdr}

\geometry{a4paper, left=20mm, right=20mm, top=20mm, bottom=20mm}
\definecolor{headercolor}{RGB}{200,200,200}
\newcounter{quesito}
\setcounter{quesito}{0}
\newcommand{\nuovoquesito}{\stepcounter{quesito}\textbf{Domanda \arabic{quesito}.}}

\newcommand{\itemdomanda}[2]{%
    \item \begin{minipage}[t]{\linewidth}
        \nuovoquesito \\ #1
        \begin{enumerate}[label=(\Alph*), nosep, leftmargin=*]
            #2
        \end{enumerate}
    \end{minipage}
    \vspace{10pt} 
}

\pagestyle{fancy}
\fancyhead[L]{Verso il Test di Ingegneria}
\fancyhead[R]{\thepage}
\fancyfoot{}
\renewcommand{\headrulewidth}{0.4pt}

\begin{document}
""") #
            f.write(f"\\noindent {{\\huge \\textbf{{{titolo}}}}} \\hfill {{\\large Data: {data_t}}} \\par \\vspace{{1cm}}\n")

            materia_scritta = False
            for m in self.core.materie:
                if not quesiti_scelti[m]: continue
                if materia_scritta: f.write("\\newpage\n")
                f.write(f"\\section*{{Sezione: {m}}}\n\\begin{{multicols}}{{2}}\n\\begin{{itemize}}[leftmargin=*]\n")
                for q in quesiti_scelti[m]: f.write(f"{q}\n")
                f.write("\\end{itemize}\n\\end{multicols}\n")
                materia_scritta = True

            f.write(f"\\newpage \\section*{{Soluzioni del Test - {data_t}}}\n")
            f.write("\\begin{longtable}{|p{0.08\\textwidth}|p{0.15\\textwidth}|p{0.59\\textwidth}|p{0.08\\textwidth}|}\n\\hline\n") #
            f.write("\\rowcolor{headercolor} \\textbf{N.} & \\textbf{Materia} & \\textbf{Argomento - Quesito} & \\textbf{Risp.} \\\\ \\hline\n")
            for s in soluzioni_data:
                desc = f"{s['arg']} - {s['nome']}"
                f.write(f"{s['n']} & {s['mat']} & {self.core.fix_latex(desc)} & \\centering \\textbf{{{s['risp']}}} \\tabularnewline \\hline\n")
            f.write("\\end{longtable}\n\\end{document}")

        messagebox.showinfo("Successo", f"Test generato: {out_path.name}")
        self.destroy()

# --- APP PRINCIPALE ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VTI Toolkit v2.3")
        self.geometry("500x500")
        self.repo_path = None
        
        ctk.CTkLabel(self, text="VTI - Gestione Quesiti", font=("Arial", 24, "bold")).pack(pady=20)
        self.btn_folder = ctk.CTkButton(self, text="📂 Seleziona Cartella VTI", command=self.select_folder)
        self.btn_folder.pack(pady=10)
        self.lbl_path = ctk.CTkLabel(self, text="Nessuna cartella selezionata", text_color="gray"); self.lbl_path.pack()
        
        self.btn_eser = ctk.CTkButton(self, text="📚 Genera Eserciziario Completo", state="disabled", command=self.run_eser)
        self.btn_eser.pack(pady=20)
        self.btn_test = ctk.CTkButton(self, text="📝 Crea Test Personalizzato", state="disabled", fg_color="#3498db", command=self.open_test)
        self.btn_test.pack(pady=5)

    def select_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.repo_path = p
            self.lbl_path.configure(text=f"Cartella: {Path(p).name}", text_color="#3498db")
            self.btn_eser.configure(state="normal"); self.btn_test.configure(state="normal")

    def run_eser(self):
        core = VTICore(self.repo_path)
        scelta = self.combo_materia.get()
        materia_target = None if scelta == "Tutte" else scelta #
        
        try:
            if core.genera_eserciziario(materia_target):
                msg = f"Generazione ({scelta}) completata con successo!"
                messagebox.showinfo("Successo", msg)
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {e}")

    def open_test(self):
        TestConfigWindow(self, VTICore(self.repo_path))

if __name__ == "__main__":
    App().mainloop()
