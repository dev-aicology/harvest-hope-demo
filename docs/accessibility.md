# Accessibility and staff usability

The web interface is intended to be usable on a phone or desktop with clear labels, visible focus, keyboard operation, readable contrast, and errors expressed in text. Controls should not rely on color alone. These are design intentions and implementation checks, not a claim of certified conformance.

## Review checklist

- Use every field and action by keyboard, with an obvious focus position.
- Verify that inputs have associated labels and that repeated receipt lines remain understandable.
- Read errors with a screen reader; confirm that status changes are announced or reachable.
- Zoom to 200% and test a narrow phone viewport without losing actions or field names.
- Distinguish draft, approved, and simulated handoff states without relying only on color.
- Confirm that a match suggestion is visibly separate from a staff-confirmed value.
- Use plain words for correction, review, and retry; test with warehouse staff.
- Keep manual barcode entry and catalog selection available when scanning or AI assistance is unsuitable.
- Check touch targets, text size, glare, gloves, network interruptions, and actual receiving conditions during the pilot.

## Limits

No formal screen-reader, WCAG, multilingual, motor-accessibility, or warehouse usability study has been completed through this draft. The browser could not launch in the build environment because of its process/socket restrictions, so rendered layout and interactive browser behavior have not been verified there. The app currently has no offline synchronization or camera barcode reader. A USB/Bluetooth scanner that sends keyboard text may be used in a focused barcode field after testing.

Record feedback with the staff member's permission, and avoid including identifying details in public issues. Resolve usability obstacles before measuring whether the tool saves time.
