import numpy as np
from ripser import ripser
from scipy.spatial import Delaunay
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class UVMapTelemetry:
    """Structured report for UV mapping telemetry."""
    islands: int
    distortion_score: float
    seam_coordinates: List[float]
    topology_status: str
    h1_lifetimes: Optional[np.ndarray] = None  # Store H1 persistence intervals

class PriceUVMapper:
    """
    Price Topology Unwrapper: Treats OHLCV as a 3D mesh for structural analysis.
    Uses Persistent Homology to flatten 3D volatility surfaces into UV islands.
    """

    def __init__(self, persistence_threshold: float = 0.6):
        self.threshold = persistence_threshold
        self.seams = []
        self.delaunay_triangulation = None

    def create_price_mesh(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generates the 3D Point Cloud (X: Time, Y: Price, Z: Volume).
        Optionally normalizes data for better topological analysis.
        """
        time_steps = np.arange(len(prices))
        mesh = np.column_stack((time_steps, prices, volumes))

        if normalize:
            mesh = (mesh - mesh.min(axis=0)) / (mesh.max(axis=0) - mesh.min(axis=0) + 1e-9)

        return mesh

    def detect_seams(
        self,
        mesh: np.ndarray,
        ranges: Dict[int, Dict[str, float]]
    ) -> List[float]:
        """
        Seam Detection: Marks IPDA 20/40/60 boundaries as UV seams.
        """
        if not ranges:
            raise ValueError("Ranges dictionary cannot be empty.")

        # Example: Use 60-period high/low as seams
        h60, l60 = ranges.get(9, {}).get('h', 0), ranges.get(9, {}).get('l', 0)
        self.seams = [h60, l60]
        return self.seams

    def unwrap_topology(
        self,
        data_cloud: np.ndarray
    ) -> UVMapTelemetry:
        """
        Unwraps the high-dimensional point cloud into flattened UV coordinates.
        Identifies Persistent Loops (H1) as 'Holes' in the texture.
        """
        if len(data_cloud) < 3:
            raise ValueError("Data cloud must have at least 3 points.")

        # Run Vietoris-Rips Filtration
        dgms = ripser(data_cloud, maxdim=1)['dgms']
        h1_intervals = dgms[1]

        # Calculate lifetimes (Death - Birth)
        lifetimes = h1_intervals[~np.isinf(h1_intervals[:, 1]), 1] - h1_intervals[~np.isinf(h1_intervals[:, 1]), 0]
        active_islands = np.sum(lifetimes > self.threshold)

        # Distortion Score: High H1 persistence = High Topological Distortion
        distortion = np.sum(lifetimes)

        status = (
            "COMPACT_CLOUD" if distortion < 0.5
            else "GEOMETRY_FRACTURE" if distortion > 1.0
            else "MODERATE_DISTORTION"
        )

        return UVMapTelemetry(
            islands=int(active_islands),
            distortion_score=float(distortion),
            seam_coordinates=self.seams,
            topology_status=status,
            h1_lifetimes=lifetimes
        )

    def generate_uv_texture(
        self,
        mesh: np.ndarray
    ) -> np.ndarray:
        """
        Flattens 3D mesh for 2D UI heatmapping using Delaunay triangulation.
        """
        if len(mesh) < 3:
            raise ValueError("Mesh must have at least 3 points for triangulation.")

        self.delaunay_triangulation = Delaunay(mesh[:, :2])  # Project Time-Price to 2D
        return self.delaunay_triangulation.simplices
