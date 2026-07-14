import os
import pickle
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from loguru import logger

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
    logger.debug("Scikit-learn library is available")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.debug("Scikit-learn library not available, ML model disabled")

from app.models import ComponentSimilarities


class AddressMatchingMLModel:
    """
    Optional ML model for address matching entity resolution.

    By default does not auto-train or write files. Load a pre-trained model via
    model_path, or set auto_train=True for development only.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        auto_train: bool = False,
        distance_threshold: float = 50.0,
    ):
        self.sklearn_available = SKLEARN_AVAILABLE
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.model_path = model_path or "address_matching_model.pkl"
        self.auto_train = auto_train
        self.distance_threshold = distance_threshold

        if self.sklearn_available:
            self.model = LogisticRegression(random_state=42)
            self.scaler = StandardScaler()

            if self.model_path and os.path.exists(self.model_path):
                self.load_model()
            elif self.auto_train:
                logger.warning(
                    "ml_auto_train=True: training synthetic model "
                    "(not recommended for production)"
                )
                self._train_with_synthetic_data()
            else:
                logger.debug(
                    "No ML model file at %s; using heuristic fallback",
                    self.model_path,
                )
        else:
            logger.debug("ML model functionality disabled due to missing dependencies")
    
    def extract_features(
        self, 
        similarities: ComponentSimilarities,
        geospatial_distance: Optional[float] = None,
        overall_similarity: Optional[float] = None
    ) -> List[float]:
        """
        Extract features for ML model from component similarities.
        
        Args:
            similarities: Component similarity scores
            geospatial_distance: Distance in meters (optional)
            overall_similarity: Overall similarity score (optional)
            
        Returns:
            List of feature values
        """
        features = []
        
        # Component similarities (use 0.0 for None values)
        features.append(similarities.house_number or 0.0)
        features.append(similarities.street or 0.0)
        features.append(similarities.city or 0.0)
        features.append(similarities.postal_code or 0.0)
        features.append(similarities.state or 0.0)
        features.append(similarities.country or 0.0)
        
        # Derived features
        # Count of non-null similarities
        non_null_count = sum(1 for score in [
            similarities.house_number, similarities.street, similarities.city,
            similarities.postal_code, similarities.state, similarities.country
        ] if score is not None)
        features.append(non_null_count / 6.0)  # Normalized completeness score
        
        # Average of available similarities
        available_scores = [score for score in [
            similarities.house_number, similarities.street, similarities.city,
            similarities.postal_code, similarities.state, similarities.country
        ] if score is not None]
        avg_similarity = sum(available_scores) / len(available_scores) if available_scores else 0.0
        features.append(avg_similarity)
        
        # Overall similarity
        features.append(overall_similarity or 0.0)
        
        # Geospatial features
        if geospatial_distance is not None:
            # Normalize distance (log transform to handle large distances)
            normalized_distance = min(1.0, np.log(max(1.0, geospatial_distance)) / np.log(1000))
            features.append(1.0 - normalized_distance)  # Convert to similarity
            features.append(1.0 if geospatial_distance <= self.distance_threshold else 0.0)
        else:
            features.append(0.5)  # Neutral value when distance unavailable
            features.append(0.5)  # Neutral value for threshold
        
        return features
    
    def predict(
        self, 
        similarities: ComponentSimilarities,
        geospatial_distance: Optional[float] = None,
        overall_similarity: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Predict if addresses match using the ML model.
        
        Args:
            similarities: Component similarity scores
            geospatial_distance: Distance in meters (optional)
            overall_similarity: Overall similarity score (optional)
            
        Returns:
            Tuple of (match_prediction, confidence_score)
        """
        if not self.sklearn_available or not self.is_trained:
            logger.debug("ML model not available or not trained, using fallback")
            return self._fallback_prediction(similarities, overall_similarity)
        
        try:
            features = self.extract_features(similarities, geospatial_distance, overall_similarity)
            features_array = np.array(features).reshape(1, -1)
            
            # Scale features
            if self.scaler is not None:
                features_scaled = self.scaler.transform(features_array)
            else:
                features_scaled = features_array
            
            # Make prediction
            if self.model is not None:
                prediction = self.model.predict(features_scaled)[0]
                probability = self.model.predict_proba(features_scaled)[0]
            else:
                return self._fallback_prediction(similarities, overall_similarity)
            
            match_prediction = bool(prediction)
            confidence = float(max(probability))  # Highest probability
            
            logger.debug(f"ML prediction: {match_prediction}, confidence: {confidence:.3f}")
            return match_prediction, confidence
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            return self._fallback_prediction(similarities, overall_similarity)
    
    def _fallback_prediction(
        self, 
        similarities: ComponentSimilarities, 
        overall_similarity: Optional[float]
    ) -> Tuple[bool, float]:
        """
        Fallback prediction when ML model is not available.
        """
        if overall_similarity is None:
            return False, 0.5
        
        # Simple threshold-based prediction
        threshold = 0.7
        match = overall_similarity >= threshold
        confidence = overall_similarity if match else 1.0 - overall_similarity
        
        return match, confidence
    
    def _generate_synthetic_data(self, n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for the model.
        """
        np.random.seed(42)
        
        features = []
        labels = []
        
        for _ in range(n_samples):
            # Generate random similarity scores
            house_num_sim = np.random.random()
            street_sim = np.random.random()
            city_sim = np.random.random()
            postal_sim = np.random.random()
            state_sim = np.random.random()
            country_sim = np.random.random()
            
            # Create ComponentSimilarities object
            similarities = ComponentSimilarities(
                house_number=house_num_sim,
                street=street_sim,
                city=city_sim,
                postal_code=postal_sim,
                state=state_sim,
                country=country_sim
            )
            
            # Generate overall similarity and distance
            overall_sim = np.mean([house_num_sim, street_sim, city_sim, postal_sim])
            distance = np.random.exponential(100)  # Exponential distribution for distances
            
            # Extract features
            feature_vector = self.extract_features(similarities, distance, overall_sim)
            features.append(feature_vector)
            
            # Generate label based on heuristics (higher similarities and lower distances = match)
            match_score = (overall_sim * 0.7 + 
                          (1.0 - min(1.0, distance / 200)) * 0.3 +
                          np.random.normal(0, 0.1))  # Add some noise
            
            label = 1 if match_score > 0.6 else 0
            labels.append(label)
        
        return np.array(features), np.array(labels)
    
    def _train_with_synthetic_data(self):
        """Train the model with synthetic data."""
        if not self.sklearn_available:
            return
        
        try:
            logger.info("Training ML model with synthetic data...")
            
            # Generate synthetic data
            X, y = self._generate_synthetic_data(1000)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Model trained with accuracy: {accuracy:.3f}")
            self.is_trained = True
            
            # Save model
            self.save_model()
            
        except Exception as e:
            logger.error(f"Error training synthetic model: {e}")
            self.is_trained = False

    def train_from_feature_rows(
        self,
        features: "np.ndarray",
        labels: "np.ndarray",
        save: bool = True,
    ) -> float:
        """
        Train from an explicit feature matrix (N x 11) and binary labels.

        Returns test accuracy.
        """
        if not self.sklearn_available:
            raise RuntimeError("scikit-learn is required for training")
        if len(features) == 0:
            raise ValueError("No training rows provided")

        if len(features) < 10:
            X_train, y_train = features, labels
            X_test, y_test = features, labels
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                features,
                labels,
                test_size=0.2,
                random_state=42,
                stratify=labels if len(set(labels.tolist())) > 1 else None,
            )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        self.model.fit(X_train_scaled, y_train)
        y_pred = self.model.predict(X_test_scaled)
        accuracy = float(accuracy_score(y_test, y_pred))
        self.is_trained = True
        logger.info(f"Model trained from labeled features accuracy={accuracy:.3f}")
        if save:
            self.save_model()
        return accuracy

    def train_from_labeled_pairs_csv(
        self,
        csv_path: str,
        save: bool = True,
    ) -> float:
        """
        Train from a CSV of address pairs.

        Required columns: address1, address2, match
        Optional: region, geospatial_distance_meters
        match values: 1/0, true/false, yes/no
        """
        import csv

        from app.address_parser import AddressParser
        from app.fuzzy_matcher import FuzzyMatcher
        from app.models import ComponentSimilarities

        parser = AddressParser()
        rows_x = []
        rows_y = []

        with open(csv_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"address1", "address2", "match"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError(
                    f"CSV must include columns {sorted(required)}; "
                    f"got {reader.fieldnames}"
                )

            for row in reader:
                region = (row.get("region") or "US").strip().upper()
                addr1 = parser.normalize_and_parse(row["address1"])
                addr2 = parser.normalize_and_parse(row["address2"])
                fuzzy = FuzzyMatcher(region=region)
                similarities, overall = fuzzy.get_similarity_details(
                    addr1, addr2, region
                )
                distance = None
                raw_distance = (row.get("geospatial_distance_meters") or "").strip()
                if raw_distance:
                    try:
                        distance = float(raw_distance)
                    except ValueError:
                        distance = None

                rows_x.append(
                    self.extract_features(similarities, distance, overall)
                )
                rows_y.append(self._parse_label(row["match"]))

        if not rows_x:
            raise ValueError(f"No data rows in {csv_path}")

        return self.train_from_feature_rows(
            np.array(rows_x, dtype=float),
            np.array(rows_y, dtype=int),
            save=save,
        )

    def train_from_features_csv(self, csv_path: str, save: bool = True) -> float:
        """
        Train from a CSV of precomputed features + label.

        Columns (11 features + label):
          house_number,street,city,postal_code,state,country,
          completeness,avg_similarity,overall_similarity,
          geo_similarity,within_threshold,label
        """
        import csv

        feature_cols = [
            "house_number",
            "street",
            "city",
            "postal_code",
            "state",
            "country",
            "completeness",
            "avg_similarity",
            "overall_similarity",
            "geo_similarity",
            "within_threshold",
        ]
        rows_x = []
        rows_y = []
        with open(csv_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            if "label" not in fields or not set(feature_cols).issubset(fields):
                raise ValueError(
                    "Features CSV must include label and: " + ", ".join(feature_cols)
                )
            for row in reader:
                rows_x.append([float(row[col]) for col in feature_cols])
                rows_y.append(self._parse_label(row["label"]))

        if not rows_x:
            raise ValueError(f"No data rows in {csv_path}")
        return self.train_from_feature_rows(
            np.array(rows_x, dtype=float),
            np.array(rows_y, dtype=int),
            save=save,
        )

    @staticmethod
    def _parse_label(value: str) -> int:
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y", "match"}:
            return 1
        if text in {"0", "false", "no", "n", "mismatch"}:
            return 0
        raise ValueError(f"Unrecognized label value: {value!r}")
    
    def save_model(self):
        """Save the trained model and scaler."""
        if not self.sklearn_available or not self.is_trained:
            return
        
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self):
        """Load a saved model and scaler."""
        if not self.sklearn_available or not os.path.exists(self.model_path):
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data.get('is_trained', False)
            
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.is_trained = False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the trained model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.sklearn_available or not self.is_trained:
            return {}
        
        try:
            # For logistic regression, use absolute coefficients as importance
            importance = np.abs(self.model.coef_[0])
            
            feature_names = [
                'house_number_sim', 'street_sim', 'city_sim', 'postal_code_sim',
                'state_sim', 'country_sim', 'completeness_score', 'avg_similarity',
                'overall_similarity', 'geo_similarity', 'within_50m_threshold'
            ]
            
            return dict(zip(feature_names, importance))
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {} 