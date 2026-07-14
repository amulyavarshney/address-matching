#!/usr/bin/env python3
"""
Offline training for the address-matching ML model.

Usage:
  python scripts/train_ml_model.py --output address_matching_model.pkl

This trains on synthetic labeled pairs for bootstrap only. Replace with real
labeled data before production use.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without install
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Train address matching ML model")
    parser.add_argument(
        "--output",
        default="address_matching_model.pkl",
        help="Path to write the trained model pickle",
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=50.0,
        help="Geospatial feature threshold in meters",
    )
    args = parser.parse_args()

    from app.ml_model import AddressMatchingMLModel, SKLEARN_AVAILABLE

    if not SKLEARN_AVAILABLE:
        print("scikit-learn is required. Install with: pip install -r requirements.txt")
        return 1

    model = AddressMatchingMLModel(
        model_path=args.output,
        auto_train=False,
        distance_threshold=args.distance_threshold,
    )
    model.model_path = args.output
    model._train_with_synthetic_data()
    if not model.is_trained:
        print("Training failed")
        return 1

    print(f"Model trained and saved to {args.output}")
    importance = model.get_feature_importance()
    if importance:
        print("Top features:")
        for name, score in sorted(importance.items(), key=lambda x: -x[1])[:5]:
            print(f"  {name}: {score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
