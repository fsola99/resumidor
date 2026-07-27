"""Summarise PDFs with Claude, from the command line or a small desktop window."""

import argparse
import os
import sys
import threading
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"

# Characters of PDF text per request. Well inside the model's context window, which
# leaves room for the prompt and keeps any single request affordable.
CHUNK_CHARS = 120_000

CHUNK_MAX_TOKENS = 2_000
SUMMARY_MAX_TOKENS = 4_000

LANGUAGES = {"es": "Spanish", "en": "English"}
DEFAULT_OUTPUT_DIR = "output_summaries"

SYSTEM_PROMPT = (
    "You summarise documents for a reader who will not see the original. "
    "Lead with what the document is and what it concludes, then the supporting "
    "detail that a reader would need. Keep specifics — names, figures, dates, "
    "decisions. Write prose, not a list of section titles."
)


class NoTextFound(Exception):
    """Raised when a PDF yields no extractable text."""


def extract_pages(pdf_path):
    """Return the text of each page of `pdf_path`, in order.

    Pages that yield no text come back as empty strings, so page numbering is kept.

    Raises NoTextFound if no page yields any text, which is what a scanned PDF with
    no OCR layer looks like.

    Raises OSError if the file cannot be read.
    """
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]

    if not any(pages):
        raise NoTextFound(
            f"{Path(pdf_path).name} holds no extractable text. Scanned PDFs need to be "
            "run through OCR first."
        )
    return pages


def chunk_pages(pages, limit=CHUNK_CHARS):
    """Return `pages` grouped into text blocks of at most `limit` characters.

    Groups break on page boundaries where possible; a single page longer than `limit`
    is split across blocks.
    """
    blocks = []
    current = []
    size = 0

    for page in pages:
        page = page.strip()
        if not page:
            continue

        while len(page) > limit:
            if current:
                blocks.append("\n\n".join(current))
                current, size = [], 0
            blocks.append(page[:limit])
            page = page[limit:]

        if size + len(page) > limit and current:
            blocks.append("\n\n".join(current))
            current, size = [], 0

        current.append(page)
        size += len(page)

    if current:
        blocks.append("\n\n".join(current))
    return blocks


def _ask(client, model, prompt, max_tokens):
    """Return Claude's reply to `prompt` as text."""
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


def summarise_block(client, block, language, model=DEFAULT_MODEL):
    """Return a summary of one block of text, written in `language`."""
    prompt = (
        f"Summarise the following text in {language}. It is one part of a longer "
        f"document, so summarise only what is here.\n\n{block}"
    )
    return _ask(client, model, prompt, CHUNK_MAX_TOKENS)


def combine_summaries(client, summaries, language, model=DEFAULT_MODEL):
    """Return one summary in `language` covering every summary in `summaries`."""
    joined = "\n\n---\n\n".join(
        f"Part {number}:\n{summary}" for number, summary in enumerate(summaries, start=1)
    )
    prompt = (
        f"The following are summaries of consecutive parts of a single document. "
        f"Write one coherent summary of the whole document in {language}, without "
        f"referring to the parts.\n\n{joined}"
    )
    return _ask(client, model, prompt, SUMMARY_MAX_TOKENS)


def summarise_pdf(client, pdf_path, language, model=DEFAULT_MODEL, on_progress=None):
    """Return a summary of `pdf_path` written in `language`.

    Long documents are summarised in parts and those summaries combined, so a PDF of
    any length can be handled. `on_progress` is called with a short status string as
    the work proceeds.

    Raises NoTextFound if the PDF yields no extractable text.
    """
    def report(message):
        if on_progress:
            on_progress(message)

    name = Path(pdf_path).name
    report(f"Reading {name}")
    blocks = chunk_pages(extract_pages(pdf_path))

    if len(blocks) == 1:
        report(f"Summarising {name}")
        return _ask(
            client,
            model,
            f"Summarise the following document in {language}.\n\n{blocks[0]}",
            SUMMARY_MAX_TOKENS,
        )

    summaries = []
    for number, block in enumerate(blocks, start=1):
        report(f"Summarising {name}, part {number} of {len(blocks)}")
        summaries.append(summarise_block(client, block, language, model))

    report(f"Combining {len(blocks)} parts of {name}")
    return combine_summaries(client, summaries, language, model)


def summary_path(pdf_path, language_code, output_dir):
    """Return where the summary of `pdf_path` is written."""
    return Path(output_dir) / f"{Path(pdf_path).stem}_summary_{language_code}.txt"


def write_summary(summary, pdf_path, language_code, output_dir):
    """Write `summary` alongside the other summaries and return the path written."""
    path = summary_path(pdf_path, language_code, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary, encoding="utf-8")
    return path


def build_client():
    """Return an Anthropic client built from ANTHROPIC_API_KEY.

    Raises SystemExit if the SDK is missing or the key is unset.
    """
    try:
        import anthropic
    except ImportError:
        raise SystemExit("The Anthropic SDK is needed: pip install anthropic")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "Set ANTHROPIC_API_KEY to your API key from https://console.anthropic.com/\n"
            "  Linux/macOS:  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  Windows:      setx ANTHROPIC_API_KEY sk-ant-..."
        )
    return anthropic.Anthropic()


def summarise_all(client, pdf_paths, language_code, output_dir, model, on_progress=None):
    """Summarise every PDF given and return the paths written and the failures.

    A PDF that cannot be summarised is recorded and the rest still run, so one bad
    file does not lose the batch.

    Returns a (written, failures) pair, where failures holds (path, reason) pairs.
    """
    language = LANGUAGES[language_code]
    written = []
    failures = []

    for pdf_path in pdf_paths:
        try:
            summary = summarise_pdf(client, pdf_path, language, model, on_progress)
            written.append(write_summary(summary, pdf_path, language_code, output_dir))
        except (NoTextFound, OSError) as error:
            failures.append((pdf_path, str(error)))
        except Exception as error:
            failures.append((pdf_path, f"{type(error).__name__}: {error}"))

    return written, failures


def run_gui(args):
    """Open the window and run until it is closed.

    Raises SystemExit with an explanation if Tkinter is unavailable.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        raise SystemExit(
            "Tkinter is part of the Python standard library but some Linux distributions "
            "package it separately. On Debian or Ubuntu: sudo apt install python3-tk"
        )

    root = tk.Tk()
    root.title("Resumidor")
    root.geometry("460x260")
    root.resizable(False, False)

    language_var = tk.StringVar(value=LANGUAGES[args.language])
    status_var = tk.StringVar(value="Choose one or more PDFs to summarise.")

    ttk.Label(root, text="Summary language:").pack(pady=(20, 6))
    ttk.Combobox(
        root, textvariable=language_var, values=list(LANGUAGES.values()), state="readonly"
    ).pack()

    choose_button = ttk.Button(root, text="Choose PDFs and summarise")
    choose_button.pack(pady=20)

    progress = ttk.Progressbar(root, mode="indeterminate", length=380)
    progress.pack()
    ttk.Label(root, textvariable=status_var, wraplength=420).pack(pady=14)

    def report(message):
        # Called from the worker thread, so the update is handed to the main loop.
        root.after(0, status_var.set, message)

    def finish(written, failures):
        progress.stop()
        choose_button.state(["!disabled"])
        status_var.set("Choose one or more PDFs to summarise.")

        if written:
            listing = "\n".join(str(path) for path in written)
            messagebox.showinfo("Finished", f"Wrote {len(written)} summaries:\n\n{listing}")
        if failures:
            listing = "\n\n".join(f"{Path(path).name}: {reason}" for path, reason in failures)
            messagebox.showerror("Some PDFs failed", listing)

    def start():
        pdf_paths = filedialog.askopenfilenames(
            title="Choose PDFs", filetypes=[("PDF files", "*.pdf")]
        )
        if not pdf_paths:
            return

        try:
            client = build_client()
        except SystemExit as error:
            messagebox.showerror("Not configured", str(error))
            return

        code = next(c for c, name in LANGUAGES.items() if name == language_var.get())
        choose_button.state(["disabled"])
        progress.start(12)

        def work():
            # Kept off the main thread so the window stays responsive during the calls.
            written, failures = summarise_all(
                client, pdf_paths, code, args.output_dir, args.model, report
            )
            root.after(0, finish, written, failures)

        threading.Thread(target=work, daemon=True).start()

    choose_button.configure(command=start)
    root.mainloop()


def run_cli(args):
    """Summarise the PDFs named on the command line and return the process exit code."""
    missing = [path for path in args.pdfs if not Path(path).is_file()]
    if missing:
        for path in missing:
            print(f"[x] No such file: {path}")
        return 1

    client = build_client()
    written, failures = summarise_all(
        client, args.pdfs, args.language, args.output_dir, args.model,
        on_progress=lambda message: print(f"    {message}"),
    )

    for path in written:
        print(f"[+] {path}")
    for path, reason in failures:
        print(f"[x] {Path(path).name}: {reason}")

    return 1 if failures else 0


def parse_args(argv=None):
    """Return the parsed command line."""
    parser = argparse.ArgumentParser(
        description="Summarise PDFs with Claude, however long they are.",
        epilog="Run with no PDFs to open the window instead.",
    )
    parser.add_argument("pdfs", nargs="*", help="PDFs to summarise")
    parser.add_argument(
        "-l", "--language", choices=sorted(LANGUAGES), default="es",
        help="language to write the summary in (default: %(default)s)",
    )
    parser.add_argument(
        "-o", "--output-dir", default=DEFAULT_OUTPUT_DIR,
        help="folder to write summaries into (default: %(default)s)",
    )
    parser.add_argument(
        "-m", "--model", default=DEFAULT_MODEL, help="Claude model (default: %(default)s)"
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Run the command line if PDFs were named, otherwise open the window."""
    args = parse_args(argv)
    if args.pdfs:
        return run_cli(args)
    run_gui(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
