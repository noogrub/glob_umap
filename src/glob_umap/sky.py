from collections.abc import Iterator

import numpy as np
from scipy.spatial import cKDTree


ARCSEC_PER_RADIAN = 206264.80624709636


def unit_vectors(ra_deg: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
    """Convert right ascension and declination to unit Cartesian vectors."""
    ra = np.deg2rad(np.asarray(ra_deg, dtype=np.float64))
    dec = np.deg2rad(np.asarray(dec_deg, dtype=np.float64))
    cos_dec = np.cos(dec)
    return np.column_stack(
        (cos_dec * np.cos(ra), cos_dec * np.sin(ra), np.sin(dec))
    )


def candidate_batches(
    reference_ids: np.ndarray,
    reference_ra_deg: np.ndarray,
    reference_dec_deg: np.ndarray,
    target_ids: np.ndarray,
    target_ra_deg: np.ndarray,
    target_dec_deg: np.ndarray,
    radius_arcsec: float,
    chunk_rows: int,
    workers: int,
) -> Iterator[tuple[int, int, list[tuple[int, int, float, int, int]]]]:
    """Yield complete, deterministically ranked spherical match candidates."""
    reference_ids = np.asarray(reference_ids, dtype=np.int64)
    target_ids = np.asarray(target_ids, dtype=np.int64)
    if radius_arcsec <= 0:
        raise ValueError("radius_arcsec must be positive")
    if chunk_rows <= 0:
        raise ValueError("chunk_rows must be positive")
    if workers == 0 or workers < -1:
        raise ValueError("workers must be -1 or a positive integer")
    if not (
        reference_ids.size == len(reference_ra_deg) == len(reference_dec_deg)
    ):
        raise ValueError("Reference identifier and coordinate lengths differ")
    if not target_ids.size == len(target_ra_deg) == len(target_dec_deg):
        raise ValueError("Target identifier and coordinate lengths differ")
    reference_vectors = unit_vectors(reference_ra_deg, reference_dec_deg)
    target_vectors = unit_vectors(target_ra_deg, target_dec_deg)
    tree = cKDTree(reference_vectors)
    radius_radians = radius_arcsec / ARCSEC_PER_RADIAN
    chord_radius = 2.0 * np.sin(radius_radians / 2.0)

    for start in range(0, target_ids.size, chunk_rows):
        stop = min(start + chunk_rows, target_ids.size)
        neighborhoods = tree.query_ball_point(
            target_vectors[start:stop], chord_radius, workers=workers
        )
        rows: list[tuple[int, int, float, int, int]] = []
        for offset, reference_indexes in enumerate(neighborhoods):
            if not reference_indexes:
                continue
            target_index = start + offset
            indexes = np.asarray(reference_indexes, dtype=np.int64)
            candidates = reference_vectors[indexes]
            target_vector = target_vectors[target_index]
            dots = candidates @ target_vector
            cross_norms = np.linalg.norm(
                np.cross(candidates, target_vector), axis=1
            )
            separations = np.arctan2(cross_norms, dots)
            separations *= ARCSEC_PER_RADIAN
            within_radius = separations <= radius_arcsec
            indexes = indexes[within_radius]
            separations = separations[within_radius]
            if indexes.size == 0:
                continue
            order = np.lexsort((reference_ids[indexes], separations))
            count = int(indexes.size)
            for rank, order_index in enumerate(order, start=1):
                reference_index = indexes[order_index]
                rows.append(
                    (
                        int(target_ids[target_index]),
                        int(reference_ids[reference_index]),
                        float(separations[order_index]),
                        count,
                        rank,
                    )
                )
        yield start, stop, rows
