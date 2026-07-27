# Resumidor

Summarises PDFs with Claude — from the command line or a small desktop window — and
writes each summary to a text file, in **Spanish or English**.

The point is documents that are too long to read and too long to paste into a chat
window: a 60-page report is summarised in parts, and those summaries are then combined
into one, so length is not a limit.

## Install

```bash
pip install -r requirements.txt
```

Then set your API key from [console.anthropic.com](https://console.anthropic.com/):

```bash
export ANTHROPIC_API_KEY=sk-ant-...     # Linux/macOS
setx ANTHROPIC_API_KEY sk-ant-...       # Windows
```

The key is only ever read from the environment, so there is nothing to paste into the
script and nothing to accidentally commit.

## Usage

Name one or more PDFs to run on the command line:

```bash
python resumidor.py report.pdf                    # summary in Spanish
python resumidor.py report.pdf --language en      # in English
python resumidor.py *.pdf --output-dir summaries
```

Run it with no PDFs and it opens a window instead — pick a language, choose files, and
it reports each one as it goes:

```bash
python resumidor.py
```

| Argument | Default | What it does |
|---|---|---|
| `pdfs` | *(none)* | PDFs to summarise. With none given, the window opens. |
| `-l`, `--language` | `es` | Language to write the summary in: `es` or `en`. |
| `-o`, `--output-dir` | `output_summaries` | Folder to write summaries into. |
| `-m`, `--model` | `claude-sonnet-5` | Claude model to use. |

Each summary is written to `<output-dir>/<pdf name>_summary_<language>.txt`.

## How long documents are handled

Text is extracted per page and grouped into blocks of at most 120,000 characters,
breaking on page boundaries. One block is summarised in a single request; several
blocks are each summarised and those summaries then combined into one, so the model
never receives more than it can hold and a long PDF costs a predictable number of
requests.

A 60-page report of around 258,000 characters becomes three blocks, so four requests.

## What it does when things go wrong

- A **scanned PDF with no OCR layer** yields no text. Rather than sending an empty
  prompt and getting a summary of nothing, it says so and names the file.
- In a **batch**, one unreadable or failing PDF is reported at the end and the rest
  still run.
- A **missing API key** prints the variable to set and the command to set it.
- On Linux, a **missing Tkinter** names the package to install — the command line
  works regardless.

## Requirements

- Python 3.9+
- [anthropic](https://pypi.org/project/anthropic/) and [pypdf](https://pypi.org/project/pypdf/)
- Tkinter for the window, which ships with Python on Windows and macOS
  (`sudo apt install python3-tk` on Debian or Ubuntu)
