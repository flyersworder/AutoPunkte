# flake8: noqa: E501
#!/usr/bin/env python3
"""
Notifier - Utility for sending notifications about Payback coupon activation results.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger("PaybackNotifier")


class Notifier:
    """Class to handle notifications for activation results."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Notifier.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path) if config_path else {}
        self.options = self.config.get("options", {})

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Dictionary containing configuration
        """
        try:
            with open(config_path, "r") as file:
                config = yaml.safe_load(file)
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {"options": {}}

    def notify(self, results: Dict[str, Any]) -> bool:
        """
        Send notification with activation results.

        Args:
            results: Dictionary with activation results

        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Skip notification if disabled in config
        if not self._should_notify(results):
            logger.info("Notification skipped based on configuration")
            return False

        # Create notification message
        message = self._create_message(results)

        # Log notification for CI/CD
        self._log_notification(message)

        # Save results to file
        self._save_results(results)

        return True

    def _should_notify(self, results: Dict[str, Any]) -> bool:
        """
        Determine if notification should be sent based on results and configuration.

        Args:
            results: Dictionary with activation results

        Returns:
            True if notification should be sent, False otherwise
        """
        has_successful = len(results.get("successful", [])) > 0
        has_failed = len(results.get("failed", [])) > 0

        notify_on_success = self.options.get("notify_on_success", True)
        notify_on_failure = self.options.get("notify_on_failure", True)

        return (has_successful and notify_on_success) or (
            has_failed and notify_on_failure
        )

    def _create_message(self, results: Dict[str, Any]) -> str:
        """
        Create notification message from results.

        Args:
            results: Dictionary with activation results

        Returns:
            Formatted message string
        """
        timestamp = results.get("timestamp", datetime.now().isoformat())
        successful = results.get("successful", [])
        failed = results.get("failed", [])

        message = f"📊 Payback Coupon Activation Report ({timestamp})\n\n"

        # Add successful activations
        message += f"✅ Successfully activated coupons: {len(successful)}\n"
        for item in successful:
            merchant = item.get("partner_name", item.get("merchant", "Unknown"))
            coupons_activated = item.get("activated", item.get("coupons_activated", 0))
            message += f"  • {merchant}: {coupons_activated} coupons\n"

        message += "\n"

        # Add failed activations
        message += f"❌ Failed activations: {len(failed)}\n"
        for item in failed:
            merchant = item.get("partner_name", item.get("merchant", "Unknown"))
            reason = item.get("error", item.get("reason", "Unknown error"))
            message += f"  • {merchant}: {reason}\n"

        return message

    def _log_notification(self, message: str):
        """
        Log notification message.

        Args:
            message: Notification message
        """
        logger.info(f"Notification message:\n{message}")

        # Print to stdout for CI/CD logs
        print("\n" + "=" * 50)
        print("PAYBACK ACTIVATION NOTIFICATION")
        print("=" * 50)
        print(message)
        print("=" * 50 + "\n")

    def _save_results(self, results: Dict[str, Any]):
        """
        Save results to a JSON file.

        Args:
            results: Dictionary with activation results
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"activation_results_{timestamp}.json"

            with open(filename, "w") as file:
                json.dump(results, file, indent=2)

            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
