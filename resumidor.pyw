import os
import PyPDF2
from openai import OpenAI
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Inicializar el cliente de OpenAI con la clave API
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Función para extraer texto de un archivo PDF
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

# Función para resumir el texto utilizando OpenAI en el idioma seleccionado
def summarize_text(text, language):
    prompt = {
        "español": f"Por favor, resume el siguiente texto en español:\n\n{text}",
        "inglés": f"Please summarize the following text in English:\n\n{text}"
    }[language]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Función principal para seleccionar y procesar un archivo PDF
def process_pdf(language):
    pdf_path = filedialog.askopenfilename(
        title="Seleccionar PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )
    if pdf_path:
        try:
            pdf_text = extract_text_from_pdf(pdf_path)
            summary = summarize_text(pdf_text, language)
            
            # Guardar el resumen en un archivo de texto
            output_folder = 'output_summaries'
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            output_path = os.path.join(output_folder, f"{Path(pdf_path).stem}_summary_{language}.txt")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            messagebox.showinfo("Éxito", f"Resumen guardado en {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Se produjo un error: {e}")

# Crear la interfaz gráfica con Tkinter
def main():
    root = tk.Tk()
    root.title("PDF Summarizer")
    
    # Tamaño de la ventana ajustado
    root.geometry("400x250")
    
    # Etiqueta y Dropdown para seleccionar el idioma
    tk.Label(root, text="Seleccionar idioma para el resumen:").pack(pady=10)
    
    language_var = tk.StringVar(value="español")
    language_dropdown = ttk.Combobox(root, textvariable=language_var, values=["español", "inglés"], state="readonly")
    language_dropdown.pack(pady=10)
    
    # Botón para seleccionar el archivo PDF y generar el resumen
    tk.Button(root, text="Seleccionar PDF y Resumir", command=lambda: process_pdf(language_var.get()), padx=10, pady=5).pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    main()
