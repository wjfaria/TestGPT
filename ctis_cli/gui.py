from __future__ import annotations

import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, ttk
from tkinter import filedialog, messagebox

from ctis_cli.scraper import CTISScraper


class CTISGui:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("CTIS Trial Document Downloader")

        self.keywords_var = StringVar()
        self.therapeutic_area_var = StringVar()
        self.output_dir_var = StringVar(value=str(Path("data").resolve()))
        self.max_trials_var = StringVar(value="200")
        self.dry_run_var = BooleanVar(value=False)
        self.insecure_var = BooleanVar(value=False)
        self.status_var = StringVar(value="Ready")

        self._build_layout()

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(main, text="Keywords (comma-separated)").grid(row=0, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.keywords_var, width=50).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(main, text="Therapeutic area (optional)").grid(row=2, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.therapeutic_area_var, width=50).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(main, text="Output folder").grid(row=4, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.output_dir_var, width=50).grid(
            row=5, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(main, text="Browse", command=self._browse_output).grid(
            row=5, column=1, sticky="e", padx=(8, 0)
        )

        ttk.Label(main, text="Max trials per run").grid(row=6, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.max_trials_var, width=10).grid(
            row=7, column=0, sticky="w", pady=(0, 8)
        )

        ttk.Checkbutton(main, text="Dry run (no downloads)", variable=self.dry_run_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        ttk.Checkbutton(
            main,
            text="Disable SSL verification (insecure)",
            variable=self.insecure_var,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Button(main, text="Start", command=self._start_download).grid(
            row=10, column=0, sticky="w"
        )
        ttk.Label(main, textvariable=self.status_var).grid(row=10, column=1, sticky="e")

        main.columnconfigure(0, weight=1)

    def _browse_output(self) -> None:
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def _start_download(self) -> None:
        keywords = [entry.strip() for entry in self.keywords_var.get().split(",") if entry.strip()]
        if not keywords:
            messagebox.showerror("Missing keywords", "Please enter at least one keyword.")
            return

        try:
            max_trials = int(self.max_trials_var.get())
        except ValueError:
            messagebox.showerror("Invalid max trials", "Max trials must be an integer.")
            return

        output_dir = Path(self.output_dir_var.get()).expanduser()
        therapeutic_area = self.therapeutic_area_var.get().strip()
        dry_run = self.dry_run_var.get()
        insecure = self.insecure_var.get()

        self.status_var.set("Running...")
        thread = threading.Thread(
            target=self._run_download,
            args=(keywords, therapeutic_area, output_dir, max_trials, dry_run, insecure),
            daemon=True,
        )
        thread.start()

    def _run_download(
        self,
        keywords: list[str],
        therapeutic_area: str,
        output_dir: Path,
        max_trials: int,
        dry_run: bool,
        insecure: bool,
    ) -> None:
        try:
            fields: dict[str, str] = {}
            if therapeutic_area:
                fields["therapeutic_area"] = therapeutic_area

            scraper = CTISScraper(
                base_url="https://euclinicaltrials.eu/ctis-public",
                user_agent="CTIS-Document-Downloader/1.0",
                verify_ssl=not insecure,
            )

            trials_processed = 0
            page = 1
            while trials_processed < max_trials:
                trials = scraper.search_trials(keywords, fields, page=page)
                if not trials:
                    break
                for trial in trials:
                    if trials_processed >= max_trials:
                        break
                    documents = scraper.fetch_trial_documents(trial.url)
                    scraper.download_documents(
                        trial,
                        documents,
                        output_dir=output_dir,
                        metadata_path=output_dir / "metadata.jsonl",
                        dry_run=dry_run,
                    )
                    trials_processed += 1
                page += 1

            self._set_status("Completed")
            messagebox.showinfo("Done", f"Processed {trials_processed} trials.")
        except Exception as exc:  # pragma: no cover - GUI feedback
            self._set_status("Failed")
            messagebox.showerror("Error", str(exc))

    def _set_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_var.set(message))


def main() -> None:
    root = Tk()
    CTISGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
