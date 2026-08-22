# Reviewed canonical documents

This directory contains lightweight textual representations that a repository reviewer
can audit without running Docling. Each Markdown artifact includes:

- official-source metadata and a SHA-256 fingerprint;
- text and tables structurally extracted by Docling;
- explicitly verified cells where a typed evidence contract exists;
- English Gemini visual descriptions, grounded observations and declared uncertainties;
- links to the reviewed extracted figure images stored under `assets/`.

The balanced 2025 demonstration corpus contains three narrative documents (SFCR,
Governance Charter and Sustainability Statement) and three table-heavy QRTs (Foyer
Group, Foyer Assurances and Foyer Global Health).

Raw PDFs, page renders, Docling model caches and embedding vectors remain outside Git.
They are reproducible from the official URL, source hash and ingestion commands. The
reviewed Markdown and extracted figure images are versionable evidence artifacts; they
do not imply that arbitrary PDF ingestion happens in the deployed application.
