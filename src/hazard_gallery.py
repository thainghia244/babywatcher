"""Hazard object gallery: few-shot matching against caregiver-registered dangerous objects.

Reinforces (never gates) the existing OBJECT_TO_MOUTH detection in detector.py --
an object that matches a registered hazard raises confidence and reduces
confirmation delay, but unmatched objects still go through the normal
detection path unchanged, so a hazard the caregiver never photographed is
still caught.

Embeddings come from an ImageNet-pretrained MobileNetV3-Small (torchvision),
NOT from the BabyWatcher object detector's own backbone. Empirically, the
detector's embed() collapses everything close together in similarity space
(unrelated images averaged ~0.93 cosine similarity in testing -- unusable for
matching) because it's trained for a narrow 3-class task, not open-set visual
similarity. MobileNetV3's general-purpose ImageNet features separate
unrelated crops far better (~0.22-0.63 in the same test) while still scoring
a genuine repeat of the same object near 1.0.
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torchvision
from torchvision import transforms

_model = None
_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def _get_model():
    global _model
    if _model is None:
        _model = torchvision.models.mobilenet_v3_small(
            weights=torchvision.models.MobileNet_V3_Small_Weights.DEFAULT
        )
        _model.eval()
    return _model


def extract_embedding(image_bgr: np.ndarray) -> np.ndarray:
    """Extract a 576-dim MobileNetV3 feature vector from a BGR image/crop."""
    model = _get_model()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    tensor = _transform(rgb).unsqueeze(0)
    with torch.no_grad():
        features = model.features(tensor)
        pooled = torch.nn.functional.adaptive_avg_pool2d(features, 1).flatten(1)
    return pooled.numpy()[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two embedding vectors, in [-1, 1]."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class HazardGallery:
    """A small reference set of embeddings for caregiver-registered dangerous objects."""

    def __init__(self, gallery_path: str = ""):
        """
        Args:
            gallery_path: Path to a gallery.json file. Empty string disables the gallery
                (match() then always returns None, i.e. a strict no-op).
        """
        self.gallery_path = gallery_path
        self.entries: List[Dict] = []
        if gallery_path and os.path.exists(gallery_path):
            self.load()

    @property
    def enabled(self) -> bool:
        return bool(self.gallery_path)

    def load(self) -> None:
        with open(self.gallery_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.entries = data.get('entries', [])
        # Entries registered before 'id'/'thumbnail' existed (e.g. the very
        # first hazard objects added to this project) predate both fields --
        # backfill a stable id so rename()/delete() in the gallery manager UI
        # can target them unambiguously. Does not touch gallery.json until
        # the next save(), so a read-only load() has no side effect on disk.
        needs_id = False
        for entry in self.entries:
            if 'id' not in entry:
                entry['id'] = uuid.uuid4().hex[:12]
                needs_id = True
            entry.setdefault('thumbnail', None)
        if needs_id:
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.gallery_path) or '.', exist_ok=True)
        with open(self.gallery_path, 'w', encoding='utf-8') as f:
            json.dump({'entries': self.entries}, f, indent=2, ensure_ascii=False)

    def add(self, name: str, embedding: np.ndarray, severity: str = 'high',
            source_image: Optional[str] = None, thumbnail_path: Optional[str] = None) -> Dict:
        """Register a new hazard object.

        Args:
            name: Human-readable name shown in alerts/logs, e.g. "cúc áo".
            embedding: Feature vector from extract_embedding().
            severity: "high" or "critical" -- critical objects get the largest
                confirmation-delay reduction when matched (see detector.py).
            source_image: Path to the registration photo, kept for reference/debugging.
            thumbnail_path: Path to a saved crop of the registered object, shown in the
                gallery manager UI (src/hazard_manager.py) so a caregiver can visually
                tell entries apart when renaming/deleting -- entries registered before
                this field existed simply have no thumbnail and fall back to a
                name-only placeholder there.

        Returns:
            The newly created entry dict, with a stable 'id' the gallery manager UI
            uses to rename/delete this exact entry unambiguously even if two entries
            share the same name.
        """
        entry = {
            'id': uuid.uuid4().hex[:12],
            'name': name,
            'embedding': embedding.tolist(),
            'severity': severity,
            'source_image': source_image,
            'thumbnail': thumbnail_path,
        }
        self.entries.append(entry)
        return entry

    def rename(self, entry_id: str, new_name: str) -> bool:
        """Rename the entry with this id. Returns False if no such entry exists."""
        for entry in self.entries:
            if entry.get('id') == entry_id:
                entry['name'] = new_name
                return True
        return False

    def delete(self, entry_id: str) -> bool:
        """Remove the entry with this id (and its thumbnail file, if any).
        Returns False if no such entry exists."""
        for i, entry in enumerate(self.entries):
            if entry.get('id') == entry_id:
                thumb = entry.get('thumbnail')
                if thumb and os.path.exists(thumb):
                    try:
                        os.remove(thumb)
                    except OSError:
                        pass
                del self.entries[i]
                return True
        return False

    def best_match(self, embedding: np.ndarray) -> Optional[Tuple[Dict, float]]:
        """Return (entry, similarity) for the closest entry, regardless of any
        threshold -- used for debug/diagnostic readouts (see
        debug_hazard_live.py) so a near-miss is visible instead of just a
        pass/fail. Real matching decisions should use match(), not this."""
        if not self.entries:
            return None
        best_entry, best_sim = None, -1.0
        for entry in self.entries:
            sim = cosine_similarity(embedding, np.array(entry['embedding'], dtype=np.float32))
            if sim > best_sim:
                best_sim = sim
                best_entry = entry
        return (best_entry, best_sim) if best_entry is not None else None

    def match(self, embedding: np.ndarray, threshold: float = 0.75) -> Optional[Tuple[Dict, float]]:
        """Return (entry, similarity) for the best match above threshold, or None.

        Args:
            embedding: Feature vector of the candidate object crop being evaluated live.
            threshold: Minimum cosine similarity to count as a match.
        """
        best = self.best_match(embedding)
        if best is None:
            return None
        best_entry, best_sim = best

        if best_entry is not None and best_sim >= threshold:
            return best_entry, best_sim
        return None
