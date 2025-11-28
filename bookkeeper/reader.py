"""Read transactions from Quicken SQLite database."""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# Core Data reference date (Jan 1, 2001 00:00:00 UTC)
CORE_DATA_EPOCH = 978307200


def core_data_timestamp_to_date(timestamp: float) -> date:
    """
    Convert Core Data timestamp to Python date.

    Core Data uses seconds since Jan 1, 2001 (not Unix epoch).

    Args:
        timestamp: Core Data timestamp

    Returns:
        Python date object
    """
    unix_timestamp = timestamp + CORE_DATA_EPOCH
    return datetime.fromtimestamp(unix_timestamp).date()


@dataclass
class Transaction:
    """Represents a single transaction from Quicken."""

    id: int
    date: date
    payee: str
    amount: float
    category: Optional[str]
    memo: Optional[str]
    account_id: int
    # Additional fields useful for classification
    reference: Optional[str]
    check_number: Optional[str]
    # Store all raw data for ML/LLM classification
    raw_data: dict


class QuickenReader:
    """Reads transactions from Quicken SQLite database."""

    def __init__(self, quicken_file: Path):
        """
        Initialize reader for a Quicken file.

        Args:
            quicken_file: Path to .quicken file (package containing SQLite DB)
        """
        self.quicken_file = quicken_file
        self.db_path = self._find_database(quicken_file)

    def _find_database(self, quicken_file: Path) -> Path:
        """
        Find the SQLite database inside the .quicken package.

        Args:
            quicken_file: Path to .quicken file

        Returns:
            Path to SQLite database file
        """
        # .quicken files are actually packages (directories)
        # The SQLite database is named "data"
        if quicken_file.is_dir():
            db_path = quicken_file / "data"
            if db_path.exists():
                return db_path

        raise ValueError(f"Could not find SQLite database in {quicken_file}")

    def read_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_types: Optional[list[str]] = None,
    ) -> list[Transaction]:
        """
        Read transactions from the database.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            account_types: Optional list of account types to include
                          (e.g., ['CHECKING', 'CREDITCARD'])

        Returns:
            List of Transaction objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Join transactions with payees, categories, and accounts
            query = """
                SELECT
                    t.Z_PK as id,
                    t.ZENTEREDDATE as entered_date,
                    t.ZPOSTEDDATE as posted_date,
                    t.ZAMOUNT as amount,
                    t.ZNOTE as note,
                    t.ZREFERENCE as reference,
                    t.ZCHECKNUMBER as check_number,
                    t.ZACCOUNT as account_id,
                    p.ZNAME as payee_name,
                    c.ZNAME as category_name,
                    cfte.Z_PK as cashflow_entry_id,
                    a.ZNAME as account_name,
                    a.ZTYPENAME as account_type
                FROM ZTRANSACTION t
                LEFT JOIN ZUSERPAYEE p ON t.ZUSERPAYEE = p.Z_PK
                LEFT JOIN ZCASHFLOWTRANSACTIONENTRY cfte ON cfte.ZPARENT = t.Z_PK
                LEFT JOIN ZTAG c ON cfte.ZCATEGORYTAG = c.Z_PK
                LEFT JOIN ZACCOUNT a ON t.ZACCOUNT = a.Z_PK
                WHERE t.ZAMOUNT IS NOT NULL
            """
            params = []

            # Build filters
            conditions = []

            # Account type filter
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                conditions.append(f"a.ZTYPENAME IN ({placeholders})")
                params.extend(account_types)
            # Date filters
            if start_date:
                # Convert Python date to Core Data timestamp
                start_dt = datetime.combine(start_date, datetime.min.time())
                start_timestamp = start_dt.timestamp() - CORE_DATA_EPOCH
                conditions.append("t.ZENTEREDDATE >= ?")
                params.append(start_timestamp)

            if end_date:
                # Convert Python date to Core Data timestamp
                end_dt = datetime.combine(end_date, datetime.max.time())
                end_timestamp = end_dt.timestamp() - CORE_DATA_EPOCH
                conditions.append("t.ZENTEREDDATE <= ?")
                params.append(end_timestamp)

            # Apply all conditions
            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY t.ZENTEREDDATE DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Convert to Transaction objects
            transactions = []
            for row in rows:
                # Use posted date if available, otherwise entered date
                timestamp = row["posted_date"] if row["posted_date"] else row["entered_date"]
                trans_date = core_data_timestamp_to_date(timestamp) if timestamp else date.today()

                transactions.append(Transaction(
                    id=row["id"],
                    date=trans_date,
                    payee=row["payee_name"] or "Unknown",
                    amount=row["amount"],
                    category=row["category_name"],
                    memo=row["note"],
                    account_id=row["account_id"],
                    reference=row["reference"],
                    check_number=row["check_number"],
                    raw_data=dict(row),
                ))

            return transactions

        finally:
            conn.close()

    def get_all_categories(self) -> list[str]:
        """
        Get all user-assignable categories from the database.

        Returns:
            List of category names
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT ZNAME FROM ZTAG WHERE ZUSERASSIGNABLE = 1 ORDER BY ZNAME"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_accounts(self) -> dict[str, list[str]]:
        """
        Get all accounts grouped by account type.

        Returns:
            Dictionary mapping account type -> list of account names
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT ZTYPENAME, ZNAME
                FROM ZACCOUNT
                WHERE ZTYPENAME IS NOT NULL
                ORDER BY ZTYPENAME, ZNAME
                """
            )

            accounts_by_type = {}
            for row in cursor.fetchall():
                account_type = row[0]
                account_name = row[1]

                if account_type not in accounts_by_type:
                    accounts_by_type[account_type] = []
                accounts_by_type[account_type].append(account_name)

            return accounts_by_type
        finally:
            conn.close()
