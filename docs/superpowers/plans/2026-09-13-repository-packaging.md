# Repository packaging plan

Authorized destination: BirdieMoon-peter/Investment-Board. Preserve repository visibility and history; integrate with current main by a normal fast-forward or merge, never force-push.

1. Inspect remote refs, tracked/generated files, configuration and current functional evidence. Use the existing dirty checkout; preserve local runtime files when removing them from the index.
2. Update `.gitignore`; add a secret-free `backend/.env.example`, contributor setup/testing documentation and CI for Python3.12/Node22 if compatible with actual scripts. Keep local personal data, credentials and verification artifacts out of the commit. Do not invent a license.
3. Rewrite README as a polished Chinese project introduction, with concise English subtitle, actual feature matrix, architecture, reproducible installation/demo startup, AI configuration and limits. Reference `docs/images/dashboard.jpg` and `docs/images/stock-detail.jpg`.
4. Start the actual application with an isolated demo database on separate loopback ports. Capture a loaded dashboard and stock details with public/demo data. No screenshot fabrication; any simulated advice must be clearly identified as demonstration content. Preserve the main application database/settings.
5. Independently review packaging, source/config hygiene and README claims. Run backend/frontend/script tests, build, standalone smoke and fresh-clone-style setup verification. Verify the staged tree excludes dependencies, credentials and runtime data.
6. Commit coherent current sources and packaging; push the verified result to the existing default branch. Verify remote commit and README/image contents, record completion and stop only the temporary demo services.
