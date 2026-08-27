# -*- coding: utf-8 -*-
"""
perception — avci kamerasindan (oyun ekrani) hedef tespiti ve takibi.

    camera.py          — mss ekran yakalama -> tespit -> takip -> detection_state
    detector.py        — YOLO tespiti (models/talon_v3.engine varsa o, yoksa .pt) + pervane maskesi
    tracking.py        — HybridSort (boxmot) ile kareler-arasi kimlik surekliligi
    detection_state.py — kamera thread'i <-> guduum dongusu arasindaki kopru

Hat TEK YONLUDUR: camera yazar, control/main.py (PhaseSupervisor.read_detection) okur.
"""

__all__ = ["camera", "detector", "tracking", "detection_state"]
