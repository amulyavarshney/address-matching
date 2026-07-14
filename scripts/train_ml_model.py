#!/usr/bin/env python3
"""
Offline training for the address-matching ML model.

Examples:
  # Bootstrap with synthetic data (dev only)
  python scripts/train_ml_model.py --synthetic --output address_matching_model.pkl

  # Train from labeled address pairs
  python scripts/train_ml_model.py --pairs data/sample_labeled_pairs.csv \\
      --output address_matching_model.pkl

  # Train from precomputed feature rows
  python scripts/train_ml_model.py --features data/sample_features.csv \\
      --output address_matching_model.pkl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--synthetic",
        action="store_true",
        help="Train on synthetic bootstrap data (not for production)",
    )
    source.add_argument(
        "--pairs",
        help="CSV of address1,address2,match[,region,geospatial_distance_meters]",
    )
    source.add_argument(
        "--features",
        help="CSV of 11 feature columns + label",
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

    try:
        if args.synthetic:
            model._train_with_synthetic_data()
            accuracy = None
        elif args.pairs:
            accuracy = model.train_from_labeled_pairs_csv(args.pairs, save=True)
        else:
            accuracy = model.train_from_features_csv(args.features, save=True)
    except Exception as exc:
        print(f"Training failed: {exc}")
        return 1

    if not model.is_trained:
        print("Training failed")
        return 1

    print(f"Model trained and saved to {args.output}")
    if accuracy is not None:
        print(f"Holdout accuracy: {accuracy:.3f}")
    importance = model.get_feature_importance()
    if importance:
        print("Top features:")
        for name, score in sorted(importance.items(), key=lambda x: -x[1])[:5]:
            print(f"  {name}: {score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
