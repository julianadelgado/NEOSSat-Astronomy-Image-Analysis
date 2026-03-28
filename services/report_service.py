from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ReportTable:
    headers: List[str]
    rows: List[List[str]]


@dataclass
class ReportSection:
    title: str
    content: str = ""
    images: List[Path] = field(default_factory=list)
    tables: List[ReportTable] = field(default_factory=list)
    subsections: List["ReportSection"] = field(default_factory=list)


@dataclass
class ReportData:
    task_name: str
    sections: List[ReportSection] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class ReportService:
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir

    def generate(self, data: ReportData, filename: Optional[str] = None) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            ts = data.timestamp.strftime("%Y%m%d_%H%M%S")
            slug = data.task_name.lower().replace(" ", "_")
            filename = f"{slug}_report_{ts}.md"

        output_path = self.reports_dir / filename

        lines = [
            f"# {data.task_name} Report",
            f"Generated at: {data.timestamp.isoformat()}",
            "",
        ]

        for section in data.sections:
            lines.extend(self._render_section(section, level=2))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"Report generated: {output_path.absolute()}")
        return output_path

    def _render_section(self, section: ReportSection, level: int) -> List[str]:
        heading = "#" * level
        lines = [f"{heading} {section.title}", ""]

        if section.content:
            lines += [section.content, ""]

        for image in section.images:
            lines += [f"![{image.stem}]({image.absolute().as_posix()})", ""]

        for table in section.tables:
            lines.append("| " + " | ".join(table.headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(table.headers)) + " |")
            for row in table.rows:
                lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
            lines.append("")

        for subsection in section.subsections:
            lines.extend(self._render_section(subsection, level + 1))

        lines += ["---", ""]
        return lines

    #TODO PDF generation method