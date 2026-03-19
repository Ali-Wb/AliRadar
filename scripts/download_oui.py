from pathlib import Path

import requests


OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "oui.csv"
CHUNK_SIZE = 8192


def download_oui() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(OUI_URL, stream=True, timeout=60) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with OUTPUT_PATH.open("wb") as output_file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                output_file.write(chunk)
                downloaded += len(chunk)

                if total_size:
                    percent = downloaded / total_size * 100
                    print(f"Downloaded {downloaded}/{total_size} bytes ({percent:.1f}%)")
                else:
                    print(f"Downloaded {downloaded} bytes")

    print(f"Saved OUI data to {OUTPUT_PATH}")


if __name__ == "__main__":
    download_oui()
