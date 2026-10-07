# RecordChain: Blockchain-Based Tamper-Proof Record Verification

A complete beginner-friendly web application demonstrating blockchain-based tamper detection for academic marks/certificate records.

## Stack
- Python 3.10+
- Flask
- SQLite
- HTML/CSS/JavaScript
- SHA-256 via Python `hashlib`
- QR codes via `qrcode`

## Architecture
Frontend → Flask REST API → Blockchain engine + SQLite → SHA-256 validation.

SQLite stores trusted application records and correction history. The custom blockchain stores the tamper-evident history. A legitimate correction creates a new block; it never edits the historical block.

## Features
- Admin login with hashed password
- Add certificate/marks records
- Create linked SHA-256 blocks
- Blockchain explorer
- Full chain validation
- Legitimate correction as a new block
- Public certificate verification
- QR code for verification
- Tampering simulator for the judge demo
- Resettable demonstration state
- Protected write operations while the chain is invalid
- Responsive dashboard

## Windows setup
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Demo admin credentials:
- Username: `admin`
- Password: `admin123`

## Test the project
```powershell
pytest -q
```

The suite covers hashing, chain integrity, legitimate corrections, certificate verification, invalid input, duplicate IDs, authentication, tampering, and reset recovery.

## Judge demo
1. Log in.
2. Add two records, for example 85 and 92 marks.
3. Open Blockchain Explorer and explain `Hash` and `Previous Hash`.
4. Show the green valid-chain status.
5. Make a legitimate correction, for example 85 → 90. Explain that the old block remains 85 and a new correction block records 90.
6. Open Public Verify and verify the certificate. Generate its QR code.
7. Return to Dashboard and choose a non-genesis block.
8. Click **Simulate Hacker Attack** and change its marks to 99.
9. Show the hash mismatch and broken chain.
10. Explain that the application blocks further normal writes while the chain is invalid.
11. Click **Reset Demo**. The chain is rebuilt from trusted SQLite application records and correction history.
12. Verify the certificate again and show the chain is valid.

## Core concept
`record data → SHA-256 hash → previous-hash link → validation`.

Changing historical data changes its calculated hash. The next block still contains the old hash, so validation detects the mismatch. A legitimate update is not an edit of history; it is a new correction block linked to the existing chain.

## Phase 3 validation
The project was checked against the agreed flow:
- Admin authentication → dashboard
- Add record → SHA-256 block creation → SQLite record
- Blockchain explorer → previous/current hash display
- Official correction → new correction block, historical block unchanged
- Public verification → hash + full-chain validation + correction history
- QR verification link generation
- Tamper simulation → hash mismatch + broken chain detection
- Invalid-chain write protection
- Reset → rebuild from trusted application data and correction history

Core blockchain tests and JavaScript syntax checks were run during packaging. On Windows, run `pytest -q` after installing the requirements to execute the full Flask integration suite as well.
