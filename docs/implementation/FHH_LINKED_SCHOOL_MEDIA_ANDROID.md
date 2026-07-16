
Multi-photo guarantee: each update image is keyed by update ID plus photo ID. Native downloads use the same authenticated FHH proxy/blob flow for one-photo and five-photo updates; one failed key affects only its own tile.

Device smoke: test both a one-photo and a five-photo linked CHH update in FHH Dev; all thumbnails should resolve independently, and one intentionally unavailable photo must not hide the others.
