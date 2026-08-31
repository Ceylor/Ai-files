"""
GPU/CPU detection and compute type selection.

Provides a singleton GPUDetector that probes actual hardware capabilities
(not just presence) and selects optimal compute types for ML workloads.

Usage:
    from src.utils.gpu_detector import gpu
    device = gpu.get_whisper_device()  # "cuda" or "cpu"
    compute = gpu.get_compute_type()  # "int8", "float16", "int8_float16"
"""
from __future__ import annotations

import logging
import os
import subprocess
import shutil

logger = logging.getLogger("gpu_detector")


class GPUDetector:
    """Singleton that detects GPU capabilities and selects optimal compute config."""

    _instance: "GPUDetector | None" = None

    def __new__(cls) -> "GPUDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detected = False
        return cls._instance

    def _ensure_detected(self) -> None:
        if self._detected:
            return
        self._detected = True
        self.cuda_available = False
        self.gpu_name: str | None = None
        self.compute_capability: tuple[int, int] | None = None
        self.fp16_tensor_cores = False
        self._detect()

    def _detect(self) -> None:
        try:
            import torch
            if torch.cuda.is_available():
                self.cuda_available = True
                self.gpu_name = torch.cuda.get_device_name(0)
                cc = torch.cuda.get_device_capability(0)
                self.compute_capability = cc
                self.fp16_tensor_cores = cc[0] >= 7  # Volta+
                logger.info(
                    "GPU detected: %s, CC=%s, FP16=%s",
                    self.gpu_name, cc, self.fp16_tensor_cores,
                )
            else:
                logger.info("CUDA not available, using CPU")
        except ImportError:
            logger.info("PyTorch not installed, using CPU")
        except Exception as exc:
            logger.warning("GPU detection failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_torch_device(self) -> str:
        """Returns 'cuda' or 'cpu' for torch operations."""
        self._ensure_detected()
        return "cuda" if self.cuda_available else "cpu"

    def get_whisper_device(self) -> str:
        """Returns device string for faster-whisper."""
        self._ensure_detected()
        return "cuda" if self.cuda_available else "cpu"

    def get_whisper_compute_type(self) -> str:
        """Returns optimal compute type for faster-whisper.

        Pre-Volta GPUs lack fp16 tensor cores, so we use int8_float16.
        CPU always uses int8.
        """
        self._ensure_detected()
        if not self.cuda_available:
            return "int8"
        if self.fp16_tensor_cores:
            return "float16"
        return "int8_float16"

    def get_yolo_device(self) -> str:
        """Returns device string for YOLO: '0' for GPU, 'cpu' for CPU."""
        self._ensure_detected()
        return "0" if self.cuda_available else "cpu"

    def get_clip_device(self) -> str:
        """Returns torch device string for CLIP model."""
        self._ensure_detected()
        return "cuda" if self.cuda_available else "cpu"

    def get_clip_dtype(self):
        """Returns optimal torch dtype for CLIP on this hardware."""
        self._ensure_detected()
        try:
            import torch
            if self.cuda_available and self.fp16_tensor_cores:
                return torch.float16
            return torch.float32
        except ImportError:
            return None

    def get_nvenc_available(self) -> bool:
        """Probes whether NVENC actually encodes (not just listed)."""
        self._ensure_detected()
        if not self.cuda_available:
            return False
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False
        try:
            result = subprocess.run(
                [ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=10,
            )
            return "h264_nvenc" in result.stdout
        except Exception:
            return False

    def get_info(self) -> dict:
        """Returns full GPU info dict for health checks."""
        self._ensure_detected()
        info = {
            "cuda_available": self.cuda_available,
            "gpu_name": self.gpu_name,
            "compute_capability": (
                f"{self.compute_capability[0]}.{self.compute_capability[1]}"
                if self.compute_capability else None
            ),
            "fp16_tensor_cores": self.fp16_tensor_cores,
            "nvenc_available": self.get_nvenc_available(),
            "whisper_device": self.get_whisper_device(),
            "whisper_compute_type": self.get_whisper_compute_type(),
            "yolo_device": self.get_yolo_device(),
        }
        return info


# Module-level singleton for convenient import
gpu = GPUDetector()
