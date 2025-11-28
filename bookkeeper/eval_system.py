"""Evaluation system for tracking classification accuracy and learning from corrections."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ClassificationResult:
    """Record of a classification decision."""

    transaction_id: int
    original_category: Optional[str]
    suggested_category: str
    confidence: float
    actual_category: Optional[str]  # Set after user correction
    timestamp: str
    transaction_data: dict


class EvalSystem:
    """Tracks classification performance and learns from corrections."""

    def __init__(self, eval_dir: Path = Path("eval_data")):
        """
        Initialize eval system.

        Args:
            eval_dir: Directory to store eval data
        """
        self.eval_dir = eval_dir
        self.eval_dir.mkdir(exist_ok=True)
        self.results_file = eval_dir / "classification_results.jsonl"

    def record_classification(
        self,
        transaction_id: int,
        original_category: Optional[str],
        suggested_category: str,
        confidence: float,
        transaction_data: dict,
    ) -> None:
        """
        Record a classification suggestion.

        Args:
            transaction_id: ID of transaction
            original_category: Original category (if any)
            suggested_category: Suggested new category
            confidence: Confidence score (0-1)
            transaction_data: Full transaction data for future training
        """
        result = ClassificationResult(
            transaction_id=transaction_id,
            original_category=original_category,
            suggested_category=suggested_category,
            confidence=confidence,
            actual_category=None,
            timestamp=datetime.now().isoformat(),
            transaction_data=transaction_data,
        )

        # Append to JSONL file
        with open(self.results_file, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")

    def record_correction(self, transaction_id: int, actual_category: str) -> None:
        """
        Record a user correction to update the eval dataset.

        Args:
            transaction_id: ID of transaction that was corrected
            actual_category: The category the user chose
        """
        # TODO: Implement updating the record with actual category
        # This will be used to build training data for ML model
        pass

    def get_accuracy_stats(self) -> dict:
        """
        Calculate accuracy statistics from recorded results.

        Returns:
            Dictionary with accuracy metrics
        """
        if not self.results_file.exists():
            return {"total": 0, "correct": 0, "accuracy": 0.0}

        total = 0
        correct = 0

        with open(self.results_file) as f:
            for line in f:
                result = json.loads(line)
                if result["actual_category"] is not None:
                    total += 1
                    if result["suggested_category"] == result["actual_category"]:
                        correct += 1

        accuracy = correct / total if total > 0 else 0.0

        return {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
        }

    def export_training_data(self) -> Path:
        """
        Export corrected classifications as training data for ML model.

        Returns:
            Path to exported training data CSV
        """
        # TODO: Implement export to pandas DataFrame -> CSV
        # Filter for records where actual_category is set
        # Use transaction_data features + actual_category as labels
        pass
