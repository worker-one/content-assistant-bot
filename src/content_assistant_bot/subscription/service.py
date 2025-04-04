import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..auth.models import User
from .models import Payment, Subscription, SubscriptionPlan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_subscription_plan(
    db_session: Session,
    name: str,
    price: float, currency: str,
    duration_in_days: int,
    description: Optional[str] = None
    ) -> SubscriptionPlan:
    plan = SubscriptionPlan(
        name=name, description=description,
        price=price, currency=currency,
        duration_in_days=duration_in_days
    )
    db_session.expire_on_commit = False
    db_session.add(plan)
    db_session.commit()
    db_session.close()
    return plan


def get_subscription_plan(db_session: Session, plan_id: int) -> Optional[SubscriptionPlan]:
    plan = db_session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    db_session.close()
    return plan


def get_subscription_plans(db_session: Session, plan_name: Optional[str] = None) -> Optional[list[SubscriptionPlan]]:
    if plan_name:
        plans = db_session.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).all()
    else:
        plans = db_session.query(SubscriptionPlan).all()
    db_session.close()
    return plans


def update_subscription_plan(
    db_session: Session,
    plan_id: int,
    name: Optional[str]=None,
    price: Optional[float]=None,
    currency: Optional[str]=None,
    duration_in_days: Optional[int]=None
    ) -> Optional[SubscriptionPlan]:
    plan = db_session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if plan:
        if name is not None:
            plan.name = name
        if price is not None:
            plan.price = price
        if currency is not None:
            plan.currency = currency
        if duration_in_days is not None:
            plan.duration_in_days = duration_in_days
        db_session.commit()
    db_session.close()
    return plan


def delete_subscription_plan(db_session: Session, plan_id: int):
    plan = db_session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if plan:
        db_session.delete(plan)
        db_session.commit()
    db_session.close()


# Subscription CRUD operations
def create_subscription(db_session: Session, user_id: int, plan_id: int, status: str = "active") -> Subscription:
    plan = get_subscription_plan(db_session, plan_id)
    if not plan:
        raise ValueError("Subscription plan not found")
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=plan.duration_in_days),
        status=status
    )
    db_session.expire_on_commit = False
    db_session.add(subscription)

    logger.info(f"Subscription created for user {user_id} with plan {plan.name}")

    db_session.commit()
    db_session.close()
    return subscription


def get_subscriptions_by_user_id(db_session: Session, user_id: int) -> Optional[list[Subscription]]:
    subscriptions = db_session.query(Subscription).filter(Subscription.user_id == user_id).all()
    db_session.close()
    return subscriptions


def update_subscription(db_session: Session, subscription_id: int, status: Optional[str]=None, end_date: Optional[datetime]=None) -> Optional[Subscription]:
    subscription = db_session.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription:
        if status is not None:
            subscription.status = status
        if end_date is not None:
            subscription.end_date = end_date
        db_session.commit()
    db_session.close()
    return subscription


def get_active_subscriptions_by_user_id(db_session: Session, user_id: int) -> Optional[list[Subscription]]:

    # Fetch the subscriptions
    active_subscriptions = (
        db_session.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .filter(Subscription.status.in_(["active"]))  # Relevant statuses
        .all()
    )

    db_session.commit()
    db_session.close()
    return active_subscriptions if active_subscriptions else None


def update_subscription_statuses(db_session: Session, user_id: int) -> None:
    current_date = datetime.now()
    subscriptions = db_session.query(Subscription).filter(
        Subscription.user_id == user_id
    ).all()

    for subscription in subscriptions:
        if subscription.status == "active" and subscription.end_date < current_date:
            subscription.status = "inactive"
            logger.info(f"Subscription {subscription.id} has expired")
        elif subscription.status == "inactive" and subscription.end_date > current_date:
            subscription.status = "active"
            logger.info(f"Subscription {subscription.id} has been reactivated")

    db_session.commit()
    db_session.close()


def delete_subscription(db_session: Session, subscription_id: int):
    subscription = db_session.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription:
        db_session.delete(subscription)
        db_session.commit()
    db_session.close()


def credit_balance(db_session: Session, user_id: int, amount: float) -> None:
    user = db_session.query(User).filter(User.id == user_id).first()
    if user:
        user.balance += amount
        db_session.commit()
    db_session.close()


def create_payment(
    db_session: Session,
    subscription_id: int,
    amount: float,
    currency: str,
    payment_date: datetime,
    payment_method: str
    ) -> Payment:
    payment = Payment(
        subscription_id=subscription_id,
        amount=amount,
        currency=currency,
        payment_date=payment_date,
        payment_method=payment_method
    )
    db_session.add(payment)
    db_session.commit()
    db_session.close()
    return payment


def get_payment(db_session: Session, payment_id: int) -> Optional[Payment]:
    payment = db_session.query(Payment).filter(Payment.id == payment_id).first()
    db_session.close()
    return payment


def update_payment(db_session: Session, payment_id: int, amount: Optional[float]=None, payment_method: Optional[str]=None) -> Optional[Payment]:
    payment = db_session.query(Payment).filter(Payment.id == payment_id).first()
    if payment:
        if amount is not None:
            payment.amount = amount
        if payment_method is not None:
            payment.payment_method = payment_method
        db_session.commit()
    db_session.close()
    return payment


def delete_payment(db_session: Session, payment_id: int):
    payment = db_session.query(Payment).filter(Payment.id == payment_id).first()
    if payment:
        db_session.delete(payment)
        db_session.commit()
    db_session.close()