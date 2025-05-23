# AutoPunkte

Automatic Payback coupon activation using GitHub CI/CD.

## Overview

AutoPunkte is a Python application that automatically activates Payback coupons for specified merchants. It uses the pydoll library to interact with the Payback website without requiring webdrivers.

## Features

- Automatic login to Payback account
- Activation of coupons for specified merchants
- Scheduled runs via GitHub Actions
- Optional notification of activation results
- Saves screenshots and HTML content of activation results

## Requirements

- Python 3.12
- pydoll library
- GitHub account (for CI/CD)

## Setup

1. Clone this repository
2. Install dependencies using `uv`: `uv sync`
3. Configure your Payback credentials as GitHub secrets:
   - `PAYBACK_USERNAME`: Your Payback username/email
   - `PAYBACK_PASSWORD`: Your Payback password
4. Customize the list of merchants in `config.yaml`
5. Push to GitHub to trigger automatic runs

## Configuration

Create a `config.yaml` file with your preferred merchants:

```yaml
merchants:
  - name: REWE
    partner_id: lp123456
  - name: Douglas
    partner_id: lp703660
  - name: Edeka
    partner_id: lp747
  - name: Payback Gutscheine
    partner_id: lp741
  - name: Payback Prospekte
    partner_id: lp570
  - name: DM
    partner_id: lp54
  - name: Decathlon
    partner_id: lp732
```

These partner IDs can be found on the Payback website by clicking on the merchant's name and copying the partner ID from the URL.

## VPN Setup (Mullvad)

To mitigate potential CAPTCHA issues caused by frequent logins from varying GitHub Actions IP addresses, this project uses Mullvad VPN via OpenVPN.

1.  **Mullvad Configuration:**

    - Download an OpenVPN configuration package for macOS (`.tblk`) from your Mullvad account.
    - Place the extracted `.tblk` directory (e.g., `Mullvad.tblk`) in the root of this project.
    - This directory must contain at least:
      - Your specific OpenVPN configuration file (e.g., `mullvad_xx_yyy.conf`).
      - The Mullvad certificate file (`mullvad_ca.crt`).
    - The workflow is configured to use the `.conf` and `.crt` files from this directory.

2.  **GitHub Secret:**

    - Add your Mullvad account number as a GitHub secret named `MULLVAD_USER`.

3.  **Credentials File (`.gitignore`):**

    - The workflow automatically creates the necessary `mullvad_userpass.txt` file inside the `Mullvad.tblk` directory during runtime, using the `MULLVAD_USER` secret.
    - **Important:** Ensure `Mullvad.tblk/mullvad_userpass.txt` is added to your `.gitignore` file to prevent committing your account number.

4.  **Workflow:**
    - The GitHub Actions workflow automatically installs OpenVPN using Homebrew and connects using the provided configuration before running the Python script.

## GitHub Actions Workflow

The workflow is set to run every Monday and Thursday at 10:00 AM UTC and can also be triggered manually. It uploads logs, screenshots, and HTML files as artifacts for each run.

## Security

Ensure that your Payback credentials are stored securely as GitHub secrets to prevent exposure in logs or code.

## License

MIT
