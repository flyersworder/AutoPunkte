# flake8: noqa: E501
#!/usr/bin/env python3
"""
PaybackActivator - Automatically activates Payback coupons for specified merchants.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

import yaml

# Import pydoll for web interaction without webdrivers
try:
    from pydoll.browser.chrome import Chrome
    from pydoll.browser.options import Options
    from pydoll.constants import By
except ImportError:
    print(
        "Error: pydoll library not found. Please install it with: uv add pydoll-python"
    )
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"payback_activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger("PaybackActivator")


class PaybackActivator:
    """Class to handle Payback coupon activation."""

    def __init__(self, username, password, config_path="config.yaml", headless=False):
        """Initialize the PaybackActivator with credentials and configuration."""
        self.username = username
        self.password = password
        self.config_path = config_path
        self.headless = headless
        self.config = self._load_config()
        self.logger = logging.getLogger("PaybackActivator")
        # Detect if running in GitHub Actions
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        # Enable debug mode if DEBUG environment variable is set
        self.debug_mode = os.environ.get("DEBUG") == "1"
        # Check for custom Chrome path
        self.chrome_path = os.environ.get("CHROME_PATH")

    def _load_config(self):
        """Load configuration from config.yaml file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading config file {self.config_path}: {e}")
            return {"merchants": [], "options": {"activation_timeout": 30}}

    async def activate_coupons_for_partner(self, page, partner_name, partner_id):
        """Activate all coupons for a specific partner."""
        self.logger.info(f"Activating coupons for {partner_name} (ID: {partner_id})...")

        # Navigate to the specific partner's coupons page
        await page.go_to(f"https://www.payback.de/coupons?partnerId={partner_id}")

        # Wait longer for coupons to load in GitHub Actions
        wait_time = 15 if self.is_github_actions else 5
        self.logger.info(f"Waiting {wait_time} seconds for coupons to load...")
        await asyncio.sleep(wait_time)

        # Take a screenshot before activation attempt for debugging
        if self.debug_mode or self.is_github_actions:
            debug_screenshot = f"payback_debug_{partner_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(debug_screenshot)
            self.logger.info(f"Debug screenshot saved to {debug_screenshot}")

        # Find and click all "Jetzt aktivieren" buttons
        self.logger.info("Attempting to activate all coupons...")
        await page.execute_script(
            """
            // Get the coupon center container
            var couponCenter = document.querySelector("#coupon-center");
            if (!couponCenter || !couponCenter.shadowRoot) {
                // Debug the DOM structure to help diagnose issues
                var debugInfo = {
                    hasCouponCenter: !!document.querySelector('#coupon-center'),
                    hasShadowRoot: !!(document.querySelector('#coupon-center') && document.querySelector('#coupon-center').shadowRoot),
                    bodyContent: document.body.innerHTML.substring(0, 1000), // First 1000 chars of body
                    urlPath: window.location.href,
                    title: document.title
                };

                console.log("Coupon center not found or no shadow root. Debug info:", JSON.stringify(debugInfo));
                window.activationResults = {
                    success: false,
                    error: "Coupon center not found",
                    activated: 0,
                    total: 0,
                    debugInfo: debugInfo
                };
            } else {
                // Try multiple selectors for the coupon container to be more robust
                var selectors = [
                    "div > div.coupon-center__container > div.coupon-center__published-column.column--double > div.coupon-center__container-published-coupons",
                    "div > div.coupon-center__container > div.coupon-center__published-column > div.coupon-center__container-published-coupons",
                    "div.coupon-center__container div.coupon-center__container-published-coupons",
                    "div.coupon-center__published-column div.coupon-center__container-published-coupons"
                ];

                var couponContainer = null;
                for (var i = 0; i < selectors.length && !couponContainer; i++) {
                    couponContainer = couponCenter.shadowRoot.querySelector(selectors[i]);
                    if (couponContainer) {
                        console.log("Found coupon container with selector: " + selectors[i]);
                    }
                }

                if (!couponContainer) {
                    console.log("Coupon container not found - this may mean all coupons are already activated");
                    window.activationResults = { success: true, error: "No coupons to activate", activated: 0, total: 0, alreadyActivated: true };
                } else {
                    var coupons = couponContainer.querySelectorAll("pbc-coupon");
                    console.log("Found " + coupons.length + " coupons");

                    var activatedCount = 0;

                    // Iterate through each coupon and try to activate it
                    for (var i = 0; i < coupons.length; i++) {
                        var coupon = coupons[i];
                        try {
                            if (coupon.shadowRoot) {
                                // Try multiple selectors for the call to action element
                                var callToActionSelectors = [
                                    "div > pbc-coupon-call-to-action",
                                    "pbc-coupon-call-to-action"
                                ];

                                var callToAction = null;
                                for (var j = 0; j < callToActionSelectors.length && !callToAction; j++) {
                                    callToAction = coupon.shadowRoot.querySelector(callToActionSelectors[j]);
                                }

                                if (callToAction && callToAction.shadowRoot) {
                                    // Try multiple selectors for the activation button
                                    var buttonSelectors = [
                                        "div > button.coupon-call-to-action__button.coupon__activate-button.not-activated",
                                        "button.coupon-call-to-action__button.coupon__activate-button.not-activated",
                                        "button.not-activated",
                                        "button:not(.activated)"
                                    ];

                                    var button = null;
                                    for (var j = 0; j < buttonSelectors.length && !button; j++) {
                                        button = callToAction.shadowRoot.querySelector(buttonSelectors[j]);
                                        if (button) {
                                            console.log("Found activation button with selector: " + buttonSelectors[j] + " for coupon " + (i + 1));
                                        }
                                    }

                                    // If still no button found, try to find by text content
                                    if (!button) {
                                        var allButtons = callToAction.shadowRoot.querySelectorAll("button");
                                        for (var j = 0; j < allButtons.length; j++) {
                                            if (allButtons[j].textContent.toLowerCase().includes("aktivieren")) {
                                                button = allButtons[j];
                                                console.log("Found activation button by text content for coupon " + (i + 1));
                                                break;
                                            }
                                        }
                                    }

                                    if (button) {
                                        console.log("Found activation button for coupon " + (i + 1));
                                        button.click();
                                        activatedCount++;
                                        console.log("Clicked activation button for coupon " + (i + 1));
                                    } else {
                                        // Check if the button is already activated
                                        var activatedButtonSelectors = [
                                            "div > button.coupon-call-to-action__button.coupon__activate-button.activated",
                                            "button.coupon-call-to-action__button.activated",
                                            "button.activated"
                                        ];

                                        var activatedButton = null;
                                        for (var j = 0; j < activatedButtonSelectors.length && !activatedButton; j++) {
                                            activatedButton = callToAction.shadowRoot.querySelector(activatedButtonSelectors[j]);
                                        }

                                        if (activatedButton) {
                                            console.log("Coupon " + (i + 1) + " is already activated");
                                        } else {
                                            console.log("Activation button not found for coupon " + (i + 1));
                                        }
                                    }
                                } else {
                                    console.log("Call to action element or shadow root not found for coupon " + (i + 1));
                                }
                            } else {
                                console.log("No shadow root for coupon " + (i + 1));
                            }
                        } catch (e) {
                            console.log("Error processing coupon " + (i + 1) + ": " + e.message);
                        }
                    }

                    // Store results in a global variable instead of returning
                    window.activationResults = {
                        success: true,
                        activated: activatedCount,
                        total: coupons.length
                    };
                    console.log("Activation complete. Activated " + activatedCount + " out of " + coupons.length + " coupons");
                }
            }
            """
        )

        # Wait a moment for the activations to complete
        await asyncio.sleep(2)

        # Get the activation results from the global variable
        await page.execute_script(
            """
            if (window.activationResults) {
                console.log("Activation results:", window.activationResults);
                window.activationResultsJSON = JSON.stringify(window.activationResults);
            } else {
                console.log("No activation results found");
                window.activationResultsJSON = JSON.stringify({success: false, error: "No results found"});
            }
            """
        )

        # Get the results as a JSON string
        results_json = await page.execute_script("window.activationResultsJSON")

        # Process the activation results
        if results_json:
            try:
                # Check if results_json is already a dict with 'result' key (pydoll specific format)
                if isinstance(results_json, dict) and "result" in results_json:
                    # Extract the actual JSON string from the pydoll result structure
                    json_str = (
                        results_json.get("result", {})
                        .get("result", {})
                        .get("value", "{}")
                    )
                    results = json.loads(json_str)
                else:
                    # Try to parse it directly
                    results = json.loads(results_json)

                if results.get("success"):
                    # Check if this is the "already activated" case
                    if results.get("alreadyActivated"):
                        self.logger.info(
                            f"No new coupons to activate for {partner_name} - they may already be activated"
                        )
                    else:
                        self.logger.info(
                            f"Successfully activated {results.get('activated')} out of {results.get('total')} coupons for {partner_name}"
                        )
                    return {
                        "partner_name": partner_name,
                        "partner_id": partner_id,
                        "activated": results.get("activated", 0),
                        "total": results.get("total", 0),
                        "success": True,
                        "alreadyActivated": results.get("alreadyActivated", False),
                    }
                else:
                    self.logger.error(
                        f"Activation failed for {partner_name}: {results.get('error', 'Unknown error')}"
                    )
                    return {
                        "partner_name": partner_name,
                        "partner_id": partner_id,
                        "error": results.get("error", "Unknown error"),
                        "success": False,
                    }
            except Exception as e:
                self.logger.error(
                    f"Error processing activation results for {partner_name}: {e}"
                )
                return {
                    "partner_name": partner_name,
                    "partner_id": partner_id,
                    "error": str(e),
                    "success": False,
                }
        else:
            self.logger.error(f"Failed to get activation results for {partner_name}")
            return {
                "partner_name": partner_name,
                "partner_id": partner_id,
                "error": "Failed to get activation results",
                "success": False,
            }

    async def run(self):
        """Run the Payback coupon activation process."""
        merchants = self.config.get("merchants", [])

        if not merchants:
            self.logger.warning(
                "No merchants found in config. Please add at least one merchant."
            )
            return {"successful": [], "failed": [], "error": "No merchants configured"}

        self.logger.info(f"Found {len(merchants)} merchants in configuration")

        # Create browser options
        browser_options = Options()

        # Set headless mode if requested
        if self.headless and not self.is_github_actions:
            browser_options.add_argument("--headless=new")

        # Add additional options for stability
        browser_options.add_argument("--no-sandbox")
        browser_options.add_argument("--disable-dev-shm-usage")
        browser_options.add_argument("--disable-gpu")
        browser_options.add_argument("--disable-extensions")
        browser_options.add_argument("--disable-popup-blocking")
        browser_options.add_argument("--disable-notifications")
        browser_options.add_argument("--disable-infobars")
        browser_options.add_argument("--window-size=1920,1080")
        browser_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )

        # Use pre-installed Chrome in GitHub Actions if available
        if self.is_github_actions and self.chrome_path:
            self.logger.info(f"Using pre-installed Chrome at: {self.chrome_path}")
            # pydoll doesn't have set_binary method, use binary_location if it exists
            # or add as an argument if not
            try:
                browser_options.binary_location = self.chrome_path
            except AttributeError:
                # If binary_location doesn't exist, use chrome path as an argument
                browser_options.add_argument(f"--binary={self.chrome_path}")

        if self.headless:
            browser_options.add_argument("--headless")
            # Add additional headless-specific options for GitHub Actions
            if self.is_github_actions:
                browser_options.add_argument("--disable-web-security")

        async with Chrome(options=browser_options) as browser:
            await browser.start()
            page = await browser.get_page()

            # Set a more realistic user agent
            await page.execute_script(
                """
                Object.defineProperty(navigator, 'userAgent', {
                    get: function () { return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'; }
                });

                // Override properties that automation detection might check
                Object.defineProperty(navigator, 'webdriver', {
                    get: function () { return false; }
                });
                """
            )

            # Navigate to the login page
            self.logger.info("Navigating to Payback login page...")
            await page.go_to("https://www.payback.de/login")

            # Wait for page to load
            await asyncio.sleep(5)
            self.logger.info("Page loaded, looking for cookie consent...")

            # Handle cookie consent button
            try:
                cookie_selector = '//*[@id="onetrust-reject-all-handler"]'
                button = await page.find_element(By.XPATH, cookie_selector)
                await button.click()
                self.logger.info("Clicked cookie consent button")
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not find or click cookie button: {e}")

            # Wait for page to fully load after cookie handling
            await asyncio.sleep(3)
            self.logger.info("Attempting to interact with login form...")

            # Access the input element through the nested shadow DOM structure
            self.logger.info("Accessing username input through nested shadow DOM...")

            # Create a JavaScript string with the username value properly escaped
            username_script = (
                """
                // Step 1: Get the first shadow host
                var loginElement = document.querySelector("#cid-29334 > div > div > div > div > pbc-login");

                // Step 2: Access its shadow root
                var loginShadow = loginElement.shadowRoot;

                // Step 3: Find the second shadow host
                var loginIdentification = loginShadow.querySelector("pbc-double-image-background > div > pbc-login-identification");

                // Step 4: Access its shadow root
                var identificationShadow = loginIdentification.shadowRoot;

                // Step 5: Find the input container
                var inputContainer = identificationShadow.querySelector("#identificationInput__slotted");

                // Step 6: Find the actual input element
                // The input might be directly inside the container or it might be inside another element
                var inputElement = inputContainer.querySelector("input");
                if (!inputElement) {
                    inputElement = inputContainer;
                }

                // Step 7: Interact with the input
                inputElement.focus();
                inputElement.click();

                // Set the value and dispatch events
                inputElement.value = '"""
                + self.username
                + """';

                // Dispatch input event
                var inputEvent = new Event('input', { bubbles: true });
                inputElement.dispatchEvent(inputEvent);

                // Dispatch change event
                var changeEvent = new Event('change', { bubbles: true });
                inputElement.dispatchEvent(changeEvent);

                console.log("Successfully interacted with username input in shadow DOM");
                """
            )

            await page.execute_script(username_script)

            self.logger.info("Successfully entered username")

            # Wait a moment before trying to find and click the continue button
            await asyncio.sleep(2)

            # Try to find and click the continue button in the shadow DOM
            self.logger.info("Clicking continue button...")
            await page.execute_script(
                """
                // Step 1: Get the first shadow host
                var loginElement = document.querySelector("#cid-29334 > div > div > div > div > pbc-login");

                // Step 2: Access its shadow root
                var loginShadow = loginElement.shadowRoot;

                // Step 3: Find the second shadow host
                var loginIdentification = loginShadow.querySelector("pbc-double-image-background > div > pbc-login-identification");

                // Step 4: Access its shadow root
                var identificationShadow = loginIdentification.shadowRoot;

                // Step 5: Find the button container element
                var buttonElement = identificationShadow.querySelector("#buttonElement");
                console.log("Button container found: " + (buttonElement ? "yes" : "no"));

                if (buttonElement && buttonElement.shadowRoot) {
                    // Step 6: Access the button container's shadow root
                    var buttonShadow = buttonElement.shadowRoot;

                    // Step 7: Find the actual button
                    var button = buttonShadow.querySelector("button");
                    console.log("Button found: " + (button ? "yes" : "no"));

                    if (button) {
                        // Click the button
                        button.click();
                        console.log("Clicked button: " + button.textContent.trim());
                    }
                } else {
                    console.log("Button container or its shadow root not found");

                    // Fallback: try to find any button in the identification shadow
                    var buttons = identificationShadow.querySelectorAll("button");
                    console.log("Found " + buttons.length + " buttons in identification shadow");

                    if (buttons.length > 0) {
                        buttons[0].click();
                        console.log("Clicked first button as fallback");
                    }
                }
                """
            )

            self.logger.info("Clicked continue button")

            # Wait for the password page to load
            self.logger.info("Waiting for password page to load...")
            await asyncio.sleep(5)

            # Now enter the password using the provided shadow DOM path
            self.logger.info("Accessing password input through nested shadow DOM...")

            # Create a JavaScript string with the password value properly escaped
            password_script = (
                """
                // Step 1: Get the first shadow host
                var loginElement = document.querySelector("#cid-29334 > div > div > div > div > pbc-login");

                // Step 2: Access its shadow root
                var loginShadow = loginElement.shadowRoot;

                // Step 3: Find the password component
                var passwordComponent = loginShadow.querySelector("pbc-double-image-background > div > pbc-login-password");
                console.log("Password component found: " + (passwordComponent ? "yes" : "no"));

                if (passwordComponent && passwordComponent.shadowRoot) {
                    // Step 4: Access the password component's shadow root
                    var passwordShadow = passwordComponent.shadowRoot;

                    // Step 5: Find the password input container
                    var passwordContainer = passwordShadow.querySelector("#passwordInput__slotted");
                    console.log("Password container found: " + (passwordContainer ? "yes" : "no"));

                    if (passwordContainer) {
                        // Step 6: Find the actual input element
                        var passwordInput = passwordContainer.querySelector("input");
                        if (!passwordInput) {
                            passwordInput = passwordContainer;
                        }

                        console.log("Password input found: " + (passwordInput ? "yes" : "no"));

                        if (passwordInput) {
                            // Step 7: Interact with the password input
                            passwordInput.focus();
                            passwordInput.click();

                            // Set the value and dispatch events
                            passwordInput.value = '"""
                + self.password
                + """';

                            // Dispatch input event
                            var inputEvent = new Event('input', { bubbles: true });
                            passwordInput.dispatchEvent(inputEvent);

                            // Dispatch change event
                            var changeEvent = new Event('change', { bubbles: true });
                            passwordInput.dispatchEvent(changeEvent);

                            console.log("Successfully entered password");
                        }
                    }
                }
                """
            )

            await page.execute_script(password_script)

            self.logger.info("Successfully entered password")

            # Wait a moment before clicking the login button
            await asyncio.sleep(2)

            # Click the login button
            self.logger.info("Clicking login button...")
            await page.execute_script(
                """
                // Step 1: Get the first shadow host
                var loginElement = document.querySelector("#cid-29334 > div > div > div > div > pbc-login");

                // Step 2: Access its shadow root
                var loginShadow = loginElement.shadowRoot;

                // Step 3: Find the password component
                var passwordComponent = loginShadow.querySelector("pbc-double-image-background > div > pbc-login-password");

                if (passwordComponent && passwordComponent.shadowRoot) {
                    // Step 4: Access the password component's shadow root
                    var passwordShadow = passwordComponent.shadowRoot;

                    // Step 5: Find the button container
                    var buttonElement = passwordShadow.querySelector("#buttonElement");
                    console.log("Login button container found: " + (buttonElement ? "yes" : "no"));

                    if (buttonElement && buttonElement.shadowRoot) {
                        // Step 6: Access the button container's shadow root
                        var buttonShadow = buttonElement.shadowRoot;

                        // Step 7: Find the actual button
                        var button = buttonShadow.querySelector("button");
                        console.log("Login button found: " + (button ? "yes" : "no"));

                        if (button) {
                            // Click the button
                            button.click();
                            console.log("Clicked login button: " + button.textContent.trim());
                        }
                    } else {
                        // Fallback: try to find any button in the password shadow
                        var buttons = passwordShadow.querySelectorAll("button");
                        console.log("Found " + buttons.length + " buttons in password shadow");

                        if (buttons.length > 0) {
                            buttons[0].click();
                            console.log("Clicked first button as fallback");
                        }
                    }
                }
                """
            )

            self.logger.info("Clicked login button")

            # Wait to see the result
            self.logger.info("Waiting for login to complete...")
            await asyncio.sleep(5)

            # Check if login was successful by looking for elements on the page
            self.logger.info("Checking login status...")
            try:
                # Try to find an element that would only be present after successful login
                await page.execute_script(
                    """
                    // Look for elements that would indicate successful login
                    var userMenuElement = document.querySelector('pbc-user-menu');
                    var couponElements = document.querySelectorAll('pbc-coupon-card');

                    // Log what we found for debugging
                    console.log('User menu found: ' + (userMenuElement ? 'yes' : 'no'));
                    console.log('Coupon elements found: ' + couponElements.length);

                    // Store results in window for access
                    window.loginSuccessIndicators = {
                        userMenuFound: !!userMenuElement,
                        couponCount: couponElements.length
                    };
                    """
                )

                self.logger.info("Login completed.")
                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"Error checking login status: {e}")
                return {
                    "successful": [],
                    "failed": [],
                    "error": f"Login failed: {str(e)}",
                }

            # Process each merchant from the config
            activation_results = []
            successful = []
            failed = []

            for merchant in merchants:
                merchant_name = merchant.get("name", "Unknown")
                partner_id = merchant.get("partner_id", "")

                if not partner_id:
                    self.logger.warning(
                        f"Skipping {merchant_name}: No partner_id specified"
                    )
                    failed.append(
                        {
                            "partner_name": merchant_name,
                            "error": "No partner_id specified",
                            "success": False,
                        }
                    )
                    continue

                # Activate coupons for this merchant
                result = await self.activate_coupons_for_partner(
                    page, merchant_name, partner_id
                )
                activation_results.append(result)

                if result.get("success", False):
                    successful.append(result)
                else:
                    failed.append(result)

                # Wait a moment before processing the next merchant
                await asyncio.sleep(2)

            # Print summary of all activations
            self.logger.info("\n===== ACTIVATION SUMMARY =====")
            total_activated = 0
            total_available = 0

            for result in activation_results:
                partner_name = result.get("partner_name", "Unknown")
                if result.get("success", False):
                    activated = result.get("activated", 0)
                    total = result.get("total", 0)
                    total_activated += activated
                    total_available += total
                    if result.get("alreadyActivated", False):
                        self.logger.info(
                            f"✅ {partner_name}: No new coupons to activate (may already be activated)"
                        )
                    else:
                        self.logger.info(
                            f"✅ {partner_name}: Activated {activated} out of {total} coupons"
                        )
                else:
                    error = result.get("error", "Unknown error")
                    self.logger.error(f"❌ {partner_name}: Failed - {error}")

            self.logger.info(
                f"\nTotal: Activated {total_activated} out of {total_available} coupons across {len(merchants)} merchants"
            )
            self.logger.info("===== END OF SUMMARY =====")

            # Capture screenshot of activated coupons
            self.logger.info("\n===== ACTIVATED COUPONS OVERVIEW =====")
            await page.go_to("https://www.payback.de/coupons?partnerId=")
            await asyncio.sleep(5)

            # Take a screenshot instead of PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"payback_coupons_{timestamp}.png"
            await page.get_screenshot(screenshot_path)
            self.logger.info(f"Screenshot saved to {screenshot_path}")

            # Extract activated coupons HTML
            html_path = f"payback_coupons_{timestamp}.html"
            html_content = await page.page_source

            # Save HTML content
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                self.logger.info(f"HTML content saved to {html_path}")
            except Exception as e:
                self.logger.error(f"Error saving HTML content: {e}")

            self.logger.info("===== END OF ACTIVATED COUPONS OVERVIEW =====")

            # Return results in the format expected by activate.py
            return {
                "successful": successful,
                "failed": failed,
                "total_activated": total_activated,
                "total_available": total_available,
                "screenshot_path": screenshot_path,
                "html_path": html_path,
            }


async def main_async(username, password, config_path="config.yaml", headless=False):
    """Main async function to run the Payback coupon activator."""
    activator = PaybackActivator(username, password, config_path, headless)
    return await activator.run()


if __name__ == "__main__":
    import argparse

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
        "--headless", action="store_true", help="Run in headless mode (no browser UI)"
    )

    args = parser.parse_args()

    # Get credentials from arguments or environment variables
    username = args.username or os.environ.get("PAYBACK_USERNAME")
    password = args.password or os.environ.get("PAYBACK_PASSWORD")

    if not username or not password:
        print(
            "Error: Payback credentials not provided. Use --username/--password arguments or PAYBACK_USERNAME/PAYBACK_PASSWORD environment variables"
        )
        sys.exit(1)

    # Run the async main function
    results = asyncio.run(main_async(username, password, args.config, args.headless))

    # Return exit code based on results
    if len(results["failed"]) > 0 and len(results["successful"]) == 0:
        print("All coupon activations failed")
        sys.exit(1)
    elif len(results["failed"]) > 0:
        print("Some coupon activations failed")
        sys.exit(0)
    else:
        print("All coupon activations successful")
        sys.exit(0)
