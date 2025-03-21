from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from .models import SubscriptionPlan


def init_subscription_plans(db: Session) -> list[SubscriptionPlan]:
    """
    Create three sample subscription plans in the database.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        List of created SubscriptionPlan instances
    """
    
    plans = [
        SubscriptionPlan(
            name="Basic",
            description="Основной пакет с 100 постами",
            price=Decimal("299.00"),
            currency="RUB",
            credits=100,
            duration_in_days=30
        ),
        SubscriptionPlan(
            name="Standard",
            description="Расширенный пакет с 300 постами",
            price=Decimal("699.00"),
            currency="RUB",
            credits=300,
            duration_in_days=30
        ),
        SubscriptionPlan(
            name="Premium",
            description="Премиум пакет с 1000 постами",
            price=Decimal("2699.00"),
            currency="RUB",
            credits=1000,
            duration_in_days=30
        )
    ]
    
    # Add plans to the session
    for plan in plans:
        db.add(plan)
    
    # Commit the session to save plans to the database
    db.commit()
    
    # Refresh plans to ensure they have IDs assigned
    for plan in plans:
        db.refresh(plan)
    
    return plans
