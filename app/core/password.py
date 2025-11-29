"""Password hashing service - Injectable dependency following DIP."""

import bcrypt


class PasswordHasher:
    """
    Password hashing service using bcrypt.

    Following Dependency Inversion Principle:
    - Can be injected as dependency
    - Can be mocked for testing
    - Configuration can be changed without modifying code

    Note: Bcrypt has a 72-byte limit on passwords. Longer passwords are
    automatically truncated to ensure compatibility.
    """

    def __init__(self, rounds: int = 12):
        """
        Initialize password hasher.

        Args:
            rounds: Number of bcrypt rounds (cost factor). Default is 12.
                   Higher values = more secure but slower. Range: 4-31.
        """
        self.rounds = rounds

    def hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password as a string

        Note:
            Bcrypt has a 72-byte limit. Passwords are truncated if needed.
        """
        # Encode password to bytes and truncate to 72 bytes for bcrypt compatibility
        password_bytes = password.encode('utf-8')[:72]

        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)

        # Return as string
        return hashed.decode('utf-8')

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password (from database)

        Returns:
            True if password matches, False otherwise
        """
        try:
            # Encode and truncate password
            password_bytes = plain_password.encode('utf-8')[:72]
            hashed_bytes = hashed_password.encode('utf-8')

            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False

    def needs_update(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.

        Args:
            hashed_password: Current hash

        Returns:
            True if the hash was created with fewer rounds than configured
        """
        try:
            # Extract the cost factor from the hash
            # Bcrypt hash format: $2b$rounds$salthash
            parts = hashed_password.split('$')
            if len(parts) >= 3:
                hash_rounds = int(parts[2])
                return hash_rounds < self.rounds
        except (ValueError, IndexError):
            pass

        return False


# Default instance (can be overridden via dependency injection)
password_hasher = PasswordHasher()
