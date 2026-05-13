from pathlib import Path
import email
import quopri


def ingest_all_mhtml(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    print("🥉 Bronze:...")

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print("📊 Bronze Summary:")
        print("Total: 0 | Extracted: 0 | Failed: 0")
        return

    files = list(input_dir.glob("*.mhtml"))

    total = len(files)
    extracted = 0
    failed = 0

    if not files:
        print("\n⚠️ No MHTML files found in input directory.")
        print("\nFailed due to no files found.")
        return

    for file in files:
        raw = file.read_bytes()
        msg = email.message_from_bytes(raw)

        html = None

        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True)
                break

        if not html:
            print(f"⚠️ No HTML content found in: {file.name}")
            failed += 1
            continue

        try:
            html = quopri.decodestring(html)
        except Exception:
            pass

        output_file = output_dir / file.with_suffix(".html").name
        output_file.write_bytes(html)

        print(f"✅ Extracted: {file.name}")
        extracted += 1

    print("\n📊 Bronze Summary:")
    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")