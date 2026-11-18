# Excluded pilot — GitHub Actions run 44237397496

Remote run: https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237397496

**Disposition: DO NOT INCLUDE in the three-run controlled Attest timing/overhead analysis.**

This first workflow run genuinely executed on hosted GitHub Actions runners
and successfully uploaded its trusted oracle plus 14 metric ZIPs. However,
its original prototype input-fingerprint walker recursively enumerated all
*.ts files, inadvertently including emitted *.d.ts declarations inside dist/.
When a test deliberately corrupted an emitted declaration, the guarded arm
wrongly treated an **output** change as a changed **input**. It rejected
selective repair (input_rejected=true and output_sha_scanned_bytes=0), fell
back to full cleaning, and distorted the claimed selective-method cost.

We fixed this by fingerprinting only explicitly designated config files and
packages/*/src TypeScript files. The corrected script passed its 16-case local
smoke test and was then executed on independently provisioned GitHub-hosted
runners in the three INCLUDED runs:

- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237916114
- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238758566
- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238773494

The pilot's original 15 artifact ZIPs and decoded JSON are retained for
transparent auditing. No pilot timing is mixed into the final aggregates.
All pilot and included-run partial-output faults were researcher-injected.
