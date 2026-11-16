"""Persistent storage for the safety moment library shipped with the app."""
import json
import shutil
from pathlib import Path


def prepare_library(storage: Path, bundled: Path) -> Path:
    destination = storage / 'safety_moments'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = destination / 'manifest.json'
    # Seed only once: subsequent deployments must not overwrite uploads or
    # restore materials intentionally removed by an administrator.
    if not manifest.exists():
        source_manifest = bundled / 'manifest.json'
        content = source_manifest.read_text(encoding='utf-8') if source_manifest.exists() else '[]'
        json.loads(content)  # Do not turn a damaged legacy manifest into data loss.
        if bundled.exists():
            for source in bundled.iterdir():
                if source.is_file() and source.name != 'manifest.json':
                    target = destination / source.name
                    if not target.exists():
                        shutil.copy2(source, target)
        # Publish only after every legacy file has been copied successfully.
        try:
            with manifest.open('x', encoding='utf-8') as output:
                output.write(content)
        except FileExistsError:
            pass  # Another server worker completed initialization first.
    return destination
