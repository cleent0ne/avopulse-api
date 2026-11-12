import abc
import asyncio
import random
import string
from datetime import datetime
from typing import Dict, Any

class PaymentProvider(abc.ABC):
    @abc.abstractmethod
    async def disburse(self, phone: str, amount: float, reference: str) -> Dict[str, Any]:
        """Disburse payment to a mobile recipient and return receipt details."""
        pass

class SimulatedMpesa(PaymentProvider):
    """
    Simulated M-Pesa B2C provider.
    Delivers realistic 1.5-second async delay and generates validly formatted M-Pesa receipt codes.
    Prevents Wi-Fi/sandbox failure risks during live hackathon demos.
    """
    def __init__(self, simulated_delay_seconds: float = 1.5):
        self.delay = simulated_delay_seconds

    async def disburse(self, phone: str, amount: float, reference: str) -> Dict[str, Any]:
        await asyncio.sleep(self.delay)
        
        # Format receipt code: 2 uppercase letters + 2 digits + 3 uppercase + 3 alphanumeric
        prefix = "".join(random.choices(string.ascii_uppercase, k=2))
        digits = "".join(random.choices(string.digits, k=2))
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        receipt = f"{prefix}{digits}{suffix}"
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        return {
            "status": "SUCCESS",
            "receipt": receipt,
            "phone": phone,
            "amount": round(amount, 2),
            "currency": "KES",
            "reference": reference,
            "timestamp": timestamp,
            "message": f"KES {amount:,.2f} sent to {phone}. Transaction ID: {receipt}. Balance updated."
        }

# Global payment provider instance
payment_service: PaymentProvider = SimulatedMpesa()

