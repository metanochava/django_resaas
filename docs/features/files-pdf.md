# Files and PDF

## Files

The framework can represent `FileField` and `ImageField` with useful
information such as URL, name, extension, size and MIME type.

## Upload

Paths must avoid name collisions and respect the organization by
entity/application when defined.

## PDF

The utilities layer can include:

-   PDF generation;
-   QR Code;
-   barcode;
-   PNG-to-Base64 conversion;
-   document templates.

Applications should keep their specific presentation in their own
templates and reuse the common utilities.
