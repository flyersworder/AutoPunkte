# AutoPunkte

Automatic Payback coupon activation using GitHub CI/CD.

## Overview

AutoPunkte is a Python application that automatically activates Payback coupons for specified merchants. It uses the pydoll library to interact with the Payback website without requiring webdrivers.

## Features

- Automatic login to Payback account
- Activation of coupons for specified merchants
- Scheduled runs via GitHub Actions
- Optional notification of activation results

## Requirements

- Python 3.8+
- pydoll library
- GitHub account (for CI/CD)

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your Payback credentials as GitHub secrets
4. Customize the list of merchants in `config.yaml`
5. Push to GitHub to trigger automatic runs

## Configuration

Create a `config.yaml` file with your preferred merchants:

```yaml
merchants:
  - REWE
  - dm
  - ALDI SÜD
  # Add more merchants as needed
```

## GitHub Secrets

Set up the following secrets in your GitHub repository:

- `PAYBACK_USERNAME`: Your Payback username/email
- `PAYBACK_PASSWORD`: Your Payback password

## License

MIT
