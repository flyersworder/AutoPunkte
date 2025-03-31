# flake8: noqa: E501
import asyncio
import json
import os

import yaml
from dotenv import load_dotenv
from pydoll.browser.chrome import Chrome
from pydoll.browser.options import Options
from pydoll.constants import By

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
PAYBACK_USERNAME = os.getenv("PAYBACK_USERNAME", "test@example.com")
PAYBACK_PASSWORD = os.getenv("PAYBACK_PASSWORD", "test_password")

# Validate credentials
if not PAYBACK_USERNAME or not PAYBACK_PASSWORD:
    print(
        "Warning: PAYBACK_USERNAME and/or PAYBACK_PASSWORD not set in .env file. Using default test values."
    )


# Load configuration from config.yaml
def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        return {"merchants": [], "options": {"activation_timeout": 30}}


async def activate_coupons_for_partner(page, partner_name, partner_id):
    """Activate all coupons for a specific partner"""
    print(f"\nActivating coupons for {partner_name} (ID: {partner_id})...")

    # Navigate to the specific partner's coupons page
    await page.go_to(f"https://www.payback.de/coupons?partnerId={partner_id}")

    # Wait for the coupons to load
    print("Waiting for coupons to load...")
    await asyncio.sleep(5)

    # Find and click all "Jetzt aktivieren" buttons
    print("Attempting to activate all coupons...")
    await page.execute_script(
        """
        // Get the coupon center container
        var couponCenter = document.querySelector("#coupon-center");
        if (!couponCenter || !couponCenter.shadowRoot) {
            console.log("Coupon center not found or no shadow root");
            window.activationResults = { success: false, error: "Coupon center not found", activated: 0, total: 0 };
        } else {
            // Find all coupon elements within the container
            var couponContainer = couponCenter.shadowRoot.querySelector("div > div.coupon-center__container > div.coupon-center__published-column.column--double > div.coupon-center__container-published-coupons");
            if (!couponContainer) {
                console.log("Coupon container not found");
                window.activationResults = { success: false, error: "Coupon container not found", activated: 0, total: 0 };
            } else {
                var coupons = couponContainer.querySelectorAll("pbc-coupon");
                console.log("Found " + coupons.length + " coupons");

                var activatedCount = 0;

                // Iterate through each coupon and try to activate it
                for (var i = 0; i < coupons.length; i++) {
                    var coupon = coupons[i];
                    try {
                        if (coupon.shadowRoot) {
                            var callToAction = coupon.shadowRoot.querySelector("div > pbc-coupon-call-to-action");

                            if (callToAction && callToAction.shadowRoot) {
                                var button = callToAction.shadowRoot.querySelector("div > button.coupon-call-to-action__button.coupon__activate-button.not-activated");

                                if (button) {
                                    console.log("Found activation button for coupon " + (i + 1));
                                    button.click();
                                    activatedCount++;
                                    console.log("Clicked activation button for coupon " + (i + 1));
                                } else {
                                    // Check if the button is already activated
                                    var activatedButton = callToAction.shadowRoot.querySelector("div > button.coupon-call-to-action__button.coupon__activate-button.activated");
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
                    results_json.get("result", {}).get("result", {}).get("value", "{}")
                )
                results = json.loads(json_str)
            else:
                # Try to parse it directly
                results = json.loads(results_json)

            if results.get("success"):
                print(
                    f"Successfully activated {results.get('activated')} out of {results.get('total')} coupons for {partner_name}"
                )
                return {
                    "partner_name": partner_name,
                    "partner_id": partner_id,
                    "activated": results.get("activated", 0),
                    "total": results.get("total", 0),
                    "success": True,
                }
            else:
                print(
                    f"Activation failed for {partner_name}: {results.get('error', 'Unknown error')}"
                )
                return {
                    "partner_name": partner_name,
                    "partner_id": partner_id,
                    "error": results.get("error", "Unknown error"),
                    "success": False,
                }
        except Exception as e:
            print(f"Error processing activation results for {partner_name}: {e}")
            return {
                "partner_name": partner_name,
                "partner_id": partner_id,
                "error": str(e),
                "success": False,
            }
    else:
        print(f"Failed to get activation results for {partner_name}")
        return {
            "partner_name": partner_name,
            "partner_id": partner_id,
            "error": "Failed to get activation results",
            "success": False,
        }


async def main():
    # Load configuration
    config = load_config()
    merchants = config.get("merchants", [])
    options = config.get("options", {})

    if not merchants:
        print("No merchants found in config.yaml. Please add at least one merchant.")
        return

    print(f"Found {len(merchants)} merchants in config.yaml")

    # Create browser options
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    async with Chrome(options=options) as browser:
        await browser.start()
        page = await browser.get_page()

        # Set a more realistic user agent
        await page.execute_script(
            """
            Object.defineProperty(navigator, 'userAgent', {
                get: function () { return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'; }
            });

            // Override properties that automation detection might check
            Object.defineProperty(navigator, 'webdriver', {
                get: function () { return false; }
            });
        """
        )

        # Navigate to the login page
        print("Navigating to Payback login page...")
        await page.go_to("https://www.payback.de/login")

        # Wait for page to load
        await asyncio.sleep(5)
        print("Page loaded, looking for cookie consent...")

        # Handle cookie consent button
        try:
            cookie_selector = '//*[@id="onetrust-reject-all-handler"]'
            button = await page.find_element(By.XPATH, cookie_selector)
            await button.click()
            print("Clicked cookie consent button")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Could not find or click cookie button: {e}")

        # Wait for page to fully load after cookie handling
        await asyncio.sleep(3)
        print("Attempting to interact with login form...")

        # Access the input element through the nested shadow DOM structure
        print("Accessing username input through nested shadow DOM...")

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
            + PAYBACK_USERNAME
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

        print(f"Successfully entered username: {PAYBACK_USERNAME}")

        # Wait a moment before trying to find and click the continue button
        await asyncio.sleep(2)

        # Try to find and click the continue button in the shadow DOM
        # Using the correct JS path with the additional shadow root level
        print("Clicking continue button...")
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

        print("Clicked continue button")

        # Wait for the password page to load
        print("Waiting for password page to load...")
        await asyncio.sleep(5)

        # Now enter the password using the provided shadow DOM path
        print("Accessing password input through nested shadow DOM...")

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
            + PAYBACK_PASSWORD
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

        print("Successfully entered password")

        # Wait a moment before clicking the login button
        await asyncio.sleep(2)

        # Click the login button
        print("Clicking login button...")
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

        print("Clicked login button")

        # Wait to see the result
        print("Waiting for login to complete...")
        await asyncio.sleep(2)

        # Check if login was successful by looking for elements on the page
        print("Checking login status...")
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

            print("Login completed.")
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error checking login status: {e}")
            return

        # Process each merchant from the config
        activation_results = []
        for merchant in merchants:
            merchant_name = merchant.get("name", "Unknown")
            partner_id = merchant.get("partner_id", "")

            if not partner_id:
                print(f"Skipping {merchant_name}: No partner_id specified")
                continue

            # Activate coupons for this merchant
            result = await activate_coupons_for_partner(page, merchant_name, partner_id)
            activation_results.append(result)

            # Wait a moment before processing the next merchant
            await asyncio.sleep(2)

        # Print summary of all activations
        print("\n===== ACTIVATION SUMMARY =====")
        total_activated = 0
        total_available = 0

        for result in activation_results:
            partner_name = result.get("partner_name", "Unknown")
            if result.get("success", False):
                activated = result.get("activated", 0)
                total = result.get("total", 0)
                total_activated += activated
                total_available += total
                print(
                    f"✅ {partner_name}: Activated {activated} out of {total} coupons"
                )
            else:
                error = result.get("error", "Unknown error")
                print(f"❌ {partner_name}: Failed - {error}")

        print(
            f"\nTotal: Activated {total_activated} out of {total_available} coupons across {len(merchants)} merchants"
        )
        print("===== END OF SUMMARY =====")

        # Activated coupons overview
        print("\n===== ACTIVATED COUPONS OVERVIEW =====")
        await page.go_to("https://www.payback.de/coupons?partnerId=")

        await asyncio.sleep(10)

        await page.print_to_pdf("coupons.pdf")
        print("===== END OF ACTIVATED COUPONS OVERVIEW =====")


asyncio.run(main())
