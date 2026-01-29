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
        self.materie = ["Matematica", "Logica", "Scienze"] 

    def fix_latex(self, testo):
        """Normalizza i caratteri Unicode e applica l'escape per LaTeX."""
        if not testo: return ""
        testo_norm = unicodedata.normalize('NFC', testo) 
        return testo_norm.replace("_", "\\_").replace("#", "\\#").replace("&", "\\&").replace("%", "\\%") 

    def natural_sort_key(self, s):
        """Chiave di ordinamento per gestire correttamente i numeri nelle stringhe."""
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))] 

    def processa_file(self, filepath):
        """Estrae il contenuto e la lettera della risposta dal file txt."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                linee = f.readlines()
            if not linee: return None
            
            ultima_riga = linee[-1].strip()
            match = re.search(r"Risposta\s+corretta:\s*([1-5])", ultima_riga, re.IGNORECASE)
            mappa = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"} 
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
            cartella = self.base_path / "quesiti" / f"Q - {m}" 
            if not cartella.exists(): continue
            
            files = sorted([f for f in cartella.glob("*.txt") if not f.name.startswith('.')], 
                           key=lambda x: self.natural_sort_key(x.name))
            
            for f in files:
                parti = [p.strip() for p in f.stem.split(" - ")] 
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
        # Gestione scelta singola materia o Tutte
        materie_da_processare = [materia_selezionata] if materia_selezionata else self.materie
        
        soluzioni_globali = [] 
        contatore_globale = 1

        for materia in materie_da_processare:
            if not db.get(materia): continue
            
            soluzioni_materia = [] 
            contatore_materia = 1 # Reset contatore per singola materia
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

            # Crea file soluzioni per singola materia
            self._scrivi_tabella_latex(path_sol, f"Soluzioni - {materia}", soluzioni_materia, "id_mat")

        # Se richiesto "Tutte", crea anche il file completo globale
        if not materia_selezionata:
            path_completo = output_dir / "soluzioni_completo.tex"
            self._scrivi_tabella_latex(path_completo, "Soluzioni Complete (Tutte le materie)", soluzioni_globali, "id_glob")
            
        return True

    def _scrivi_tabella_latex(self, path, titolo, dati, id_key):
        """Metodo di supporto per scrivere le tabelle LaTeX."""
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

        # Logica scrittura file .tex omessa per brevità, rimane identica alla tua versione
        # ... (Codice LaTeX del test)
        messagebox.showinfo("Successo", f"Test generato!")
        self.destroy()

# --- APP PRINCIPALE ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VTI Toolkit v2.3")
        self.geometry("500x600")
        self.repo_path = None
        
        ctk.CTkLabel(self, text="VTI - Gestione Quesiti", font=("Arial", 24, "bold")).pack(pady=20)
        self.btn_folder = ctk.CTkButton(self, text="📂 Seleziona Cartella VTI", command=self.select_folder)
        self.btn_folder.pack(pady=10)
        self.lbl_path = ctk.CTkLabel(self, text="Nessuna cartella selezionata", text_color="gray"); self.lbl_path.pack()
        
        # SPOSTATO QUI: Selettore ambito generazione
        ctk.CTkLabel(self, text="Ambito generazione eserciziario:").pack(pady=(20, 0))
        self.combo_materia = ctk.CTkComboBox(self, values=["Tutte le Materie", "Matematica", "Logica", "Scienze"], state="disabled")
        self.combo_materia.set("Tutte le Materie")
        self.combo_materia.pack(pady=5)

        self.btn_eser = ctk.CTkButton(self, text="📚 Genera Eserciziario", state="disabled", command=self.run_eser)
        self.btn_eser.pack(pady=20)
        self.btn_test = ctk.CTkButton(self, text="📝 Crea Test Personalizzato", state="disabled", fg_color="#3498db", command=self.open_test)
        self.btn_test.pack(pady=5)

    def select_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.repo_path = p
            self.lbl_path.configure(text=f"Cartella: {Path(p).name}", text_color="#3498db")
            self.btn_eser.configure(state="normal")
            self.btn_test.configure(state="normal")
            self.combo_materia.configure(state="normal") # Abilita il selettore

    def run_eser(self):
        core = VTICore(self.repo_path)
        scelta = self.combo_materia.get()
        # Se l'utente sceglie "Tutte le Materie", passiamo None
        materia_target = None if scelta == "Tutte le Materie" else scelta
        
        try:
            if core.genera_eserciziario(materia_target):
                msg = f"Eserciziario ({scelta}) generato con successo!"
                messagebox.showinfo("Successo", msg)
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {e}")

    def open_test(self):
        TestConfigWindow(self, VTICore(self.repo_path))

if __name__ == "__main__":
    App().mainloop()
