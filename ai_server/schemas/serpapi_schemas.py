"""
SerpAPI Response Validation Schemas

Versioned Pydantic schemas for validating SerpAPI responses.
Provides strict typing, default values, and migration support.

Version History:
- v1.0.0: Initial schema based on observed API responses
- v1.1.0: Added optional fields for new API features
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import logging

logger = logging.getLogger(__name__)

# Schema version for migration tracking
SCHEMA_VERSION = "1.1.0"


class SchemaVersion(str, Enum):
    """Supported schema versions for backward compatibility."""
    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"
    CURRENT = "1.1.0"


# ============== Product Schemas ==============

class ProductPrice(BaseModel):
    """Price information with currency support."""
    
    raw: Optional[str] = Field(None, description="Raw price string (e.g., '$29.99')")
    value: Optional[float] = Field(None, description="Numeric price value")
    currency: str = Field(default="USD", description="Currency code")
    
    @field_validator('value', mode='before')
    @classmethod
    def parse_price_value(cls, v: Any) -> Optional[float]:
        """Convert string prices to float."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Remove currency symbols and parse
            cleaned = v.replace('$', '').replace(',', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not parse price value: {v}")
                return None
        return None
    
    @field_validator('currency', mode='before')
    @classmethod
    def normalize_currency(cls, v: Any) -> str:
        """Normalize currency codes."""
        if v is None:
            return "USD"
        return str(v).upper()[:3]


class ProductRating(BaseModel):
    """Product rating information."""
    
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating (0-5)")
    reviews_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    
    @field_validator('rating', mode='before')
    @classmethod
    def parse_rating(cls, v: Any) -> Optional[float]:
        """Parse rating from various formats."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return min(5.0, max(0.0, float(v)))
        if isinstance(v, str):
            try:
                # Handle "4.5 out of 5" format
                if 'out of' in v.lower():
                    v = v.split()[0]
                return min(5.0, max(0.0, float(v)))
            except ValueError:
                return None
        return None
    
    @field_validator('reviews_count', mode='before')
    @classmethod
    def parse_reviews_count(cls, v: Any) -> Optional[int]:
        """Parse review count from various formats."""
        if v is None:
            return None
        if isinstance(v, int):
            return max(0, v)
        if isinstance(v, str):
            # Handle "1,234 reviews" format
            cleaned = v.replace(',', '').split()[0]
            try:
                return max(0, int(cleaned))
            except ValueError:
                return None
        return None


class ProductImage(BaseModel):
    """Product image information."""
    
    link: Optional[str] = Field(None, description="Image URL")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    
    @field_validator('link', 'thumbnail', mode='before')
    @classmethod
    def validate_url(cls, v: Any) -> Optional[str]:
        """Basic URL validation."""
        if v is None or v == "":
            return None
        v = str(v)
        if v.startswith(('http://', 'https://', '//')):
            return v
        return None


class ShippingInfo(BaseModel):
    """Shipping information."""
    
    is_free: bool = Field(default=False, description="Whether shipping is free")
    is_prime: bool = Field(default=False, description="Whether Prime eligible")
    delivery_estimate: Optional[str] = Field(None, description="Delivery time estimate")
    
    @model_validator(mode='before')
    @classmethod
    def parse_shipping(cls, data: Any) -> Dict[str, Any]:
        """Parse shipping from various formats."""
        if isinstance(data, dict):
            return data
        
        # Handle string format
        if isinstance(data, str):
            lower = data.lower()
            return {
                "is_free": "free" in lower,
                "is_prime": "prime" in lower,
                "delivery_estimate": data
            }
        
        return {"is_free": False, "is_prime": False}


class ProductResult(BaseModel):
    """Individual product result from search."""
    
    # Core fields
    title: str = Field(..., min_length=1, description="Product title")
    link: Optional[str] = Field(None, description="Product URL")
    asin: Optional[str] = Field(None, description="Amazon ASIN")
    
    # Price information
    price: Optional[ProductPrice] = None
    original_price: Optional[ProductPrice] = Field(None, description="Price before discount")
    
    # Ratings
    rating: Optional[ProductRating] = None
    
    # Images
    image: Optional[ProductImage] = None
    
    # Shipping
    shipping: Optional[ShippingInfo] = None
    
    # Metadata
    source: Optional[str] = Field(None, description="Data source (e.g., 'amazon')")
    position: Optional[int] = Field(None, ge=0, description="Result position")
    
    # Raw data for debugging
    _raw_data: Optional[Dict[str, Any]] = None
    
    @model_validator(mode='before')
    @classmethod
    def normalize_product_data(cls, data: Any) -> Dict[str, Any]:
        """Normalize product data from various API formats."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        result = {}
        
        # Title (required)
        result['title'] = data.get('title') or data.get('name') or data.get('product_title', '')
        
        # Link
        result['link'] = data.get('link') or data.get('url') or data.get('product_link')
        
        # ASIN
        result['asin'] = data.get('asin') or data.get('product_id')
        
        # Price
        if 'price' in data:
            price_data = data['price']
            if isinstance(price_data, dict):
                result['price'] = price_data
            else:
                result['price'] = {'raw': str(price_data), 'value': price_data}
        elif 'extracted_price' in data:
            result['price'] = {
                'raw': data.get('price_raw', str(data['extracted_price'])),
                'value': data['extracted_price']
            }
        
        # Rating
        if 'rating' in data or 'reviews' in data:
            result['rating'] = {
                'rating': data.get('rating') or data.get('stars'),
                'reviews_count': data.get('reviews') or data.get('reviews_count') or data.get('ratings_total')
            }
        
        # Image
        if 'thumbnail' in data or 'image' in data:
            result['image'] = {
                'thumbnail': data.get('thumbnail'),
                'link': data.get('image')
            }
        
        # Shipping
        if 'shipping' in data or 'is_prime' in data:
            result['shipping'] = {
                'is_prime': data.get('is_prime', False),
                'is_free': 'free' in str(data.get('shipping', '')).lower(),
                'delivery_estimate': data.get('delivery')
            }
        
        # Position
        result['position'] = data.get('position')
        
        # Source
        result['source'] = data.get('source', 'amazon')
        
        return result


# ============== Search Response Schemas ==============

class SearchMetadata(BaseModel):
    """Metadata about the search request."""
    
    query: str = Field(..., description="Original search query")
    total_results: Optional[int] = Field(None, ge=0, description="Total results available")
    page: int = Field(default=1, ge=1, description="Current page number")
    engine: str = Field(default="google_shopping", description="Search engine used")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                pass
        return datetime.utcnow()


class SerpAPISearchResponse(BaseModel):
    """Complete SerpAPI search response."""
    
    # Schema version for migration
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version")
    
    # Metadata
    metadata: SearchMetadata
    
    # Results
    products: List[ProductResult] = Field(default_factory=list, description="Product results")
    
    # Pagination
    has_more: bool = Field(default=False, description="Whether more results available")
    next_page_token: Optional[str] = Field(None, description="Token for next page")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if any")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    
    @model_validator(mode='before')
    @classmethod
    def normalize_response(cls, data: Any) -> Dict[str, Any]:
        """Normalize raw SerpAPI response to our schema."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        result = {
            'schema_version': SCHEMA_VERSION,
            'warnings': []
        }
        
        # Build metadata
        search_metadata = data.get('search_metadata', {})
        search_parameters = data.get('search_parameters', {})
        
        result['metadata'] = {
            'query': search_parameters.get('q', search_parameters.get('query', '')),
            'total_results': data.get('search_information', {}).get('total_results'),
            'page': int(search_parameters.get('page', 1)),
            'engine': search_metadata.get('engine', 'google_shopping'),
            'timestamp': search_metadata.get('created_at')
        }
        
        # Extract products from various locations
        products = []
        
        # Google Shopping format
        if 'shopping_results' in data:
            products.extend(data['shopping_results'])
        
        # Amazon format
        if 'organic_results' in data:
            products.extend(data['organic_results'])
        
        # Direct results
        if 'results' in data:
            products.extend(data['results'])
        
        result['products'] = products
        
        # Pagination
        if 'serpapi_pagination' in data:
            pagination = data['serpapi_pagination']
            result['has_more'] = 'next' in pagination
            result['next_page_token'] = pagination.get('next_page_token')
        
        # Error handling
        if 'error' in data:
            result['error'] = data['error']
        
        return result
    
    def get_valid_products(self) -> List[ProductResult]:
        """Return only products with valid essential data."""
        return [
            p for p in self.products
            if p.title and (p.price or p.link)
        ]
    
    def to_dict_for_llm(self) -> Dict[str, Any]:
        """Convert to dict format suitable for LLM consumption."""
        return {
            'query': self.metadata.query,
            'total_results': len(self.products),
            'products': [
                {
                    'title': p.title,
                    'price': p.price.raw if p.price else None,
                    'rating': p.rating.rating if p.rating else None,
                    'reviews': p.rating.reviews_count if p.rating else None,
                    'link': p.link,
                    'is_prime': p.shipping.is_prime if p.shipping else False
                }
                for p in self.products[:10]  # Limit for context window
            ]
        }


# ============== Review Schemas ==============

class ReviewAuthor(BaseModel):
    """Review author information."""
    
    name: str = Field(default="Anonymous", description="Author name")
    profile_link: Optional[str] = Field(None, description="Profile URL")
    verified_purchase: bool = Field(default=False, description="Whether verified purchase")


class ProductReview(BaseModel):
    """Individual product review."""
    
    title: Optional[str] = Field(None, description="Review title")
    body: str = Field(..., min_length=1, description="Review text")
    rating: float = Field(..., ge=0, le=5, description="Review rating")
    date: Optional[datetime] = Field(None, description="Review date")
    author: Optional[ReviewAuthor] = None
    helpful_votes: int = Field(default=0, ge=0, description="Helpful vote count")
    
    @field_validator('rating', mode='before')
    @classmethod
    def parse_rating(cls, v: Any) -> float:
        """Parse rating from various formats."""
        if isinstance(v, (int, float)):
            return min(5.0, max(0.0, float(v)))
        if isinstance(v, str):
            try:
                return min(5.0, max(0.0, float(v.split()[0])))
            except (ValueError, IndexError):
                return 0.0
        return 0.0


class ReviewSummary(BaseModel):
    """Aggregated review summary."""
    
    average_rating: float = Field(..., ge=0, le=5)
    total_reviews: int = Field(..., ge=0)
    rating_distribution: Dict[int, int] = Field(
        default_factory=lambda: {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    )
    
    @property
    def sentiment_score(self) -> float:
        """Calculate weighted sentiment score (-1 to 1)."""
        if self.total_reviews == 0:
            return 0.0
        # Normalize 0-5 rating to -1 to 1
        return (self.average_rating - 2.5) / 2.5


class ProductReviewsResponse(BaseModel):
    """Complete product reviews response."""
    
    schema_version: str = Field(default=SCHEMA_VERSION)
    product_asin: Optional[str] = None
    product_title: Optional[str] = None
    summary: Optional[ReviewSummary] = None
    reviews: List[ProductReview] = Field(default_factory=list)
    
    def get_top_reviews(self, n: int = 5) -> List[ProductReview]:
        """Get top N most helpful reviews."""
        return sorted(
            self.reviews,
            key=lambda r: r.helpful_votes,
            reverse=True
        )[:n]


# ============== Validation Utilities ==============

class ValidationResult(BaseModel):
    """Result of data validation."""
    
    is_valid: bool
    data: Optional[Union[SerpAPISearchResponse, ProductReviewsResponse]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def validate_search_response(raw_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate and parse raw SerpAPI search response.
    
    Args:
        raw_data: Raw response from SerpAPI
        
    Returns:
        ValidationResult with parsed data or errors
    """
    errors = []
    warnings = []
    
    try:
        # Attempt to parse with our schema
        response = SerpAPISearchResponse.model_validate(raw_data)
        
        # Check for empty results
        if len(response.products) == 0:
            warnings.append("No products found in response")
        
        # Check for missing prices
        products_without_price = sum(1 for p in response.products if not p.price)
        if products_without_price > len(response.products) * 0.5:
            warnings.append(f"{products_without_price}/{len(response.products)} products missing price")
        
        return ValidationResult(
            is_valid=True,
            data=response,
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        errors.append(str(e))
        
        return ValidationResult(
            is_valid=False,
            errors=errors
        )


def validate_reviews_response(raw_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate and parse raw reviews response.
    
    Args:
        raw_data: Raw response from reviews API
        
    Returns:
        ValidationResult with parsed data or errors
    """
    try:
        response = ProductReviewsResponse.model_validate(raw_data)
        return ValidationResult(is_valid=True, data=response)
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[str(e)])


# ============== Migration Utilities ==============

def migrate_schema(data: Dict[str, Any], from_version: str, to_version: str = SCHEMA_VERSION) -> Dict[str, Any]:
    """
    Migrate data between schema versions.
    
    Args:
        data: Data to migrate
        from_version: Source schema version
        to_version: Target schema version
        
    Returns:
        Migrated data
    """
    # For now, just validate with current schema (handles most cases)
    logger.info(f"Migrating schema from {from_version} to {to_version}")
    
    # Future: Add specific migration logic between versions
    # if from_version == "1.0.0" and to_version >= "1.1.0":
    #     data = _migrate_v1_0_to_v1_1(data)
    
    return data
