import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np


#Install: pip install pymupdf opencv-python-headless tkinter
#Start with: python pdf_verifier.py
#
#
#

class PDFVerifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vérificateur de PDF")
        
        self.create_ui()
        
    def create_ui(self):
        self.load_button = tk.Button(self.root, text="Charger PDF", command=self.load_pdf)
        self.load_button.pack(pady=10)
        
        self.margin_label = tk.Label(self.root, text="Marges (haut, bas, gauche, droit) en mm :")
        self.margin_label.pack()
        self.margin_entry = tk.Entry(self.root)
        self.margin_entry.pack(pady=5)
        
        self.indentation_label = tk.Label(self.root, text="Indentation des sections et sous-sections en mm :")
        self.indentation_label.pack()
        self.indentation_entry = tk.Entry(self.root)
        self.indentation_entry.pack(pady=5)
        
        self.resolution_label = tk.Label(self.root, text="Résolution des figures (dpi) :")
        self.resolution_label.pack()
        self.resolution_entry = tk.Entry(self.root)
        self.resolution_entry.pack(pady=5)
        
        self.verify_button = tk.Button(self.root, text="Vérifier PDF", command=self.verify_pdf)
        self.verify_button.pack(pady=10)
        
        self.result_text = tk.Text(self.root, height=15, width=80)
        self.result_text.pack(pady=10)
        
    def load_pdf(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if self.file_path:
            messagebox.showinfo("Info", "PDF chargé avec succès.")
    
    def verify_pdf(self):
        if not hasattr(self, 'file_path'):
            messagebox.showerror("Erreur", "Veuillez charger un fichier PDF d'abord.")
            return
        
        margins = self.margin_entry.get().split(',')
        indentations = self.indentation_entry.get().split(',')
        resolution = self.resolution_entry.get()
        
        try:
            margins = [int(m) for m in margins]
            indentations = [int(i) for i in indentations]
            resolution = int(resolution)
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides.")
            return
        
        try:
            pdf_document = fitz.open(self.file_path)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Vérification des marges et des indentations...\n")
            
            # Vérification des marges et des indentations
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                issues = self.verify_margins_and_indentations(page, margins, indentations)
                for issue in issues:
                    self.result_text.insert(tk.END, f"Page {page_num + 1} : {issue}\n")
            
            self.result_text.insert(tk.END, "Vérification des figures...\n")
            
            # Vérification des figures
            for img_index, img in enumerate(pdf_document.get_images(full=True)):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                issue = self.verify_image_resolution(image, resolution)
                if issue:
                    self.result_text.insert(tk.END, f"Image {img_index + 1} : {issue}\n")
            
            self.result_text.insert(tk.END, "Vérification terminée.\n")
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")
    
    def verify_margins_and_indentations(self, page, margins, indentations):
        text_blocks = page.get_text("blocks")
        issues = []
        
        for block in text_blocks:
            x0, y0, x1, y1, _, _, _, _ = block
            if x0 < margins[2] or x1 > page.rect.width - margins[3]:
                issues.append(f"Texte hors des marges horizontales à la position ({x0}, {y0})")
            if y0 < margins[0] or y1 > page.rect.height - margins[1]:
                issues.append(f"Texte hors des marges verticales à la position ({x0}, {y0})")
            # Vérification des indentations (exemple simple)
            if x0 < indentations[0]:
                issues.append(f"Indentation insuffisante à la position ({x0}, {y0})")
        
        return issues
    
    def verify_image_resolution(self, image, required_dpi):
        height, width = image.shape[:2]
        dpi = 300  # DPI par défaut pour les PDF
        actual_dpi = (width / 8.5) * dpi  # Supposons une largeur de page de 8.5 pouces
        
        if actual_dpi < required_dpi:
            return f"Résolution de l'image insuffisante : {actual_dpi} dpi"
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFVerifierApp(root)
    root.mainloop()
