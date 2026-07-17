# Action plan contract

An action plan binds a source prediction and challenge instance to a coordinate frame and ordered actions. The frame includes viewport size, device-pixel ratio, crop origin, scroll offsets, iframe transforms, and rounding policy.

Action kinds include pointer down/move/up, click/tap, wait, text input, press, and rotate. Every action has monotonic `time_ms`; coordinate-bearing actions must be inside the resolved viewport.

Plans include an expiry, constraints, stop conditions, and authorization record ID. The default is `executable: false`.
