import hashlib
import hmac
from typing import Any, Dict, Optional


def sha256(data: bytes):
    """Compute the SHA-256 hash of data and return as hex string."""
    return hashlib.sha256(data).hexdigest()


class Transaction:
    """
    Simple transaction for an art ownership registry.

    Fields:
      - sender: public key or identifier of the sender ("MINT" for artwork creation)
      - recipient: public key or identifier of the recipient
      - artwork_id: unique string identifying the artwork
      - signature: HMAC-SHA256 signature of the transaction data using sender as key
    """
    def __init__(self, sender, recipient, artwork_id, signature):
        """
        Initialize the transaction.
        """
        self.sender = sender
        self.recipient = recipient
        self.artwork_id = artwork_id
        self.signature = signature


    def signature_message(self):
        """
        Construct the canonical message string for signing and hashing.

        Returns:
            str: concatenation of sender, recipient, and artwork_id
        """
        return f"{self.sender}|{self.recipient}|{self.artwork_id}"


    def hash(self):
        """
        Compute the SHA-256 hash of the transaction payload (excluding signature).

        Returns:
            str: hex-encoded hash of the transaction data
        """
        data = self.signature_message().encode()
        return sha256(data)


    def sign(self, sender_key):
        """
        Generate and store an HMAC-SHA256 signature using the sender_key.

        Args:
            sender_key (str): the secret key to sign with (in practice, private key)

        Returns:
            None
        """
        msg = self.signature_message().encode()
        # Use HMAC with sender_key as the key
        sig = hmac.new(sender_key.encode(), msg, hashlib.sha256).hexdigest()
        self.signature = sig


    def verify_signature(self):
        """
        Verify the stored signature against the transaction data and sender identifier.

        Returns:
            bool: True if signature matches, False otherwise
        """
        if not self.signature:
            return False
        expected = hmac.new(self.sender.encode(), self.signature_message().encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)


    def to_dict(self):
        """
        Serialize the transaction to a dictionary.

        Returns:
            dict: with keys sender, recipient, artwork_id, signature
        """
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "artwork_id": self.artwork_id,
            "signature": self.signature or ""
        }


    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Deserialize a dictionary to a Transaction object.

        Args:
            data (dict): dictionary with keys sender, recipient, artwork_id, signature

        Returns:
            Transaction: reconstructed transaction instance
        """
        return cls(
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            artwork_id=data.get("artwork_id", ""),
            signature=data.get("signature", "")
        )

    def __repr__(self) -> str:
        return (
            f"Tx(sender={self.sender}, recipient={self.recipient}, "
            f"artwork_id={self.artwork_id}, sig={self.signature[:8]}... )"
        )
