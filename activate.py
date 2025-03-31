# flake8: noqa: E501
#!/usr/bin/env python3
"""
Main entry point for AutoPunkte - Payback coupon activator.
"""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from src.notifier import Notifier
from src.payback_activator import main_async

# Load environment variables from .env file if present
load_dotenv()


def main():
    """Main function to run the Payback coupon activator."""
    # Configure argument parser
    parser = argparse.ArgumentParser(
        description="Activate Payback coupons automatically"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to configuration file"
    )
    parser.add_argument("--username", help="Payback username/email")
    parser.add_argument("--password", help="Payback password")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--no-notify", action="store_true", help="Disable notifications"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode (no browser UI)"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("autopunkte.log")],
    )
    logger = logging.getLogger("AutoPunkte")

    # Get credentials from arguments, environment variables
    username = args.username or os.environ.get("PAYBACK_USERNAME")
    password = args.password or os.environ.get("PAYBACK_PASSWORD")

    if not username or not password:
        logger.error(
            "Payback credentials not provided. Use --username/--password arguments or "
            "PAYBACK_USERNAME/PAYBACK_PASSWORD environment variables"
        )
        sys.exit(1)

    logger.info("Starting AutoPunkte - Payback coupon activator")

    # Run the async main function
    try:
        results = asyncio.run(
            main_async(username, password, args.config, args.headless)
        )

        # Send notification if not disabled
        if not args.no_notify:
            notifier = Notifier(args.config)
            notifier.notify(results)

        # Return exit code based on results
        if len(results["failed"]) > 0 and len(results["successful"]) == 0:
            logger.error("All coupon activations failed")
            return 1
        elif len(results["failed"]) > 0:
            logger.warning("Some coupon activations failed")
            return 0
        else:
            logger.info("All coupon activations successful")
            return 0

    except Exception as e:
        logger.error(f"Error during coupon activation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
