# Raster-only and leakage gate

The solver boundary accepts raster bytes and explicit non-answer context. Raw SVG/XML, HTML, DOM, query parameters, accessibility labels, `data-*` attributes, manifests, and evaluator ground truth stay outside the solver process.

The evidence record includes an input hash and metadata-stripping result. Self-reported leakage flags are not sufficient; negative fixtures must intentionally include semantic metadata and prove it is absent from the solver input.
