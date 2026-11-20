# Local demonstration walkthrough

Use only the fictional products and receipts in `data/synthetic/`. This walkthrough is for a local review, not a warehouse operating procedure.

## 1. Capture a delivery

Start the app using the README and select **Receiver**. Create a receipt with a fictional supplier, a unique delivery reference, the demo warehouse, the receiving date, and a fictional purchase-order reference. The order field refers to an order that would already exist in real systems; this demonstration creates no order.

Use `data/synthetic/sample_receipt.json` as the reference example, or add one catalog item. Enter a valid synthetic barcode or type a label description. Request a suggestion, inspect its reason, and apply it only if it identifies the intended item. A match does not confirm the quantity.

Enter the actual illustrative quantity and its catalog unit. Add measured weight, lot, and expiry only as required by the item. Check the line after inspecting its values and save the draft. If using a sample with a date that has become past, change it to an appropriate fictional future expiry for the normal-path demonstration.

## 2. Exercise an exception

Add a line with an unknown item, a wrong unit, a missing required weight, or a `hold` disposition. Save it, then try to submit. Read the blocking issue. Correct the entry or leave it in draft. The system should not create a new product or mark the line available on its own.

An optional uploaded label image is stored evidence. The current app does not read the image, count its contents, or measure its weight. Use `data/synthetic/labels/demo-beans-case.png`, `demo-oats-case.png`, or `demo-apples-lb.png` to test storage and deletion.

## 3. Submit and approve

Once every line is valid and explicitly checked, submit the receipt. Switch to **Reviewer** and reopen it. Inspect the entries, suggestions, and validation findings. Return it with a reason if it needs correction, or approve it.

A reviewer cannot approve their own latest content edit. Edits before handoff remove an existing approval and send the record back through draft/review. These controls are enforced by the backend, not only by hidden buttons.

## 4. Simulate a handoff

With a valid purchase-order reference, run the mock handoff. The visible result should identify itself as simulated. No WAERlinx or NetSuite record has changed.

Repeat the same handoff request with the same idempotency key in an API test to confirm that it retrieves the prior result instead of making another transaction. The UI retains a key for a retry; do not deliberately change the key merely to bypass an uncertain result.

Run mock reconciliation to compare the approved and returned record. Use the mismatch scenario to see the discrepancy state. Do not edit the sent receipt to conceal the difference.

## 5. Inspect the evidence

Open the audit view and inspect capture, suggestions, corrections, approval, handoff, and reconciliation. The chain check concerns consistency of the local audit records. Export the neutral JSON for technical review; it is not a vendor import file and carries its actual status. An approved snapshot is present only when one exists.

## 6. Run the comparison

Run `python -m evaluation.run`, then inspect the generated report and case details. Compare coverage with precision and abstentions. The displayed elapsed time is algorithm time on synthetic examples, not end-to-end staff time. Read [evaluation/README.md](../evaluation/README.md) before attempting an optional model run.

If local Tesseract and English language data are installed, run `python -m evaluation.ocr_run` for the separate three-image OCR check. Its included result has three correct catalog suggestions from three synthetic label illustrations. Keep that result separate from the 62 authored text cases and from any claim about real warehouse images.

For a future study, copy `evaluation/observations.template.csv` into a private location and record actual observations. The summarizer described in the evaluation README reports only supplied measurements; the included template is empty and establishes no staff-time savings or operating cost.
