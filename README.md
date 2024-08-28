# Resumidor

Este script es una herramienta que permite extraer texto de archivos PDF y generar un resumen utilizando la API de OpenAI. El resumen puede generarse en español o en inglés, según la preferencia del usuario. La aplicación cuenta con una interfaz gráfica sencilla creada con Tkinter.

## Requisitos

- Python 3.x
- [OpenAI Python Client](https://pypi.org/project/openai/)
- [PyPDF2](https://pypi.org/project/PyPDF2/)
- Tkinter (incluido con Python estándar)

## Instalación

1. Clona este repositorio o descarga el archivo ZIP.

2. Instala las dependencias necesarias usando `pip`:

    ```bash
    pip install openai PyPDF2
    ```

3. Configura tu clave API de OpenAI. Puedes hacerlo estableciendo una variable de entorno:

    ```bash
    export OPENAI_API_KEY='tu_clave_api'
    ```

    O añadiendo la clave directamente en tu código (no recomendado para producción).

## Uso

1. Ejecuta el script `pdf_summarizer.py`:

    ```bash
    python pdf_summarizer.py
    ```

2. Aparecerá una ventana con una interfaz gráfica que te permitirá:

    - Seleccionar el idioma en el que deseas que se genere el resumen (español o inglés).
    - Seleccionar un archivo PDF desde tu equipo.
    - El script extraerá el texto del PDF y generará un resumen utilizando la API de OpenAI.
    - El resumen se guardará en la carpeta `output_summaries` con un nombre que incluye el idioma seleccionado.

## Estructura del Proyecto

- `pdf_summarizer.py`: Contiene el código principal del script.
- `output_summaries/`: Carpeta donde se almacenan los resúmenes generados.

## Contribuciones

Las contribuciones son bienvenidas. Si encuentras algún problema o tienes una mejora, no dudes en abrir un issue o enviar un pull request.
