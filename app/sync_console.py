"""
Local desktop synchronization console for Event Tracker.

This application:

- runs only on the user's computer
- accepts a phone-generated sync package
- imports events into the local SQLite database
- generates a synchronization receipt
- makes the receipt available for immediate download

It binds to localhost only and does not send event data externally.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.import_sync import (
    SyncPackageError,
    import_sync_package,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECEIPTS_DIRECTORY = (
    PROJECT_ROOT / "database" / "sync_receipts"
)

app = FastAPI(
    title="Event Tracker Sync Console",
    docs_url=None,
    redoc_url=None,
)


@app.get("/", response_class=HTMLResponse)
def read_sync_console() -> str:
    """Serve the local synchronization interface."""

    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    />

    <title>Event Tracker Sync</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 24px 16px;
            font-family: Arial, sans-serif;
            background: #f4f4f4;
            color: #222;
        }

        main {
            max-width: 620px;
            margin: 0 auto;
        }

        h1 {
            margin-bottom: 6px;
        }

        .subtitle {
            margin-top: 0;
            color: #666;
        }

        .card {
            margin-top: 20px;
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.08);
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }

        input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 8px;
            background: white;
        }

        button {
            width: 100%;
            margin-top: 16px;
            padding: 14px;
            border: none;
            border-radius: 8px;
            background: #222;
            color: white;
            font-size: 17px;
            font-weight: bold;
            cursor: pointer;
        }

        button:disabled {
            opacity: 0.6;
            cursor: default;
        }

        .status {
            margin-bottom: 0;
            font-weight: bold;
            line-height: 1.5;
        }

        .success {
            color: #176b35;
        }

        .error {
            color: #8f1d1d;
        }

        .privacy {
            margin-top: 18px;
            color: #666;
            font-size: 14px;
            line-height: 1.5;
        }
    </style>
</head>

<body>
    <main>
        <h1>Event Tracker Sync</h1>

        <p class="subtitle">
            Import phone events into the local SQLite database.
        </p>

        <section class="card">
            <form id="sync-form">
                <label for="sync-package">
                    Phone sync package
                </label>

                <input
                    id="sync-package"
                    name="sync_package"
                    type="file"
                    accept="application/json,.json"
                    required
                />

                <button
                    id="import-button"
                    type="submit"
                >
                    Import and Create Receipt
                </button>
            </form>

            <p
                id="status-message"
                class="status"
            ></p>

            <p class="privacy">
                This utility runs only on your computer.
                Event data is written directly to your local
                SQLite database and is not uploaded elsewhere.
            </p>
        </section>
    </main>

    <script>
        const syncForm =
            document.getElementById("sync-form");

        const packageInput =
            document.getElementById("sync-package");

        const importButton =
            document.getElementById("import-button");

        const statusMessage =
            document.getElementById("status-message");


        function downloadReceipt(receiptUrl) {
            const link =
                document.createElement("a");

            link.href = receiptUrl;
            link.download = "";

            document.body.appendChild(link);
            link.click();
            link.remove();
        }


        async function importPackage(event) {
            event.preventDefault();

            const selectedFile =
                packageInput.files[0];

            if (!selectedFile) {
                statusMessage.className =
                    "status error";

                statusMessage.textContent =
                    "Choose a sync package first.";

                return;
            }

            importButton.disabled = true;

            statusMessage.className = "status";
            statusMessage.textContent =
                "Importing events into SQLite...";

            const formData = new FormData();

            formData.append(
                "sync_package",
                selectedFile
            );

            try {
                const response = await fetch(
                    "/import",
                    {
                        method: "POST",
                        body: formData,
                    }
                );

                const result =
                    await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.detail ||
                        "Import failed."
                    );
                }

                statusMessage.className =
                    "status success";

                statusMessage.textContent =
                    `Sync complete. ` +
                    `${result.new_events_imported} new event` +
                    `${result.new_events_imported === 1 ? "" : "s"} ` +
                    `imported; ` +
                    `${result.events_already_present} already present. ` +
                    `The receipt download has started.`;

                downloadReceipt(
                    result.receipt_download_url
                );
            } catch (error) {
                statusMessage.className =
                    "status error";

                statusMessage.textContent =
                    error.message;

                console.error(error);
            } finally {
                importButton.disabled = false;
            }
        }


        syncForm.addEventListener(
            "submit",
            importPackage
        );
    </script>
</body>
</html>
"""


@app.post("/import")
async def import_uploaded_sync_package(
    sync_package: UploadFile = File(...),
) -> dict:
    """
    Import an uploaded sync package and return receipt metadata.
    """

    original_filename = (
        sync_package.filename or "sync-package.json"
    )

    if not original_filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="The sync package must be a JSON file.",
        )

    uploaded_bytes = await sync_package.read()

    if not uploaded_bytes:
        raise HTTPException(
            status_code=400,
            detail="The selected sync package is empty.",
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".json",
            delete=False,
        ) as temporary_file:
            temporary_file.write(uploaded_bytes)

            temporary_path = Path(
                temporary_file.name
            )

        receipt_path = import_sync_package(
            temporary_path
        )

        receipt = json.loads(
            receipt_path.read_text(
                encoding="utf-8"
            )
        )

        return {
            "status": "complete",
            "package_id": receipt["package_id"],
            "new_events_imported": len(
                receipt["accepted_event_ids"]
            ),
            "events_already_present": len(
                receipt[
                    "already_present_event_ids"
                ]
            ),
            "acknowledged_event_count": len(
                receipt[
                    "acknowledged_event_ids"
                ]
            ),
            "receipt_filename": (
                receipt_path.name
            ),
            "receipt_download_url": (
                f"/receipts/{receipt_path.name}"
            ),
        }

    except SyncPackageError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "The generated receipt could not be read."
            ),
        ) from error

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


@app.get("/receipts/{receipt_filename}")
def download_receipt(
    receipt_filename: str,
) -> FileResponse:
    """Download a previously generated synchronization receipt."""

    safe_filename = Path(
        receipt_filename
    ).name

    receipt_path = (
        RECEIPTS_DIRECTORY / safe_filename
    )

    if not receipt_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Synchronization receipt not found.",
        )

    return FileResponse(
        path=receipt_path,
        media_type="application/json",
        filename=safe_filename,
    )