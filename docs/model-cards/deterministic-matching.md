# Deterministic matching card

**Type:** barcode lookup and bounded label rules. **Not a learned model.**

## Intended use

Suggest a unique known item from the synthetic catalog. Barcode input is text from keyboard entry or a scanner that acts like a keyboard. A valid checksum only establishes a well-formed identifier, not the identity or legitimacy of a real product.

Label matching uses catalog names and aliases. Ambiguous variants and unsupported text require a person. A suggested item must still be selected and checked by staff.

## Inputs and outputs

Inputs are a barcode string, typed label text, and the catalog. Output is a catalog `product_id` or an abstention, with method and reason. Ground-truth evaluation labels are not supplied to the matcher.

The mechanism does not return trusted quantities, weights, lots, expiry dates, product condition, shelf-life decisions, or safe storage instructions. A text phrase that resembles a command cannot authorize any workflow action.

## Evaluation

Use `python -m evaluation.run` and the evaluation README for exact metric definitions. Results concern small, authored synthetic cases. They are suitable for checking the pipeline and comparing behaviors, not estimating warehouse error rates or adoption.

Form-only has no automated prediction. A lack of prediction is not a claim that a person's entry is inaccurate. Human completion time and correction effort must be measured separately.

The optional `python -m evaluation.ocr_run` command supplies actual local Tesseract-extracted text from three synthetic label illustrations to catalog matching. Its three-image report is separate from the authored text benchmark and must not be combined with that denominator. The deterministic rules remain rules even when their input came from OCR.

## Limitations

Real item catalogs contain duplicate labels, packaging changes, damaged identifiers, aliases in multiple languages, and unit conversions. The synthetic catalog covers only a few examples. Correct the catalog through a controlled process rather than expanding matching until every input receives a confident answer.
