# Artifacts

## `collatz_certificate.json`

`collatz_certificate.json` is the large exported certificate artifact generated
by the workbench. It packages the certificate data into one JSON file for
external transfer and verification workflows.

The file is intentionally excluded from normal git tracking because it is about
390 MB. GitHub rejects normal git blobs over 100 MB, and storing the artifact in
git would make the repository heavy for reviewers who only need the scripts,
reports, and UI.

The repository is not incomplete without this file. The source scripts, audit
reports, checksum, and regeneration path are tracked here; the large JSON
artifact is distributed separately.

## Download

Primary location:

https://github.com/lv300-max/collatz-certificate-workbench/releases/download/certificate-artifacts-v1/collatz_certificate.json

Checksum:

```text
479645e83e56cb2864d6a4340ee945ca00c2dbed466a3d1e575d3326de31cca7  collatz_certificate.json
```

The checksum is also stored in `collatz_certificate.sha256`.

## Regenerate

From the repository root:

```bash
python3 certificate_export.py
```

This recreates `collatz_certificate.json` from the local workbench export path.

## Verify

After downloading or regenerating the artifact, run:

```bash
shasum -a 256 -c collatz_certificate.sha256
```

Expected result:

```text
collatz_certificate.json: OK
```

## Future Archive Targets

The GitHub Release asset is the first distribution target. If serious external
review starts, a Zenodo archive should be created for a DOI-backed immutable
snapshot. Other acceptable mirrors include Google Drive, OSF, or a Hugging Face
dataset.
