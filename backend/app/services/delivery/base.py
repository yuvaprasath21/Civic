from abc import ABC, abstractmethod


class DeliveryError(Exception):
    """Raised when a provider fails to deliver a message."""


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, body: str) -> None: ...


class SMSProvider(ABC):
    @abstractmethod
    def send(self, to_number: str, body: str) -> None: ...
