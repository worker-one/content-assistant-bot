from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String

from ..models import Base, TimeStampMixin

class SubscriptionPlan(Base, TimeStampMixin):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2))
    currency = Column(String, default="RUB")
    credits = Column(Integer)
    duration_in_days = Column(Integer)


class Subscription(Base, TimeStampMixin):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    remaining_credits = Column(Integer)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(Enum("active", "inactive", "canceled", name="subscription_status"))


class Payment(Base, TimeStampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Numeric(10, 2))
    currency = Column(String)
    payment_date = Column(DateTime)
    payment_method = Column(String)

