from sqlalchemy.orm import Session

from app.models.location import Location
from app.schemas.issue import LocationInput


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: LocationInput) -> Location:
        location = Location(
            latitude=payload.latitude,
            longitude=payload.longitude,
            address_text=payload.address_text,
            landmark=payload.landmark,
            ward=payload.ward,
            city=payload.city,
            pincode=payload.pincode,
        )
        self.db.add(location)
        self.db.flush()
        return location
