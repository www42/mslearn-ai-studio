import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def fmt_time(ts):
    """Unix-Timestamp -> lesbares Datum (UTC), None -> '-'"""
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def fmt_bytes(n):
    """Bytes -> menschenlesbare Größe"""
    n = n or 0
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    show_files = "--files" in sys.argv

    load_dotenv()
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        print("AZURE_OPENAI_ENDPOINT muss in der .env gesetzt sein.")
        return

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://ai.azure.com/.default"
    )
    client = OpenAI(base_url=endpoint, api_key=token_provider)

    total_stores = 0
    total_bytes = 0

    # Iteration über die Liste paginiert automatisch über alle Seiten
    for vs in client.vector_stores.list(limit=100):
        total_stores += 1
        total_bytes += vs.usage_bytes or 0
        fc = vs.file_counts

        print(f"\n{vs.name or '(ohne Namen)'}")
        print(f"  ID:           {vs.id}")
        print(f"  Status:       {vs.status}")
        print(f"  Dateien:      {fc.total} gesamt | {fc.completed} ok | "
              f"{fc.failed} fehlgeschlagen | {fc.in_progress} in Arbeit")
        print(f"  Speicher:     {fmt_bytes(vs.usage_bytes)}")
        print(f"  Erstellt:     {fmt_time(vs.created_at)}")
        print(f"  Zuletzt aktiv:{' ' + fmt_time(vs.last_active_at)}")
        print(f"  Läuft ab:     {fmt_time(vs.expires_at)}")

        if show_files:
            for f in client.vector_stores.files.list(vector_store_id=vs.id, limit=100):
                try:
                    name = client.files.retrieve(f.id).filename
                except Exception:
                    name = "(Datei nicht mehr vorhanden)"
                print(f"    - {name}  [{f.id}, {f.status}]")

    print(f"\n{total_stores} Vector Store(s), insgesamt {fmt_bytes(total_bytes)}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"Fehler: {ex}")