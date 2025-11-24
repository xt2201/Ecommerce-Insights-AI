"""Personalized product scoring based on user preferences."""

from typing import Dict, List, Any, Union

from ai_server.schemas.memory_models import UserPreferences


class PersonalizedScorer:
    """Score products based on user preferences and learned patterns."""
    
    @staticmethod
    def _get_attr(prefs: Union[UserPreferences, Dict[str, Any]], attr: str, default=None):
        """Get attribute from either UserPreferences object or dict.
        
        Args:
            prefs: UserPreferences object or dict
            attr: Attribute name
            default: Default value if not found
            
        Returns:
            Attribute value or default
        """
        if isinstance(prefs, dict):
            return prefs.get(attr, default)
        else:
            return getattr(prefs, attr, default)
    
    @staticmethod
    def score_product(
        product: Dict,
        user_preferences: Union[UserPreferences, Dict[str, Any]],
        base_score: float = 0.5
    ) -> float:
        """Calculate personalized score for a product.
        
        Args:
            product: Product dictionary
            user_preferences: User's learned preferences (UserPreferences object or dict)
            base_score: Base score (e.g., from value calculation)
            
        Returns:
            Personalized score (0-1)
        """
        # Get confidence
        confidence = PersonalizedScorer._get_attr(user_preferences, 'confidence', 0.0)
            
        if confidence < 0.3:
            # Not enough preference data, return base score
            return base_score
        
        score = base_score
        adjustments = []
        
        # Brand preference boost/penalty
        brand = product.get("brand", "").strip()
        if brand:
            brand_adjustment = PersonalizedScorer._score_brand(brand, user_preferences)
            score += brand_adjustment
            if brand_adjustment != 0:
                adjustments.append(f"brand({brand}): {brand_adjustment:+.2f}")
        
        # Feature preference boost
        feature_adjustment = PersonalizedScorer._score_features(product, user_preferences)
        score += feature_adjustment
        if feature_adjustment != 0:
            adjustments.append(f"features: {feature_adjustment:+.2f}")
        
        # Price preference
        price_adjustment = PersonalizedScorer._score_price(product, user_preferences)
        score += price_adjustment
        if price_adjustment != 0:
            adjustments.append(f"price: {price_adjustment:+.2f}")
        
        # Rating preference
        rating_adjustment = PersonalizedScorer._score_rating(product, user_preferences)
        score += rating_adjustment
        if rating_adjustment != 0:
            adjustments.append(f"rating: {rating_adjustment:+.2f}")
        
        # Clamp to 0-1
        score = max(0.0, min(1.0, score))
        
        # Add personalization metadata
        product["personalization"] = {
            "personalized_score": score,
            "base_score": base_score,
            "adjustments": adjustments,
            "preference_confidence": confidence
        }
        
        return score
    
    @staticmethod
    def _score_brand(brand: str, user_prefs: Union[UserPreferences, Dict[str, Any]]) -> float:
        """Score brand preference.
        
        Args:
            brand: Product brand
            user_prefs: User preferences
            
        Returns:
            Adjustment to score (-0.2 to +0.2)
        """
        brand_lower = brand.lower()
        
        # Get liked/disliked brands
        liked_brands = PersonalizedScorer._get_attr(user_prefs, 'liked_brands', {})
        disliked_brands = PersonalizedScorer._get_attr(user_prefs, 'disliked_brands', {})
        
        # Check liked brands
        for liked_brand, confidence in liked_brands.items():
            if liked_brand.lower() in brand_lower or brand_lower in liked_brand.lower():
                # Boost based on confidence
                return min(0.2, confidence * 0.3)
        
        # Check disliked brands
        for disliked_brand, confidence in disliked_brands.items():
            if disliked_brand.lower() in brand_lower or brand_lower in disliked_brand.lower():
                # Penalty based on confidence
                return -min(0.2, confidence * 0.3)
        
        return 0.0
    
    @staticmethod
    def _score_features(product: Dict, user_prefs: Union[UserPreferences, Dict[str, Any]]) -> float:
        """Score feature preferences.
        
        Args:
            product: Product dictionary
            user_prefs: User preferences
            
        Returns:
            Adjustment to score (0 to +0.3)
        """
        must_have = PersonalizedScorer._get_attr(user_prefs, 'must_have_features', {})
        nice_to_have = PersonalizedScorer._get_attr(user_prefs, 'nice_to_have_features', {})
        
        if not must_have and not nice_to_have:
            return 0.0
        
        # Get product features (from title, description, or features field)
        product_text = " ".join([
            str(product.get("title", "")),
            str(product.get("description", "")),
            str(product.get("features", ""))
        ]).lower()
        
        score_adjustment = 0.0
        
        # Check must-have features
        for feature, confidence in must_have.items():
            if feature.lower() in product_text:
                # Strong boost for must-have features
                score_adjustment += min(0.15, confidence * 0.2)
        
        # Check nice-to-have features
        for feature, confidence in nice_to_have.items():
            if feature.lower() in product_text:
                # Smaller boost for nice-to-have
                score_adjustment += min(0.05, confidence * 0.1)
        
        return min(0.3, score_adjustment)
    
    @staticmethod
    def _score_price(product: Dict, user_prefs: Union[UserPreferences, Dict[str, Any]]) -> float:
        """Score price preference.
        
        Args:
            product: Product dictionary
            user_prefs: User preferences
            
        Returns:
            Adjustment to score (-0.1 to +0.1)
        """
        price = product.get("price")
        if price is None or not isinstance(price, (int, float)):
            return 0.0
        
        # Get price preferences
        preferred_price_range = PersonalizedScorer._get_attr(user_prefs, 'preferred_price_range')
        max_budget = PersonalizedScorer._get_attr(user_prefs, 'max_budget')
        
        # Check against preferred price range
        if preferred_price_range:
            min_price, max_price = preferred_price_range
            
            if min_price <= price <= max_price:
                # Perfect match
                return 0.1
            elif price < min_price:
                # Too cheap (might be suspicious)
                return -0.05
            elif price > max_price * 1.2:
                # Too expensive
                return -0.1
            else:
                # Slightly over range
                return -0.03
        
        # Check against max budget
        if max_budget:
            if price <= max_budget:
                # Within budget
                return 0.05
            else:
                # Over budget - penalty
                overage_ratio = (price - max_budget) / max_budget
                return -min(0.1, overage_ratio * 0.2)
        
        return 0.0
    
    @staticmethod
    def _score_rating(product: Dict, user_prefs: Union[UserPreferences, Dict[str, Any]]) -> float:
        """Score rating preference.
        
        Args:
            product: Product dictionary
            user_prefs: User preferences
            
        Returns:
            Adjustment to score (-0.1 to +0.1)
        """
        rating = product.get("rating")
        if rating is None or not isinstance(rating, (int, float)):
            return 0.0
        
        min_rating = PersonalizedScorer._get_attr(user_prefs, 'min_rating')
        
        if min_rating:
            if rating >= min_rating:
                # Meets minimum rating
                excess = rating - min_rating
                return min(0.1, excess * 0.05)
            else:
                # Below minimum rating
                deficit = min_rating - rating
                return -min(0.1, deficit * 0.1)
        
        return 0.0
    
    @staticmethod
    def rerank_products(
        products: List[Dict],
        user_preferences: Union[UserPreferences, Dict[str, Any]]
    ) -> List[Dict]:
        """Rerank products based on personalized scores.
        
        Args:
            products: List of products with base scores
            user_preferences: User's learned preferences
            
        Returns:
            Reranked list of products
        """
        confidence = PersonalizedScorer._get_attr(user_preferences, 'confidence', 0.0) or 0.0
        
        if confidence < 0.3:
            # Not enough data for personalization
            return products
        
        # Score each product
        for product in products:
            base_score = product.get("value_score", 0.5)
            personalized_score = PersonalizedScorer.score_product(
                product,
                user_preferences,
                base_score
            )
            product["personalized_score"] = personalized_score
        
        # Rerank by personalized score
        reranked = sorted(
            products,
            key=lambda p: p.get("personalized_score", 0),
            reverse=True
        )
        
        return reranked
