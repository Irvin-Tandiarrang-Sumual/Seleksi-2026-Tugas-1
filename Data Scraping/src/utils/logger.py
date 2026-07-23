from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, output_dir: str = "logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        self.log_file_path = self.output_dir / f"scraping_{timestamp}.log"

        self._log_file = open(self.log_file_path, "a", encoding="utf-8")

        self._write_header(f"SCRAPING LOG STARTED AT {now.isoformat()}")

    def info(self, message: str, course_code: str = ""):
        self._log("INFO", message, course_code)

    def success(self, message: str, course_code: str = ""):
        self._log("SUCCESS", message, course_code)

    def warning(self, message: str, course_code: str = ""):
        self._log("WARN", message, course_code)

    def error(self, message: str, course_code: str = ""):
        self._log("ERROR", message, course_code)

    def close(self):
        if not self._log_file.closed:
            self._log_file.close()

        print("\n[INFO] Log files successfully saved:")
        print(f"  - {self.log_file_path}")

    def _write_header(self, text: str):
        divider = "=" * 80
        self._write_to_file_without_timestamp_per_row(f"{divider}\n{text}\n{divider}")

    def _write_to_file_without_timestamp_per_row(self, message: str):
        self._log_file.write(f"{message}\n")
        self._log_file.flush()

    def _log(self, level: str, message: str, course_code: str = ""):
        timestamp = datetime.now().isoformat()
        prefix = f"[{course_code}] " if course_code else ""
        level_tag = f"[{level:^7}]"
        formatted_msg = f"{level_tag} {prefix}{message}"

        self._write_to_terminal(formatted_msg)
        self._write_to_file_without_timestamp_per_row(f"[{timestamp}] {formatted_msg}")

    def _write_to_terminal(self, formatted_message: str):
        print(formatted_message)
