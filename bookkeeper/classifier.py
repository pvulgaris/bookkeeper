"""Transaction classification using ML and LLM."""

import json
import time
from typing import Optional

import requests
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

        # Rule-based patterns: payee substring -> category
        # Case-insensitive matching
        self.rules = self._load_default_rules()

    def _load_default_rules(self) -> dict[str, str]:
        """
        Load default rule-based categorization patterns.

        Returns:
            Dictionary mapping payee patterns to categories
        """
        return {
            # Groceries
            "whole foods": "Groceries",
            "trader joe": "Groceries",
            "safeway": "Groceries",
            "stop & shop": "Groceries",
            "costco": "Groceries",
            "target": "Groceries",
            "walmart": "Groceries",
            "wegmans": "Groceries",
            "kroger": "Groceries",
            "publix": "Groceries",

            # Gas & Auto
            "shell": "Gas & Fuel",
            "chevron": "Gas & Fuel",
            "exxon": "Gas & Fuel",
            "mobil": "Gas & Fuel",
            "bp ": "Gas & Fuel",
            "texaco": "Gas & Fuel",
            "arco": "Gas & Fuel",

            # Coffee & Fast Food
            "starbucks": "Coffee Shops",
            "dunkin": "Coffee Shops",
            "mcdonald": "Fast Food",
            "burger king": "Fast Food",
            "wendy": "Fast Food",
            "taco bell": "Fast Food",
            "kfc": "Fast Food",
            "chick-fil-a": "Fast Food",
            "five guys": "Fast Food",
            "shake shack": "Fast Food",

            # Restaurants
            "chipotle": "Restaurants",
            "panera": "Restaurants",
            "subway": "Fast Food",

            # Transportation
            "uber": "Auto & Transport",
            "lyft": "Auto & Transport",
            "mta": "Public Transportation",

            # Entertainment & Subscriptions
            "netflix": "Entertainment",
            "hulu": "Entertainment",
            "spotify": "Entertainment",
            "patreon": "Entertainment",
            "substack": "Books",
            "parentdata": "Books",

            # Shopping & Services
            "amazon": "Shopping",
            "apple.com": "Electronics & Software",
            "peloton": "Gym",
            "ups": "Shopping",
            "usps": "Shopping",
            "federal express": "Shopping",
            "fedex": "Shopping",

            # Travel
            "united airlines": "Air Travel",
            "jetblue": "Air Travel",
            "alaska air": "Air Travel",
            "southwest": "Air Travel",
            "delta": "Air Travel",
            "american airlines": "Air Travel",

            # Local merchants (Berkeley/Oakland area)
            "souvenir": "Coffee Shops",
            "barneys gourmet": "Restaurants",
            "rick and ann": "Restaurants",
            "timeless coff": "Coffee Shops",
            "la farine": "Restaurants",

            # Car rental & sharing
            "zipcar": "Auto & Transport",
        }

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
        # Case-insensitive payee matching
        payee_lower = transaction.payee.lower()

        # Check each rule pattern
        for pattern, category in self.rules.items():
            if pattern in payee_lower:
                return category

        return None

    def _web_search(self, query: str, max_retries: int = 3) -> str:
        """
        Perform a web search using DuckDuckGo's instant answer API with retry logic.

        Args:
            query: Search query
            max_retries: Maximum number of retry attempts

        Returns:
            Search results as formatted string, or error message if all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Use DuckDuckGo instant answer API (free, no key needed)
                url = "https://api.duckduckgo.com/"
                params = {
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                }

                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()  # Raise exception for bad status codes
                data = response.json()

                results = []

                # Add abstract if available
                if data.get("Abstract"):
                    results.append(f"Summary: {data['Abstract']}")

                # Add related topics
                if data.get("RelatedTopics"):
                    for i, topic in enumerate(data["RelatedTopics"][:3]):
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append(f"{i+1}. {topic['Text']}")

                if results:
                    return "\n".join(results)
                else:
                    return f"No specific results found for '{query}'"

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    time.sleep(0.5 * (2 ** attempt))
                    continue

        # All retries failed - return error message instead of raising exception
        return f"Web search failed after {max_retries} attempts: {str(last_error)}"

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
        Classify using Claude LLM with web search tool.

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
            prompt = f"""You are a financial transaction categorization expert with access to web search. Analyze this transaction and suggest the most appropriate category.

Transaction Details:
- {transaction_details}

Available Categories:
{categories_formatted}

Instructions:
1. If the payee name is unclear or contains merchant codes, use the web_search tool to identify the actual merchant
2. Choose the single most appropriate category from the list above
3. Provide a confidence score between 0.0 and 1.0
4. Consider ALL transaction details including payee, account type, day of week, amount, and any memo/reference

Respond with valid JSON only, in this exact format:
{{
  "category": "CATEGORY_NAME",
  "confidence": 0.95
}}

Example responses:
{{"category": "Groceries", "confidence": 0.95}}
{{"category": "Electronics & Software", "confidence": 0.88}}
{{"category": "Gas & Fuel", "confidence": 0.92}}"""

            # Define web search tool
            tools = [{
                "name": "web_search",
                "description": "Search the web to identify merchants or get information about businesses. Use this when the payee name is unclear or contains merchant codes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to identify the merchant or business"
                        }
                    },
                    "required": ["query"]
                }
            }]

            # Initial API call with tool support and JSON prefill
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"}  # Prefill to force JSON output
            ]
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                tools=tools,
                messages=messages
            )

            # Tool use loop - always send tool_result even if search fails
            while response.stop_reason == "tool_use":
                # Find ALL tool use blocks in response
                tool_use_blocks = [
                    block for block in response.content
                    if block.type == "tool_use"
                ]

                if not tool_use_blocks:
                    break

                # Add assistant message with all tool uses
                messages.append({"role": "assistant", "content": response.content})

                # Execute web search for each tool use and collect results
                tool_results = []
                for tool_use_block in tool_use_blocks:
                    search_query = tool_use_block.input["query"]
                    search_results = self._web_search(search_query)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": search_results
                    })

                # Add all tool results in a single user message
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue conversation with JSON prefill
                messages.append({"role": "assistant", "content": "{"})
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1000,
                    tools=tools,
                    messages=messages
                )

            # Parse final response as JSON
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text = block.text.strip()
                    break

            # Add opening brace from prefill and parse JSON
            try:
                json_str = "{" + response_text
                data = json.loads(json_str)

                category = data.get("category", "").strip()
                confidence = float(data.get("confidence", 0.0))

                # Validate category exists in available categories
                if category in available_categories:
                    return category, confidence
                else:
                    # Try case-insensitive match
                    for cat in available_categories:
                        if cat.lower() == category.lower():
                            return cat, confidence

                    # Category not found in available categories
                    return "Uncategorized", 0.0

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # JSON parsing failed
                return "Uncategorized", 0.0

        except Exception as e:
            # Log error and return uncategorized
            print(f"Error classifying transaction {transaction.id}: {e}")
            return "Uncategorized", 0.0
