# Normalized solution contract

A solution uses one typed payload while retaining all canonical fields for stable serialization:

- `text`
- `points: [{x, y}]`
- `tiles: [integer]`
- `offset: {x, y}`
- `angle_degrees`
- `track: [{x, y, time_ms}]`
- `press: {duration_ms, x, y}`

Unused fields are null or empty. Do not introduce an `offset_x` alias into the v1 contract.
