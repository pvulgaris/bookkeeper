"""Write category updates back to Quicken SQLite database."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class QuickenWriter:
    """Writes category updates to Quicken SQLite database."""

    def __init__(self, db_path: Path):
        """
        Initialize writer for a Quicken database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def _get_category_id(self, conn: sqlite3.Connection, category_name: str) -> Optional[int]:
        """
        Get the Z_PK for a category by name.

        Args:
            conn: Database connection
            category_name: Name of the category

        Returns:
            Category ID (Z_PK) or None if not found
        """
        cursor = conn.execute(
            "SELECT Z_PK FROM ZTAG WHERE ZNAME = ? AND ZUSERASSIGNABLE = 1",
            (category_name,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_or_create_cashflow_entry(
        self, conn: sqlite3.Connection, transaction_id: int
    ) -> int:
        """
        Get existing cashflow entry for a transaction, or create one.

        Args:
            conn: Database connection
            transaction_id: Transaction Z_PK

        Returns:
            Cashflow entry Z_PK
        """
        # Check if cashflow entry already exists
        cursor = conn.execute(
            "SELECT Z_PK FROM ZCASHFLOWTRANSACTIONENTRY WHERE ZPARENT = ?",
            (transaction_id,)
        )
        row = cursor.fetchone()

        if row:
            return row[0]

        # Create new cashflow entry
        # Get the transaction amount for the entry
        cursor = conn.execute(
            "SELECT ZAMOUNT FROM ZTRANSACTION WHERE Z_PK = ?", (transaction_id,)
        )
        amount_row = cursor.fetchone()
        amount = amount_row[0] if amount_row else 0

        # Get next Z_PK for cashflow entry table
        cursor = conn.execute("SELECT MAX(Z_PK) FROM ZCASHFLOWTRANSACTIONENTRY")
        max_pk = cursor.fetchone()[0] or 0
        new_pk = max_pk + 1

        # Insert new cashflow entry
        conn.execute(
            """
            INSERT INTO ZCASHFLOWTRANSACTIONENTRY
            (Z_PK, Z_ENT, Z_OPT, ZPARENT, ZAMOUNT, ZSEQUENCENUMBER)
            VALUES (?, 80, 1, ?, ?, 0)
            """,
            (new_pk, transaction_id, amount)
        )

        return new_pk

    def update_category(self, transaction_id: int, category_name: str) -> bool:
        """
        Update the category for a single transaction.

        Args:
            transaction_id: ID of transaction to update (Z_PK from ZTRANSACTION)
            category_name: Name of the category

        Returns:
            True if successful, False if category not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Get category ID
            category_id = self._get_category_id(conn, category_name)
            if category_id is None:
                return False

            # Get or create cashflow entry
            cashflow_entry_id = self._get_or_create_cashflow_entry(conn, transaction_id)

            # Update the category
            conn.execute(
                "UPDATE ZCASHFLOWTRANSACTIONENTRY SET ZCATEGORYTAG = ? WHERE Z_PK = ?",
                (category_id, cashflow_entry_id)
            )

            conn.commit()
            return True

        finally:
            conn.close()

    def update_categories(self, updates: dict[int, str]) -> dict[int, bool]:
        """
        Batch update categories for multiple transactions.

        Args:
            updates: Dictionary mapping transaction_id -> new_category_name

        Returns:
            Dictionary mapping transaction_id -> success status
        """
        conn = sqlite3.connect(self.db_path)
        results = {}

        try:
            for transaction_id, category_name in updates.items():
                # Get category ID
                category_id = self._get_category_id(conn, category_name)
                if category_id is None:
                    results[transaction_id] = False
                    continue

                # Get or create cashflow entry
                cashflow_entry_id = self._get_or_create_cashflow_entry(conn, transaction_id)

                # Update the category
                conn.execute(
                    "UPDATE ZCASHFLOWTRANSACTIONENTRY SET ZCATEGORYTAG = ? WHERE Z_PK = ?",
                    (category_id, cashflow_entry_id)
                )

                results[transaction_id] = True

            conn.commit()
            return results

        finally:
            conn.close()
