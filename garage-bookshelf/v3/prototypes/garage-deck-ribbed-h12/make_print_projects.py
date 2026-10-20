"""Prepare X2D/PLA Bambu Studio projects and run an offline slicing check.

This never sends a print job or exports printer-ready G-code to the project.
"""
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = Path("/Applications/BambuStudio.app/Contents")
CLI = APP / "MacOS/BambuStudio"
PRESETS = APP / "Resources/profiles/BBL"
MACHINE = PRESETS / "machine/Bambu Lab X2D 0.4 nozzle.json"
STANDARD = PRESETS / "process/0.20mm Standard @BBL X2D.json"
FILAMENT = PRESETS / "filament/Bambu PLA Basic @BBL X2D 0.4 nozzle.json"


def process_profile():
    profile = json.loads(STANDARD.read_text())
    # Preserve the installed, named preset so Bambu Studio recognizes the project.
    # These four values are explicit overrides and remain in the saved 3MF.
    profile.update(wall_loops="4", sparse_infill_density="25%",
                   brim_width="4", brim_type="auto_brim", enable_support="0")
    path = ROOT / "X2D-PLA-process.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
    return path


def run_cli(profile, args, datadir):
    datadir.mkdir(parents=True, exist_ok=True)
    command = [str(CLI), "--debug", "2", "--datadir", str(datadir),
               "--load-settings", f"{MACHINE};{profile}",
               "--load-filaments", str(FILAMENT), "--orient", "0",
               "--arrange", "1", *map(str, args)]
    result = subprocess.run(command, text=True, capture_output=True, cwd=datadir)
    if result.returncode:
        raise RuntimeError(f"Bambu Studio failed ({result.returncode}): {result.stdout}\n{result.stderr}")
    return result


def read_settings(project):
    with zipfile.ZipFile(project) as package:
        data = json.loads(package.read("Metadata/project_settings.config"))
    keys = ("printer_model", "nozzle_diameter", "wall_loops",
            "sparse_infill_density", "brim_width", "brim_type", "enable_support")
    result = {key: data.get(key) for key in keys}
    assert result["printer_model"] == "Bambu Lab X2D"
    assert result["wall_loops"] == "4"
    assert result["sparse_infill_density"] == "25%"
    assert result["brim_width"] == "4"
    assert result["enable_support"] == "0"
    return result


def main():
    if not CLI.exists():
        raise RuntimeError("Bambu Studio CLI is not installed at the expected location")
    profile = process_profile()
    output = ROOT / "bambu-projects"
    output.mkdir(exist_ok=True)
    source = ROOT / "print-stl"
    plates = {
        "01-reinforced-deck-left": ["reinforced_deck_left.stl"],
        "02-reinforced-deck-right": ["reinforced_deck_right.stl"],
        "03-splices-and-fixtures": ["original_centre_bridge.stl", "front_splice.stl",
                                     "rear_splice.stl", *(["test_support_1.stl"] * 4)],
    }
    reports = []
    with tempfile.TemporaryDirectory(prefix="ribbed-deck-bambu-") as scratch:
        temporary = Path(scratch)
        for name, files in plates.items():
            models = [source / file for file in files]
            project = output / f"{name}.3mf"
            run_cli(profile, ["--export-3mf", project, *models], temporary / "settings")
            settings = read_settings(project)
            with zipfile.ZipFile(project) as package:
                (output / f"{name}.png").write_bytes(package.read("Metadata/plate_1.png"))
            sliced = temporary / name
            sliced.mkdir()
            run_cli(profile, ["--outputdir", sliced, "--slice", "0", *models],
                    temporary / "settings")
            result = json.loads((sliced / "result.json").read_text())
            if result.get("return_code") != 0 or len(result.get("sliced_plates", [])) != 1:
                raise RuntimeError(f"Slicing failed for {name}: {result}")
            plate = result["sliced_plates"][0]
            if plate.get("warning_message") or len(plate.get("objects", [])) != len(models):
                raise RuntimeError(f"Unexpected slicer warning/object count for {name}: {plate}")
            reports.append({"project": str(project.relative_to(ROOT)),
                            "input_files": files, "object_count": len(plate["objects"]),
                            "settings": settings, "slice_status": "passed",
                            "slicer_warnings": [],
                            "estimated_seconds": round(plate["total_predication"])})
    report = {"status": "passed", "bambu_studio": "02.08.02.61",
              "printer": "Bambu Lab X2D, 0.4 mm nozzle", "projects": reports,
              "gcode_delivered": False, "physical_print_completed": False}
    (ROOT / "slicer-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
