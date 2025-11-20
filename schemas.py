"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional

# Auth/User schema for Trust Cars 4U
class UserAuth(BaseModel):
    """
    Collection name: "userauth"
    Stores user account info. Passwords are stored as salted hashes.
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="SHA256(salt+password) hex digest")
    salt: str = Field(..., description="Per-user random salt (hex)")


class Appointment(BaseModel):
    """
    Collection name: "appointment"
    Stores appointment bookings for test drives or service.
    """
    user_id: str = Field(..., description="ID of the user who booked")
    name: str = Field(..., description="Customer name")
    phone: str = Field(..., description="Phone number")
    car_model: str = Field(..., description="Car model for test drive/service")
    datetime_iso: str = Field(..., description="ISO datetime string for appointment")
    purpose: str = Field(..., description="Purpose: Test Drive or Service or other")

# Example schemas from template retained for reference
class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
