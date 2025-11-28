"""Transaction classification using ML and LLM."""

from typing import Optional

from anthropic import Anthropic

from .reader import Transaction


class TransactionClassifier:
    """Classifies transactions using ensemble approach: rules + ML + LLM."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize classifier.

        Args:
            api_key: Anthropic API key for LLM classification
        """
        self.client = Anthropic(api_key=api_key) if api_key else None
        # TODO: Load trained ML model if available
        self.ml_model = None

    def classify(self, transaction: Transaction, available_categories: list[str]) -> tuple[str, float]:
        """
        Classify a transaction and return suggested category with confidence.

        Args:
            transaction: Transaction to classify
            available_categories: List of valid categories from Quicken

        Returns:
            Tuple of (suggested_category, confidence_score)
        """
        # Try rule-based classification first
        rule_suggestion = self._apply_rules(transaction)
        if rule_suggestion:
            return rule_suggestion, 0.95

        # Try ML model if available
        if self.ml_model:
            ml_suggestion = self._classify_with_ml(transaction, available_categories)
            if ml_suggestion[1] > 0.8:  # High confidence threshold
                return ml_suggestion

        # Fall back to LLM for complex cases
        if self.client:
            return self._classify_with_llm(transaction, available_categories)

        # No classification available
        return transaction.category or "Uncategorized", 0.0

    def _apply_rules(self, transaction: Transaction) -> Optional[str]:
        """
        Apply rule-based classification.

        Args:
            transaction: Transaction to classify

        Returns:
            Category if a rule matches, None otherwise
        """
        # TODO: Implement rule-based patterns
        # Examples:
        # - Payee contains "SAFEWAY" -> "Groceries"
        # - Payee contains "SHELL" -> "Auto:Fuel"
        # - Amount patterns (e.g., recurring $X.XX -> specific category)
        return None

    def _classify_with_ml(
        self, transaction: Transaction, available_categories: list[str]
    ) -> tuple[str, float]:
        """
        Classify using trained ML model.

        Args:
            transaction: Transaction to classify
            available_categories: Valid categories

        Returns:
            Tuple of (category, confidence)
        """
        # TODO: Implement ML classification
        # - Feature engineering: payee, amount, date patterns, etc.
        # - Use trained model (Random Forest, Gradient Boosting, etc.)
        return "Uncategorized", 0.0

    def _classify_with_llm(
        self, transaction: Transaction, available_categories: list[str]
    ) -> tuple[str, float]:
        """
        Classify using Claude LLM.

        Args:
            transaction: Transaction to classify
            available_categories: Valid categories

        Returns:
            Tuple of (category, confidence)
        """
        if not self.client:
            return "Uncategorized", 0.0

        try:
            # Format categories for better readability
            categories_formatted = "\n".join([f"  - {cat}" for cat in available_categories])

            # Get day of week for additional context
            day_of_week = transaction.date.strftime("%A")

            # Build rich context
            context_parts = [
                f"Date: {transaction.date} ({day_of_week})",
                f"Payee: {transaction.payee}",
                f"Amount: ${transaction.amount:.2f}",
            ]

            # Add account information
            if transaction.account_name:
                account_desc = transaction.account_name
                if transaction.account_type:
                    # Make account type more readable
                    readable_type = transaction.account_type.replace('CREDITCARD', 'Credit Card').replace('CHECKING', 'Checking')
                    account_desc = f"{account_desc} ({readable_type})"
                context_parts.append(f"Account: {account_desc}")

            # Add FI note (card last 4 digits)
            if transaction.fi_note:
                context_parts.append(f"Card/Account: {transaction.fi_note}")

            # Add memo if available
            if transaction.memo:
                context_parts.append(f"Memo: {transaction.memo}")

            # Add reference if available
            if transaction.reference:
                context_parts.append(f"Reference: {transaction.reference}")

            # Add check number if available
            if transaction.check_number:
                context_parts.append(f"Check #: {transaction.check_number}")

            transaction_details = "\n- ".join(context_parts)

            # Build prompt
            prompt = f"""You are a financial transaction categorization expert. Analyze this transaction and suggest the most appropriate category.

Transaction Details:
- {transaction_details}

Available Categories:
{categories_formatted}

Instructions:
1. Choose the single most appropriate category from the list above
2. Provide a confidence score between 0.0 and 1.0
3. Consider ALL transaction details including payee, account type, day of week, amount, and any memo/reference
4. The payee field may contain location info, card digits, or other metadata - use it all
5. Respond ONLY with the category name and confidence, nothing else

Format your response exactly as: CATEGORY_NAME|CONFIDENCE

Example: Groceries|0.95"""

            # Call Claude API (using latest Haiku 4.5 model)
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = response.content[0].text.strip()
            parts = response_text.split("|")

            if len(parts) == 2:
                category = parts[0].strip()
                confidence = float(parts[1].strip())

                # Validate category exists in available categories
                if category in available_categories:
                    return category, confidence
                else:
                    # Try case-insensitive match
                    for cat in available_categories:
                        if cat.lower() == category.lower():
                            return cat, confidence

                    # Category not found
                    return "Uncategorized", 0.0
            else:
                # Invalid format
                return "Uncategorized", 0.0

        except Exception as e:
            # Log error and return uncategorized
            print(f"Error classifying transaction {transaction.id}: {e}")
            return "Uncategorized", 0.0
