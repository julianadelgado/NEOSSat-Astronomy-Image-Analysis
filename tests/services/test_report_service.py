import pytest

from services.report_service import ReportData, ReportSection, ReportTable


def test_generate_report_creates_file(report_service):
    data = ReportData(task_name="Test Task")
    output_path = report_service.generate(data)
    assert output_path.exists()
    assert output_path.with_suffix(".pdf").exists()
    assert output_path.parent == report_service.reports_dir


def test_generate_report_auto_filename_format(report_service):
    data = ReportData(task_name="Star Detection")
    output_path = report_service.generate(data)
    assert output_path.name.startswith("star_detection_report_")
    assert output_path.suffix == ".md"


def test_generate_report_contains_task_name(report_service):
    data = ReportData(task_name="Star Detection")
    output_path = report_service.generate(data)
    assert "Star Detection" in output_path.read_text()


def test_generate_report_creates_reports_dir_if_missing(tmp_path):
    reports_dir = tmp_path / "nested" / "reports"
    from services.report_service import ReportService

    service = ReportService(reports_dir=reports_dir)
    service.generate(ReportData(task_name="Test Task"))
    assert reports_dir.exists()


def test_generate_stars_report_with_section_content(report_service):
    data = ReportData(
        task_name="Star Detection",
        sections=[ReportSection(title="Results", content="Stars detected: 5")],
    )
    content = report_service.generate(data).read_text()
    assert "Results" in content
    assert "Stars detected: 5" in content


def test_generate_report_with_image(
    report_service, report_data_with_image, sample_image
):
    output_path = report_service.generate(report_data_with_image)
    assert sample_image.stem in output_path.read_text()


def test_generate_streak_report_with_table(report_service):
    table = ReportTable(headers=["Name", "Confidence"], rows=[["Satellite A", "0.95"]])
    data = ReportData(
        task_name="Streak Detection",
        sections=[ReportSection(title="Results", tables=[table])],
    )
    content = report_service.generate(data).read_text()
    assert "Name" in content
    assert "Satellite A" in content


def test_generate_streak_report_with_subsection(report_service):
    data = ReportData(
        task_name="Streak Detection",
        sections=[
            ReportSection(
                title="File: image1",
                subsections=[
                    ReportSection(title="Detection 1", content="Confidence: 0.9")
                ],
            )
        ],
    )
    content = report_service.generate(data).read_text()
    assert "### Detection 1" in content
    assert "Confidence: 0.9" in content


def test_generate_report_empty_sections(report_service):
    data = ReportData(task_name="Test Task", sections=[])
    output_path = report_service.generate(data)
    assert output_path.exists()
    assert output_path.with_suffix(".pdf").exists()


def test_generate_image_stacking_report_with_section_content(report_service):
    data = ReportData(
        task_name="Image Stacking",
        sections=[ReportSection(title="Results", content="Images stacked: 10")],
    )
    content = report_service.generate(data).read_text()
    assert "Results" in content
    assert "Images stacked: 10" in content


def test_generate_report_failed(report_service, monkeypatch):
    def bad_open(*_, **__):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", bad_open)
    with pytest.raises(OSError, match="disk full"):
        report_service.generate(ReportData(task_name="Test Task"))
