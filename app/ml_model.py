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
    import pandas as pd
    SKLEARN_AVAILABLE = True
    logger.info("Scikit-learn library is available")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn library not available, ML model disabled")

from app.models import ComponentSimilarities


class AddressMatchingMLModel:
    """
    ML model stub for address matching entity resolution.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the ML model.
        
        Args:
            model_path: Path to saved model file
        """
        self.sklearn_available = SKLEARN_AVAILABLE
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.model_path = model_path or "address_matching_model.pkl"
        
        if self.sklearn_available:
            self.model = LogisticRegression(random_state=42)
            self.scaler = StandardScaler()
            
            # Try to load existing model
            if self.model_path and os.path.exists(self.model_path):
                self.load_model()
            else:
                logger.info("No existing model found, will train with synthetic data")
                self._train_with_synthetic_data()
        else:
            logger.warning("ML model functionality disabled due to missing dependencies")
    
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
            features.append(1.0 if geospatial_distance <= 50 else 0.0)  # Within 50m threshold
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